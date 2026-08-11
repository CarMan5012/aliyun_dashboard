import redis
import uuid
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

def get_redis_client():
    """获取 Redis 客户端实例"""
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=int(settings.REDIS_PORT),
        db=0,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=5
    )

import threading

local_account_locks: dict[int, threading.Lock] = {}
local_locks_guard = threading.Lock()

def get_local_lock(account_id: int | str) -> threading.Lock:
    acc_id_int = int(account_id)
    with local_locks_guard:
        if acc_id_int not in local_account_locks:
            local_account_locks[acc_id_int] = threading.Lock()
        return local_account_locks[acc_id_int]

class RedisInfrastructureError(Exception):
    """Redis 基础设施网络/连接故障异常"""
    pass

class AccountSyncLock:
    def __init__(self, account_id: int | str, timeout: int = 1000):
        self.account_id = int(account_id)
        self.lock_key = f"sync_lock:account:{account_id}"
        self.task_key = f"sync_task_id:account:{account_id}"
        self.timeout = timeout
        self.token = str(uuid.uuid4())
        self._redis = None
        self.is_fallback_local = False
        self.local_acquired = False

    @property
    def redis(self):
        if self._redis is None:
            self._redis = get_redis_client()
        return self._redis

    def acquire(self, task_id: str = None) -> bool:
        """
        尝试获取分布式锁。若 Redis 不可用，自动平滑降级至进程内本地内存锁。
        """
        lua_script = """
        if redis.call('set', KEYS[1], ARGV[1], 'NX', 'EX', ARGV[2]) then
            if ARGV[3] ~= '' then
                redis.call('set', KEYS[2], ARGV[3], 'EX', ARGV[2])
            end
            return 1
        else
            return 0
        end
        """
        task_id_str = task_id or ""
        try:
            res = self.redis.eval(lua_script, 2, self.lock_key, self.task_key, self.token, str(self.timeout), task_id_str)
            return bool(res)
        except Exception as e:
            logger.warning(f"Redis 不可用 (账号 ID {self.account_id})，平滑降级至本地线程锁: {e}")
            self.is_fallback_local = True
            loc_lock = get_local_lock(self.account_id)
            acquired = loc_lock.acquire(blocking=False)
            self.local_acquired = acquired
            return acquired

    def renew(self, additional_seconds: int = 1000) -> bool:
        """
        使用 Lua 脚本对持有令牌的当前锁进行原子续租
        """
        if self.is_fallback_local:
            return self.local_acquired

        lua_script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            redis.call('expire', KEYS[1], ARGV[2])
            if redis.call('exists', KEYS[2]) == 1 then
                redis.call('expire', KEYS[2], ARGV[2])
            end
            return 1
        else
            return 0
        end
        """
        try:
            res = self.redis.eval(lua_script, 2, self.lock_key, self.task_key, self.token, str(additional_seconds))
            return bool(res)
        except Exception as e:
            logger.warning(f"Redis 锁续租异常 (账号 ID {self.account_id}): {e}")
            return False

    def release(self):
        """使用 Lua 脚本安全释放锁，避免误解他人锁"""
        if self.is_fallback_local:
            if self.local_acquired:
                loc_lock = get_local_lock(self.account_id)
                try:
                    loc_lock.release()
                except Exception:
                    pass
                self.local_acquired = False
            return

        lua_script = """
        if redis.call('get', KEYS[1]) == ARGV[1] then
            redis.call('del', KEYS[2])
            return redis.call('del', KEYS[1])
        else
            return 0
        end
        """
        try:
            self.redis.eval(lua_script, 2, self.lock_key, self.task_key, self.token)
        except Exception as e:
            logger.warning(f"Redis 分布式锁释放异常 (账号 ID {self.account_id}): {e}")

    @classmethod
    def get_running_task_id(cls, account_id: int) -> str:
        """查询指定账号当前正在运行的任务 ID"""
        try:
            r = get_redis_client()
            return r.get(f"sync_task_id:account:{account_id}")
        except Exception as e:
            logger.warning(f"获取运行中任务 ID 失败 (账号 {account_id}): {e}")
            return None

class AccountCooldown:
    COOLDOWN_SECONDS = 900  # 15 分钟失败退避冷却

    @classmethod
    def set_cooldown(cls, account_id: int, seconds: int = None):
        """同步失败后配置账号退避冷却标识"""
        try:
            r = get_redis_client()
            r.set(f"sync_cooldown:account:{account_id}", "1", ex=seconds or cls.COOLDOWN_SECONDS)
        except Exception as e:
            logger.warning(f"设置账号 {account_id} 冷却失败: {e}")

    @classmethod
    def clear_cooldown(cls, account_id: int):
        """同步成功后清除账号退避冷却标识"""
        try:
            r = get_redis_client()
            r.delete(f"sync_cooldown:account:{account_id}")
        except Exception as e:
            logger.warning(f"清除账号 {account_id} 冷却失败: {e}")

    @classmethod
    def is_in_cooldown(cls, account_id: int) -> bool:
        """检查指定账号是否在退避冷却时间内"""
        try:
            r = get_redis_client()
            return bool(r.exists(f"sync_cooldown:account:{account_id}"))
        except Exception as e:
            logger.warning(f"检查账号 {account_id} 冷却状态失败: {e}")
            return False


class EmptyResultGuard:
    WINDOW_SECONDS = 7200

    @classmethod
    def allow_replace(cls, account_id: int, service_name: str, old_count: int, new_count: int) -> bool:
        key = f"sync_empty_result:account:{account_id}:{service_name}"
        if new_count or not old_count:
            try:
                get_redis_client().delete(key)
            except Exception as exc:
                logger.warning(f"清理账号 {account_id} 的 {service_name} 空结果标记失败: {exc}")
            return True
        try:
            redis_client = get_redis_client()
            if redis_client.get(key):
                redis_client.delete(key)
                return True
            redis_client.set(key, "1", ex=cls.WINDOW_SECONDS)
            return False
        except Exception as exc:
            logger.warning(f"账号 {account_id} 的 {service_name} 空结果保护检查失败: {exc}")
            return False
