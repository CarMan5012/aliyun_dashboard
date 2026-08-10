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
from app.tasks.sync_lock import AccountSyncLock, RedisInfrastructureError
from app.core.config import Settings
from app.models.account import CloudAccount

class TestRemainingIssuesFixes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_sqlalchemy_url_create_escaping(self):
        """测试 1：SQLAlchemy URL.create 转义，支持密码中带有 @, /, : 等特殊字符"""
        custom_settings = Settings(
            MYSQL_USER="user",
            MYSQL_PASSWORD="P@ssw0rd!/123:str",
            MYSQL_HOST="localhost",
            MYSQL_PORT="3306",
            MYSQL_DB="assetvista"
        )
        uri = custom_settings.SQLALCHEMY_DATABASE_URI
        self.assertIn("P%40ssw0rd%21%2F123%3Astr", uri)

    def test_redis_lock_fail_closed_and_renew(self):
        """测试 2：Redis 锁 Fail-Closed 策略与 Lua 锁续租 renew 方法"""
        account_id = 9999
        lock = AccountSyncLock(account_id, timeout=1000)
        
        # 2.1 模拟 Redis 抛出 Exception
        mock_r_err = MagicMock()
        mock_r_err.set.side_effect = RuntimeError("Redis socket timeout")
        mock_r_err.eval.side_effect = RuntimeError("Redis socket timeout")
        with patch("app.tasks.sync_lock.get_redis_client", return_value=mock_r_err):
            # Redis 基础设施故障判定：必须抛出专用 RedisInfrastructureError
            with self.assertRaises(RedisInfrastructureError):
                lock.acquire()

        # 2.2 模拟 Lua 续租 renew 成功
        lock2 = AccountSyncLock(account_id, timeout=1000)
        mock_r_ok = MagicMock()
        mock_r_ok.eval.return_value = 1
        with patch("app.tasks.sync_lock.get_redis_client", return_value=mock_r_ok):
            self.assertTrue(lock2.renew(1000))

    def test_structured_sync_all_accounts_result(self):
        """测试 3：全量同步返回结构化状态字典"""
        from app.tasks.aliyun_sync import sync_all_accounts_task
        
        mock_db = MagicMock()
        mock_db.query.return_value.all.return_value = []
        
        with patch("app.tasks.aliyun_sync.SessionLocal", return_value=mock_db):
            res = sync_all_accounts_task()
            self.assertIsInstance(res, dict)
            self.assertEqual(res["status"], "success")
            self.assertEqual(res["total"], 0)
            self.assertIn("skipped_cooldown_count", res)
            self.assertIn("already_running_count", res)

    def test_database_error_propagation_503(self):
        """测试 4：数据库查询/连接异常返回 HTTP 503 Service Unavailable"""
        from app.db.session import get_db
        from sqlalchemy.exc import OperationalError
        def mock_err_db():
            raise OperationalError("SELECT 1", {}, Exception("MySQL Connection refused"))

        app.dependency_overrides[get_db] = mock_err_db
        res = self.client.get("/api/v1/resources?type=ECS")
        self.assertEqual(res.status_code, 503)

    def test_account_update_credential_check(self):
        """测试 5：账号更新仅在 AccessKey 凭证发生变动时触发自动同步"""
        from app.db.session import get_db
        app.dependency_overrides[get_db] = lambda: MagicMock()

        mock_acc = CloudAccount(
            id=55,
            account_alias="旧别名",
            access_key_id="LTAI_OLD",
            sync_interval=24
        )
        mock_acc.set_secret("SK_OLD")

        with patch("app.api.v1.accounts.crud_account.get_account", return_value=mock_acc), \
             patch("app.api.v1.accounts.crud_account.get_account_by_alias", return_value=None), \
             patch("app.api.v1.accounts.crud_account.update_account", return_value=mock_acc), \
             patch("app.api.v1.accounts.sync_single_account_task.delay") as mock_delay:

            payload = {
                "account_alias": "新别名",
                "access_key_id": "LTAI_OLD",
                "sync_interval": 12
            }
            res = self.client.put("/api/v1/accounts/55", json=payload)
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertFalse(body["sync_queued"])
            mock_delay.assert_not_called()

if __name__ == "__main__":
    unittest.main()
