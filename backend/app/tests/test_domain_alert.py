import datetime
import json
import os
import sys
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet

if not os.environ.get("ASSETVISTA_MASTER_KEY"):
    os.environ["ASSETVISTA_MASTER_KEY"] = Fernet.generate_key().decode()
os.environ["TESTING"] = "true"

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.account import CloudAccount
from app.models.domain_alert import DomainAlertEvent, DomainAlertSetting
from app.models.resource import Resource
from app.tasks.domain_alert import build_markdown, is_workday, process_domain_alerts


class TestDomainAlert(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(cls.engine)
        cls.Session = sessionmaker(bind=cls.engine)

    def setUp(self):
        self.db = self.Session()
        for model in (DomainAlertEvent, Resource, DomainAlertSetting, CloudAccount):
            self.db.query(model).delete()
        self.db.commit()
        self.client = TestClient(app)
        self.old_password = settings.SETTINGS_ADMIN_PASSWORD
        settings.SETTINGS_ADMIN_PASSWORD = "admin-test"

        def override_db():
            yield self.db

        app.dependency_overrides[get_db] = override_db

    def tearDown(self):
        app.dependency_overrides.clear()
        settings.SETTINGS_ADMIN_PASSWORD = self.old_password
        self.db.close()

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def test_settings_require_password_and_hide_secrets(self):
        payload = {
            "enabled": True,
            "reminder_days": 14,
            "warning_days": 7,
            "critical_days": 3,
            "keyword": "资产到期",
            "webhook": "https://oapi.dingtalk.com/robot/send?access_token=test-token",
            "secret": "SEC-test",
        }
        denied = self.client.put("/api/v1/settings/domain-alert", json=payload)
        self.assertEqual(denied.status_code, 403)
        denied_credentials = self.client.get("/api/v1/settings/domain-alert/credentials")
        self.assertEqual(denied_credentials.status_code, 403)

        missing_fields = self.client.put(
            "/api/v1/settings/domain-alert",
            json={"enabled": True},
            headers={"X-Settings-Password": "admin-test"},
        )
        self.assertEqual(missing_fields.status_code, 422)

        with patch("app.api.v1.settings.enqueue_domain_alert_check") as enqueue_alert:
            saved = self.client.put(
                "/api/v1/settings/domain-alert",
                json=payload,
                headers={"X-Settings-Password": "admin-test"},
            )
            enqueue_alert.assert_called_once_with()
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["data"]["keyword"], "资产到期")
        self.assertTrue(saved.json()["data"]["webhook_configured"])
        self.assertNotIn("test-token", saved.text)
        self.assertNotIn("SEC-test", saved.text)

        credentials = self.client.get(
            "/api/v1/settings/domain-alert/credentials",
            headers={"X-Settings-Password": "admin-test"},
        )
        self.assertEqual(credentials.status_code, 200)
        self.assertEqual(credentials.headers["cache-control"], "no-store")
        self.assertEqual(
            credentials.json()["data"],
            {
                "webhook": "https://oapi.dingtalk.com/robot/send?access_token=test-token",
                "secret": "SEC-test",
            },
        )

        loaded = self.client.get("/api/v1/settings/domain-alert")
        self.assertEqual(loaded.status_code, 200)
        self.assertEqual(set(loaded.json()), {"status", "data"})
        self.assertEqual(
            set(loaded.json()["data"]),
            {
                "enabled",
                "reminder_days",
                "warning_days",
                "critical_days",
                "keyword",
                "webhook_configured",
                "secret_configured",
            },
        )

    def test_rest_day_alert_is_sent_once_then_followed_up_on_workday(self):
        config = DomainAlertSetting(
            id=1,
            enabled=True,
            reminder_days=14,
            warning_days=7,
            critical_days=3,
        )
        config.set_webhook("https://oapi.dingtalk.com/robot/send?access_token=test-token")
        account = CloudAccount(
            account_alias="测试账号",
            access_key_id="LTAI_TEST",
            sync_interval=24,
        )
        account.set_secret("SECRET_TEST")
        self.db.add_all([config, account])
        self.db.commit()
        self.db.refresh(account)

        sunday = datetime.date(2026, 8, 9)
        expiration = sunday + datetime.timedelta(days=7)
        self.db.add(Resource(
            account_id=account.id,
            account_name="测试账号",
            resource_type="Domain",
            search_key="example.com",
            details=json.dumps({
                "domain_name": "example.com",
                "expiration_date": expiration.isoformat(),
            }),
        ))
        self.db.commit()

        with patch("app.tasks.domain_alert.send_dingtalk_markdown") as sender:
            first = process_domain_alerts(self.db, sunday)
            duplicate = process_domain_alerts(self.db, sunday)
            followup = process_domain_alerts(self.db, sunday + datetime.timedelta(days=1))
            duplicate_followup = process_domain_alerts(self.db, sunday + datetime.timedelta(days=1))

        self.assertEqual(first["sent_count"], 1)
        self.assertEqual(duplicate["sent_count"], 0)
        self.assertEqual(followup["sent_count"], 1)
        self.assertEqual(duplicate_followup["sent_count"], 0)
        self.assertEqual(sender.call_count, 2)
        self.assertIn("域名告警", sender.call_args_list[0].args[2])
        self.assertIn("工作日补发", sender.call_args_list[1].args[3])

    def test_domain_alert_daily_fallback_runs_at_nine(self):
        schedule = celery_app.conf.beat_schedule["check-domain-alert-every-day"]["schedule"]
        self.assertEqual(schedule.hour, {9})
        self.assertEqual(schedule.minute, {0})

    def test_2026_china_holiday_and_makeup_workday(self):
        self.assertFalse(is_workday(datetime.date(2026, 2, 16)))
        self.assertTrue(is_workday(datetime.date(2026, 2, 28)))

    def test_markdown_is_compact_and_has_no_emoji(self):
        title, markdown = build_markdown([{
            "level": "critical",
            "kind": "initial",
            "domain_name": "example.com",
            "account_alias": "测试账号",
            "expiration_date": "2026-08-10",
            "days": 3,
        }], "域名告警")

        self.assertEqual(title, "域名告警｜域名到期严重")
        self.assertTrue(markdown.startswith("#### "))
        self.assertIn("**严重（1）**", markdown)
        self.assertIn("- 账号：测试账号", markdown)
        self.assertNotRegex(markdown, "[\U0001F300-\U0001FAFF]")
