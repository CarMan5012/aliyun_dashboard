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
from app.models.account import CloudAccount

class TestP0P1Fixes(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_update_account_secret_no_500(self):
        """测试 1：修改 AccessKey Secret 使用真实的 CloudAccount 实例，避免访问不存在的属性报 500"""
        from app.db.session import get_db
        
        mock_acc = CloudAccount(
            id=123,
            account_alias="真实测试账号",
            access_key_id="LTAI_ORIGINAL",
            sync_interval=24
        )
        mock_acc.set_secret("SECRET_ORIGINAL")

        with patch("app.api.v1.accounts.crud_account.get_account", return_value=mock_acc), \
             patch("app.api.v1.accounts.crud_account.get_account_by_alias", return_value=None), \
             patch("app.api.v1.accounts.crud_account.update_account", return_value=mock_acc), \
             patch("app.api.v1.accounts.sync_single_account_task.delay") as mock_delay:

            mock_task = MagicMock()
            mock_task.id = "mock-task-123"
            mock_delay.return_value = mock_task

            app.dependency_overrides[get_db] = lambda: MagicMock()

            payload = {
                "account_alias": "真实测试账号",
                "access_key_id": "LTAI_ORIGINAL",
                "access_key_secret": "NEW_SECRET_123",
                "sync_interval": 24
            }
            res = self.client.put("/api/v1/accounts/123", json=payload)
            self.assertEqual(res.status_code, 200)
            body = res.json()
            self.assertEqual(body["status"], "success")
            self.assertTrue(body["sync_queued"])
            self.assertNotIn("encrypted_secret_key", res.text)
            self.assertNotIn("access_key_secret", res.text)
            mock_delay.assert_called_once_with(123)

    def test_redis_lock_lua_atomic_acquire(self):
        """测试 2：AccountSyncLock.acquire 使用 Lua 脚本原子设置锁与 task_id"""
        account_id = 8888
        lock = AccountSyncLock(account_id, timeout=1000)

        called_args = []
        def mock_eval(script, numkeys, *keys_and_args):
            called_args.append((script, numkeys, keys_and_args))
            return 1

        mock_r = MagicMock()
        mock_r.eval.side_effect = mock_eval

        with patch("app.tasks.sync_lock.get_redis_client", return_value=mock_r):
            acquired = lock.acquire(task_id="task-999")
            self.assertTrue(acquired)
            self.assertEqual(len(called_args), 1)
            script, numkeys, args = called_args[0]
            self.assertEqual(numkeys, 2)
            self.assertEqual(args[0], f"sync_lock:account:{account_id}")
            self.assertEqual(args[1], f"sync_task_id:account:{account_id}")
            self.assertEqual(args[4], "task-999")

    def test_renew_failure_aborts_sync(self):
        """测试 3：同步过程中锁续租失败立即抛出 RuntimeError 终止同步"""
        from app.tasks.aliyun_sync import LockLostError, sync_account_resources

        mock_lock = MagicMock()
        mock_lock.renew.return_value = False

        mock_acc = CloudAccount(
            id=1,
            account_alias="续租失败账号",
            access_key_id="LTAI_RENEW_FAIL",
            sync_interval=24
        )
        mock_acc.set_secret("SECRET_RENEW_FAIL")

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = mock_acc

        with patch("app.tasks.aliyun_sync.SessionLocal", return_value=mock_db), \
             patch("app.tasks.aliyun_sync.sync_ecs", side_effect=LockLostError("分布式锁续期失败，终止同步以保护数据安全")), \
             patch("app.tasks.aliyun_sync.sync_eip") as mock_eip, \
             patch("app.tasks.aliyun_sync.sync_domain") as mock_domain, \
             patch("app.tasks.aliyun_sync.sync_ssl") as mock_ssl, \
             patch("app.tasks.aliyun_sync.AccountCooldown.is_in_cooldown", return_value=False):
            with self.assertRaises(LockLostError) as ctx:
                sync_account_resources(account_id=1, lock_token_holder=mock_lock)
            self.assertIn("分布式锁续期失败", str(ctx.exception))
            mock_eip.assert_not_called()
            mock_domain.assert_not_called()
            mock_ssl.assert_not_called()

    def test_global_sync_reports_lock_infrastructure_failure(self):
        from app.tasks.aliyun_sync import sync_all_accounts_task

        mock_acc = MagicMock()
        mock_acc.id = 42
        mock_db = MagicMock()
        mock_db.query.return_value.all.return_value = [mock_acc]

        with patch("app.tasks.aliyun_sync.SessionLocal", return_value=mock_db), \
             patch("app.tasks.aliyun_sync.AccountCooldown.is_in_cooldown", return_value=False), \
             patch("app.tasks.aliyun_sync.AccountSyncLock.acquire", side_effect=RedisInfrastructureError("redis down")):
            result = sync_all_accounts_task.run()

        self.assertEqual(result["status"], "partial_failure")
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["details"]["failed"][0]["account_id"], 42)

    def test_account_response_has_no_secret_leak(self):
        """测试 4：断言账号创建/更新/列表响应中绝对不泄露 encrypted_secret_key 或 access_key_secret"""
        from app.db.session import get_db
        mock_acc = CloudAccount(
            id=77,
            account_alias="密文校验账号",
            access_key_id="LTAI_SECRET_CHECK",
            sync_interval=24
        )
        mock_acc.set_secret("SUPER_SECRET_KEY_123")

        with patch("app.api.v1.accounts.crud_account.get_accounts", return_value=[mock_acc]), \
             patch("app.api.v1.accounts.crud_account.get_account", return_value=mock_acc), \
             patch("app.api.v1.accounts.crud_account.create_account", return_value=mock_acc):

            app.dependency_overrides[get_db] = lambda: MagicMock()

            res_list = self.client.get("/api/v1/accounts")
            json_str1 = res_list.text
            self.assertNotIn("encrypted_secret_key", json_str1)
            self.assertNotIn("access_key_secret", json_str1)
            self.assertIn("LTAI_SECRET_CHECK", json_str1)

            res_single = self.client.get("/api/v1/accounts/77")
            json_str2 = res_single.text
            self.assertNotIn("encrypted_secret_key", json_str2)
            self.assertNotIn("access_key_secret", json_str2)

    def test_classify_api_error_ssl_and_max_retries(self):
        """测试 5：验证 SSLEOFError 及 Max retries exceeded 被归类为 transient 临时网络错误"""
        from app.tasks.aliyun_sync import classify_api_error
        ssl_err = Exception("HTTPSConnectionPool(host='ecs.cn-hongkong.aliyuncs.com', port=443): Max retries exceeded with url: /?MaxResults=100&RegionId=cn-hongkong (Caused by SSLError(SSLEOFError(8, '[SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol (_ssl.c:1017)')))")
        self.assertEqual(classify_api_error(ssl_err), "transient")

    def test_sync_ecs_single_region_fault_tolerance(self):
        """测试 6：验证单地域（如 cn-hongkong）报错时，ECS 同步能跳过故障地域并完成其他地域同步"""
        from app.tasks.aliyun_sync import sync_ecs

        region_hangzhou = MagicMock(region_id="cn-hangzhou", local_name="华东1（杭州）")
        region_hongkong = MagicMock(region_id="cn-hongkong", local_name="中国香港")
        region_resp = MagicMock()
        region_resp.body.regions.region = [region_hangzhou, region_hongkong]

        inst_mock = MagicMock()
        inst_mock.instance_id = "i-hz123"
        inst_mock.instance_name = "杭州测试机"
        inst_mock.status = "Running"
        inst_mock.public_ip_address.ip_address = ["1.2.3.4"]
        inst_mock.vpc_attributes.private_ip_address.ip_address = ["192.168.1.1"]
        inst_mock.eip_address.ip_address = ""
        inst_mock.creation_time = "2026-01-01T00:00Z"
        inst_mock.cpu = 2
        inst_mock.memory = 4096
        inst_mock.expired_time = "2027-01-01T00:00Z"
        inst_mock.instance_charge_type = "PrePaid"

        hz_resp = MagicMock()
        hz_resp.body.instances.instance = [inst_mock]
        hz_resp.body.next_token = None

        def mock_create_client(ak, sk, endpoint, client_class, region_id="cn-hangzhou"):
            client = MagicMock()
            if region_id == "cn-hangzhou" and "ecs.aliyuncs.com" in endpoint:
                client.describe_regions.return_value = region_resp
            elif region_id == "cn-hangzhou":
                client.describe_instances.return_value = hz_resp
            elif region_id == "cn-hongkong":
                client.describe_instances.side_effect = Exception("SSLEOFError in hongkong")
            return client

        mock_db = MagicMock()
        mock_db.query.return_value.filter.return_value.count.return_value = 0

        with patch("app.tasks.aliyun_sync.create_client", side_effect=mock_create_client), \
             patch("app.tasks.aliyun_sync._replace_resources") as mock_replace:
            total, active_regs = sync_ecs(1, "测试账号", "ak", "sk", mock_db)
            self.assertEqual(total, 1)
            self.assertIn("cn-hangzhou", active_regs)
            mock_replace.assert_called_once()
            resources = mock_replace.call_args[0][3]
            self.assertEqual(len(resources), 1)
            self.assertEqual(resources[0].resource_type, "ECS")

    def test_sync_ecs_all_regions_failed_raises(self):
        """测试 7：验证所有选定地域均失败时，sync_ecs 正确抛出 RuntimeError"""
        from app.tasks.aliyun_sync import sync_ecs

        region_hk = MagicMock(region_id="cn-hongkong", local_name="中国香港")
        region_resp = MagicMock()
        region_resp.body.regions.region = [region_hk]

        def mock_create_client(ak, sk, endpoint, client_class, region_id="cn-hangzhou"):
            client = MagicMock()
            if "ecs.aliyuncs.com" in endpoint:
                client.describe_regions.return_value = region_resp
            else:
                client.describe_instances.side_effect = Exception("SSL Failure")
            return client

        mock_db = MagicMock()
        with patch("app.tasks.aliyun_sync.create_client", side_effect=mock_create_client):
            with self.assertRaises(RuntimeError) as ctx:
                sync_ecs(1, "测试账号", "ak", "sk", mock_db)
            self.assertIn("所有 ECS 选定区域均同步失败", str(ctx.exception))

    def test_sync_ecs_target_regions_filtering(self):
        """测试 8：验证指定 target_regions 时，sync_ecs 不会发起目标外地域（如 cn-hongkong）的请求"""
        from app.tasks.aliyun_sync import sync_ecs

        region_hangzhou = MagicMock(region_id="cn-hangzhou", local_name="华东1（杭州）")
        region_hongkong = MagicMock(region_id="cn-hongkong", local_name="中国香港")
        region_resp = MagicMock()
        region_resp.body.regions.region = [region_hangzhou, region_hongkong]

        requested_endpoints = []

        def mock_create_client(ak, sk, endpoint, client_class, region_id="cn-hangzhou"):
            requested_endpoints.append(endpoint)
            client = MagicMock()
            if "ecs.aliyuncs.com" == endpoint:
                client.describe_regions.return_value = region_resp
            else:
                client.describe_instances.return_value = MagicMock(body=MagicMock(instances=MagicMock(instance=[]), next_token=None))
            return client

        mock_db = MagicMock()
        with patch("app.tasks.aliyun_sync.create_client", side_effect=mock_create_client), \
             patch("app.tasks.aliyun_sync._replace_resources"):
            total, active_regs = sync_ecs(1, "测试账号", "ak", "sk", mock_db, target_regions={"cn-hangzhou"})
            self.assertEqual(total, 0)
            self.assertIn("ecs.cn-hangzhou.aliyuncs.com", requested_endpoints)
            self.assertNotIn("ecs.cn-hongkong.aliyuncs.com", requested_endpoints)

if __name__ == "__main__":
    unittest.main()
