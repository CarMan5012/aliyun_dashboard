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

class TestPhase3DataContractAndPages(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        from app.db.session import get_db
        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        app.dependency_overrides[get_db] = lambda: mock_db

    def test_input_cleaning_and_interval_validation(self):
        """测试 1：账号别名/AK 前后空格清洗、纯空白拒绝及 negative interval 校验"""

        from app.models.account import CloudAccount
        created_acc = CloudAccount(id=88, account_alias="清洗测试", access_key_id="LTAI_CLEAN", sync_interval=12)
        created_acc.set_secret("SK_CLEAN")

        with patch("app.api.v1.accounts.crud_account.create_account", return_value=created_acc), \
             patch("app.api.v1.accounts.sync_single_account_task.delay"):
            # 1.1 自动清洗空格并保留
            res1 = self.client.post("/api/v1/accounts", json={
                "account_alias": "  清洗测试  ",
                "access_key_id": "  LTAI_CLEAN  ",
                "access_key_secret": "  SK_CLEAN  ",
                "sync_interval": 12
            })
            self.assertEqual(res1.status_code, 201)
            body1 = res1.json()
            self.assertEqual(body1["data"]["account_alias"], "清洗测试")
            self.assertEqual(body1["data"]["access_key_id"], "LTAI_CLEAN")

        # 1.2 拒绝纯空白或纯前缀
        res2 = self.client.post("/api/v1/accounts", json={
            "account_alias": "   ",
            "access_key_id": "LTAI_NORMAL",
            "access_key_secret": "SK_NORMAL",
            "sync_interval": 12
        })
        self.assertEqual(res2.status_code, 422)

        # 1.3 拒绝负数 sync_interval
        res3 = self.client.post("/api/v1/accounts", json={
            "account_alias": "正常别名",
            "access_key_id": "LTAI_NORMAL",
            "access_key_secret": "SK_NORMAL",
            "sync_interval": -5
        })
        self.assertEqual(res3.status_code, 422)

    def test_alias_conflict_return_409(self):
        """测试 2：清洗后别名重复返回 HTTP 409 Conflict"""
        from app.db.session import get_db
        mock_acc = MagicMock()
        mock_acc.account_alias = "已存在别名"
        
        with patch("app.api.v1.accounts.crud_account.get_account_by_alias", return_value=mock_acc):
            app.dependency_overrides[get_db] = lambda: MagicMock()
            res = self.client.post("/api/v1/accounts", json={
                "account_alias": "  已存在别名  ",
                "access_key_id": "LTAI_NEW",
                "access_key_secret": "SK_NEW",
                "sync_interval": 24
            })
            self.assertEqual(res.status_code, 409)

    def test_timezone_iso_timestamp(self):
        """测试 3：时间字段输出 ISO 8601 时区字符串契约"""
        from app.models.account import CloudAccount
        from datetime import datetime, timezone

        acc = CloudAccount(
            id=1,
            account_alias="时区账号",
            access_key_id="LTAI_TZ",
            sync_interval=24
        )
        acc.created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        
        with patch("app.api.v1.accounts.crud_account.get_account", return_value=acc):
            res = self.client.get("/api/v1/accounts/1")
            self.assertEqual(res.status_code, 200)
            body = res.json()
            created_at_str = body["data"]["created_at"]
            self.assertTrue(created_at_str.endswith("Z") or "+00:00" in created_at_str)

if __name__ == "__main__":
    unittest.main()
