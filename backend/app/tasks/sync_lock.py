import time
import logging
import threading
from typing import Optional, Union

logger = logging.getLogger(__name__)

# 全局账号线程安全锁表
local_account_locks: dict[str, threading.Lock] = {}
local_locks_guard = threading.Lock()

# 全局账号冷却时间表 (account_id -> expire_timestamp)
local_account_cooldowns: dict[int, float] = {}

# 全局空结果保护表 (account_id:service_name)
local_empty_result_guards: set[str] = set()

def get_local_lock(account_id: Union[int, str]) -> threading.Lock:
    acc_id_str = str(account_id)
    with local_locks_guard:
        if acc_id_str not in local_account_locks:
            local_account_locks[acc_id_str] = threading.Lock()
        return local_account_locks[acc_id_str]


class AccountSyncLock:
    """
    账号级线程安全同步锁
    """
    def __init__(self, account_id: Union[int, str], timeout: int = 1000):
        self.account_id = str(account_id)
        self.local_acquired = False

    def acquire(self, task_id: str = None) -> bool:
        """尝试获取账号本地线程锁（非阻塞）"""
        loc_lock = get_local_lock(self.account_id)
        acquired = loc_lock.acquire(blocking=False)
        self.local_acquired = acquired
        return acquired

    def renew(self, additional_seconds: int = 1000) -> bool:
        """原生线程锁无需续租，只要持有即有效"""
        return self.local_acquired

    def release(self):
        """安全释放账号本地线程锁"""
        if self.local_acquired:
            loc_lock = get_local_lock(self.account_id)
            try:
                loc_lock.release()
            except Exception:
                pass
            self.local_acquired = False

    @classmethod
    def get_running_task_id(cls, account_id: Union[int, str]) -> Optional[str]:
        """查询指定账号当前是否正在执行同步任务"""
        loc_lock = get_local_lock(account_id)
        return "local_sync_running" if loc_lock.locked() else None


class AccountCooldown:
    """
    失败退避冷却机制（纯内存化管理）
    """
    COOLDOWN_SECONDS = 900  # 15 分钟失败退避冷却

    @classmethod
    def set_cooldown(cls, account_id: int, seconds: int = None):
        """同步失败后配置账号退避冷却标识"""
        local_account_cooldowns[account_id] = time.time() + (seconds or cls.COOLDOWN_SECONDS)

    @classmethod
    def clear_cooldown(cls, account_id: int):
        """同步成功后清除账号退避冷却标识"""
        local_account_cooldowns.pop(account_id, None)

    @classmethod
    def is_in_cooldown(cls, account_id: int) -> bool:
        """检查指定账号是否在退避冷却时间内"""
        expire_at = local_account_cooldowns.get(account_id)
        if expire_at:
            if time.time() < expire_at:
                return True
            local_account_cooldowns.pop(account_id, None)
        return False


class EmptyResultGuard:
    """
    空结果保护机制（首次出现空结果时暂不清理旧数据，等待下次确认）
    """
    @classmethod
    def allow_replace(cls, account_id: int, service_name: str, old_count: int, new_count: int) -> bool:
        key = f"sync_empty_result:account:{account_id}:{service_name}"
        if new_count or not old_count:
            local_empty_result_guards.discard(key)
            return True

        if key in local_empty_result_guards:
            local_empty_result_guards.discard(key)
            return True
        local_empty_result_guards.add(key)
        return False
