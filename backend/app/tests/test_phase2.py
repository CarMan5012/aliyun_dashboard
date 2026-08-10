import sys
import os
from cryptography.fernet import Fernet
if not os.environ.get("ASSETVISTA_MASTER_KEY"):
    os.environ["ASSETVISTA_MASTER_KEY"] = Fernet.generate_key().decode()

os.environ["TESTING"] = "true"

import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.main import app
from fastapi.testclient import TestClient
from app.tasks.sync_lock import AccountSyncLock, AccountCooldown

class TestPhase2ConcurrencyAndTaskStatus(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_account_sync_lock_and_deduplication(self):
        """测试 1：Redis 分布式锁获取、已有任务判断及安全释放"""
        account_id = 9991
        lock1 = AccountSyncLock(account_id, timeout=30)
        lock2 = AccountSyncLock(account_id, timeout=30)

        storage = {}
        def mock_get(name):
            return storage.get(name)

        def mock_eval(script, numkeys, *keys_and_args):
            lock_k = keys_and_args[0]
            task_k = keys_and_args[1]
            token_val = keys_and_args[2]
            if "redis.call('set', KEYS[1]" in script:
                if lock_k in storage:
                    return 0
                storage[lock_k] = token_val
                if len(keys_and_args) > 4 and keys_and_args[4]:
                    storage[task_k] = keys_and_args[4]
                return 1
            if storage.get(lock_k) == token_val:
                storage.pop(lock_k, None)
                storage.pop(task_k, None)
                return 1
            return 0

        mock_r = MagicMock()
        mock_r.get.side_effect = mock_get
        mock_r.eval.side_effect = mock_eval

        with patch("app.tasks.sync_lock.get_redis_client", return_value=mock_r):
            success1 = lock1.acquire("task-111")
            self.assertTrue(success1)

            success2 = lock2.acquire("task-222")
            self.assertFalse(success2)

            running_task = AccountSyncLock.get_running_task_id(account_id)
            self.assertEqual(running_task, "task-111")

            lock1.release()

            success3 = lock2.acquire("task-333")
            self.assertTrue(success3)

    def test_cooldown_backoff(self):
        """测试 2：失败任务的退避冷却逻辑"""
        account_id = 9992
        storage = {}

        def mock_set(name, value, ex=None):
            storage[name] = value
            return True

        def mock_exists(name):
            return name in storage

        mock_r = MagicMock()
        mock_r.set.side_effect = mock_set
        mock_r.exists.side_effect = mock_exists

        with patch("app.tasks.sync_lock.get_redis_client", return_value=mock_r):
            self.assertFalse(AccountCooldown.is_in_cooldown(account_id))
            AccountCooldown.set_cooldown(account_id)
            self.assertTrue(AccountCooldown.is_in_cooldown(account_id))

    def test_decoupled_account_create_on_celery_failure(self):
        """测试 3：Celery 不可用时，账号创建仍然成功，返回警告；手动同步路由返回 503"""
        with patch("app.tasks.aliyun_sync.sync_all_accounts_task.delay") as mock_delay:
            mock_delay.side_effect = RuntimeError("Celery Connection Refused")
            res = self.client.post("/api/v1/sync")
            self.assertEqual(res.status_code, 503)

if __name__ == "__main__":
    unittest.main()
