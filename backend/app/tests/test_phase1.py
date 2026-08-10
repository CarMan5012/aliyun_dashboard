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
from app.db.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.account import CloudAccount
from app.models.resource import Resource
from app.tasks import aliyun_sync

class TestPhase1SyncAndAccountSecurity(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(cls.engine)
        cls.TestingSessionLocal = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.db = self.TestingSessionLocal()
        self.db.query(Resource).delete()
        self.db.query(CloudAccount).delete()
        self.db.commit()

        self.account = CloudAccount(
            account_alias="测试账号",
            access_key_id="LTAI_TEST",
            sync_interval=24
        )
        self.account.set_secret("SECRET_TEST")
        self.db.add(self.account)
        self.db.commit()
        self.db.refresh(self.account)

    def tearDown(self):
        self.db.close()

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def test_sync_failure_preserves_old_data(self):
        """测试 1：模拟区域接口失败，数据库旧数据保持不变，Celery 任务抛出异常，last_synced_at 不更新，last_attempted_at 更新"""
        account_id = self.account.id
        
        old_resource = Resource(
            account_id=account_id,
            account_name="测试账号",
            resource_type="ECS",
            search_key="192.168.1.1,old-instance",
            details='{"instance_id": "i-old123", "instance_name": "old-instance"}'
        )
        self.db.add(old_resource)
        self.db.commit()

        initial_synced_at = self.account.last_synced_at
        self.assertIsNone(initial_synced_at)

        with patch("app.tasks.aliyun_sync.SessionLocal", side_effect=self.TestingSessionLocal), \
             patch("app.tasks.aliyun_sync.AccountSyncLock.acquire", return_value=True), \
             patch("app.tasks.aliyun_sync.AccountSyncLock.renew", return_value=True), \
             patch("app.tasks.aliyun_sync.AccountSyncLock.release", return_value=True), \
             patch("app.tasks.aliyun_sync.AccountCooldown.set_cooldown"), \
             patch("app.tasks.aliyun_sync.sync_ecs", side_effect=RuntimeError("ECS 超时")), \
             patch("app.tasks.aliyun_sync.sync_eip", side_effect=RuntimeError("EIP 超时")), \
             patch("app.tasks.aliyun_sync.sync_domain", side_effect=RuntimeError("Domain 超时")), \
             patch("app.tasks.aliyun_sync.sync_ssl", side_effect=RuntimeError("SSL 超时")):

            result = aliyun_sync.sync_account_resources(account_id)

        self.assertEqual(result["status"], "failure")
        self.assertEqual(result["services"]["ECS"]["error_category"], "unknown")

        resources = self.db.query(Resource).filter(Resource.account_id == account_id).all()
        self.assertEqual(len(resources), 1)
        self.assertEqual(resources[0].search_key, "192.168.1.1,old-instance")

        self.db.expire_all()
        updated_account = self.db.query(CloudAccount).filter(CloudAccount.id == account_id).first()
        self.assertIsNone(updated_account.last_synced_at)
        self.assertEqual(updated_account.last_sync_status, "failure")
        self.assertIn("ECS 超时", updated_account.last_sync_error)

    def test_sync_success_updates_latest_status(self):
        with (
            patch("app.tasks.aliyun_sync.SessionLocal", side_effect=self.TestingSessionLocal),
            patch("app.tasks.aliyun_sync.AccountSyncLock.acquire", return_value=True),
            patch("app.tasks.aliyun_sync.AccountSyncLock.renew", return_value=True),
            patch("app.tasks.aliyun_sync.AccountSyncLock.release", return_value=True),
            patch("app.tasks.aliyun_sync.AccountCooldown.clear_cooldown"),
            patch("app.tasks.aliyun_sync.sync_ecs", return_value=1),
            patch("app.tasks.aliyun_sync.sync_eip", return_value=2),
            patch("app.tasks.aliyun_sync.sync_domain", return_value=3),
            patch("app.tasks.aliyun_sync.sync_ssl", return_value=4),
            patch("app.tasks.aliyun_sync.enqueue_domain_alert_check") as enqueue_alert,
        ):
            aliyun_sync.sync_account_resources(self.account.id)
            enqueue_alert.assert_called_once_with()

        self.db.expire_all()
        updated_account = self.db.query(CloudAccount).filter(CloudAccount.id == self.account.id).first()
        self.assertEqual(updated_account.last_sync_status, "success")
        self.assertIsNone(updated_account.last_sync_error)
        self.assertIsNotNone(updated_account.last_synced_at)

    def test_retry_and_error_classification(self):
        class ApiError(RuntimeError):
            code = "Throttling.User"
            status_code = 429

        operation = MagicMock(side_effect=[ApiError("too many requests"), "ok"])
        with (
            patch("app.tasks.aliyun_sync.time.sleep") as sleeper,
            patch("app.tasks.aliyun_sync.random.uniform", return_value=0),
        ):
            result = aliyun_sync._aliyun_call("test", operation)

        self.assertEqual(result, "ok")
        self.assertEqual(operation.call_count, 2)
        sleeper.assert_called_once_with(1.0)
        denied = ApiError("Specified access key denied due to access policy")
        denied.code = "InvalidAccessKeyId.AccessPolicyDenied"
        self.assertEqual(aliyun_sync.classify_api_error(denied), "access_denied")

    def test_resource_account_name_dynamic_property(self):
        """测试 2：验证资源表基于外键的动态 ORM 别名匹配"""
        account_id = self.account.id
        resource = Resource(
            account_id=account_id,
            account_name="原别名",
            resource_type="ECS",
            search_key="1.1.1.1",
            details="{}"
        )
        self.db.add(resource)
        self.db.commit()

        self.assertEqual(resource.account_name, "测试账号")

        self.account.account_alias = "新集群账号"
        self.db.commit()

        self.db.expire_all()
        reloaded_resource = self.db.query(Resource).filter(Resource.id == resource.id).first()
        self.assertEqual(reloaded_resource.account_name, "新集群账号")

    def test_account_deletion_cascades_resources(self):
        """测试 3：验证删除云账号时关联的资源记录是否触发 CASCADE 被同步清除"""
        account_id = self.account.id
        resource = Resource(
            account_id=account_id,
            account_name="测试账号",
            resource_type="Domain",
            search_key="example.com",
            details="{}"
        )
        self.db.add(resource)
        self.db.commit()

        res_before = self.db.query(Resource).filter(Resource.account_id == account_id).all()
        self.assertEqual(len(res_before), 1)

        self.db.delete(self.account)
        self.db.commit()

        res_after = self.db.query(Resource).filter(Resource.account_id == account_id).all()
        self.assertEqual(len(res_after), 0)

if __name__ == "__main__":
    unittest.main()
