import os
import sys
from cryptography.fernet import Fernet
if not os.environ.get("ASSETVISTA_MASTER_KEY"):
    os.environ["ASSETVISTA_MASTER_KEY"] = Fernet.generate_key().decode()

os.environ["TESTING"] = "true"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

import json
import unittest
from unittest.mock import MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.account import CloudAccount
from app.models.resource import Resource
from app.tasks.aliyun_sync import sync_domain


class TestDomainRegistrant(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.db = self.Session()

        self.account = CloudAccount(
            account_alias="持有者测试账号",
            access_key_id="test_ak",
            encrypted_secret_key="dummy_sk",
            sync_interval=24,
        )
        self.db.add(self.account)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=self.engine)

    def test_sync_domain_stores_registrant_and_search_key(self):
        mock_domain_obj = MagicMock()
        mock_domain_obj.domain_name = "antigravity.cn"
        mock_domain_obj.ccompany = "示例信息科技有限公司"
        mock_domain_obj.domain_status = "2"
        mock_domain_obj.expiration_date = "2028-08-08"
        mock_domain_obj.registration_date = "2020-08-08"

        mock_resp = MagicMock()
        mock_resp.body.data.domain = [mock_domain_obj]
        mock_resp.body.next_page = False

        mock_client = MagicMock()
        mock_client.query_domain_list.return_value = mock_resp

        with patch("app.tasks.aliyun_sync.create_client", return_value=mock_client):
            count = sync_domain(
                account_id=self.account.id,
                account_name=self.account.account_alias,
                ak="test_ak",
                sk="test_sk",
                db=self.db,
            )

        self.assertEqual(count, 1)

        saved = self.db.query(Resource).filter(
            Resource.account_id == self.account.id,
            Resource.resource_type == "Domain"
        ).first()

        self.assertIsNotNone(saved)
        details = json.loads(saved.details)
        self.assertEqual(details.get("domain_name"), "antigravity.cn")
        self.assertEqual(details.get("registrant"), "示例信息科技有限公司")
        self.assertIn("示例信息科技有限公司", saved.search_key)
        self.assertIn("antigravity.cn", saved.search_key)


if __name__ == "__main__":
    unittest.main()
