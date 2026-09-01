import unittest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.account import CloudAccount
from app.schemas.account import CloudAccountCreate, CloudAccountUpdate
from app.tasks.scheduler import _smooth_batch_sync, _run_scheduled_sync

class TestSchedulerAndIntervals(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

    def test_cloud_account_schema_default_interval(self):
        """验证新账号默认 sync_interval 为 168 (每周一)"""
        acc_in = CloudAccountCreate(
            account_alias="生产测试账号",
            access_key_id="LTAI5test12345",
            access_key_secret="secret12345"
        )
        self.assertEqual(acc_in.sync_interval, 168)

    def test_smooth_batch_sync_execution(self):
        """验证异步平滑队列按序调用 sync_account_resources 且不崩溃"""
        account_ids = [101, 102, 103]
        with patch("app.tasks.scheduler.sync_account_resources") as mock_sync, \
             patch("app.tasks.scheduler.time.sleep") as mock_sleep, \
             patch("app.tasks.scheduler.AccountCooldown.is_in_cooldown", return_value=False), \
             patch("app.tasks.scheduler.AccountSyncLock.get_running_task_id", return_value=None):
            
            _smooth_batch_sync(account_ids, "每周一凌晨同步")
            
            # 验证依次被调用 3 次
            self.assertEqual(mock_sync.call_count, 3)
            # 验证账号间有 2 次微缓冲 sleep
            self.assertEqual(mock_sleep.call_count, 2)

if __name__ == "__main__":
    unittest.main()
