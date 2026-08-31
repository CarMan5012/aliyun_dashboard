import json
import logging
import datetime
import concurrent.futures
import random
import threading
import time
from app.tasks.domain_alert import trigger_domain_alert_check
from app.db.session import SessionLocal
from app.models.account import CloudAccount
from app.models.resource import Resource
from app.tasks.sync_lock import AccountSyncLock, AccountCooldown, EmptyResultGuard

# 阿里云 SDK 引用 (V3)
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_ecs20140526.client import Client as EcsClient
from alibabacloud_ecs20140526 import models as ecs_models
from alibabacloud_vpc20160428.client import Client as VpcClient
from alibabacloud_vpc20160428 import models as vpc_models
from alibabacloud_domain20180129.client import Client as DomainClient
from alibabacloud_domain20180129 import models as domain_models
from alibabacloud_cas20200407.client import Client as CasClient
from alibabacloud_cas20200407 import models as cas_models

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

db_write_lock = threading.Lock()
DEFAULT_MAIN_REGIONS = {"cn-hangzhou", "cn-beijing", "cn-shanghai", "cn-shenzhen"}

api_record_lock = threading.Lock()

def record_api_call(label: str, account_id: int = None):
    """记录一次阿里云 API 调用（持久化写入数据库，带并发线程锁）"""
    today_str = datetime.date.today().isoformat()
    service_type = "ECS"
    upper_label = label.upper()
    if "EIP" in upper_label:
        service_type = "EIP"
    elif "DOMAIN" in upper_label:
        service_type = "Domain"
    elif "CAS" in upper_label or "SSL" in upper_label:
        service_type = "SSL"
    elif "ECS" in upper_label:
        service_type = "ECS"

    with api_record_lock:
        try:
            from app.db.session import SessionLocal
            from app.models.api_call import ApiCallRecord
            db = SessionLocal()
            try:
                # 记录账号维度 (若有)
                if account_id:
                    rec = db.query(ApiCallRecord).filter(
                        ApiCallRecord.call_date == today_str,
                        ApiCallRecord.account_id == account_id,
                        ApiCallRecord.service_type == service_type
                    ).first()
                    if rec:
                        rec.call_count += 1
                    else:
                        db.add(ApiCallRecord(call_date=today_str, account_id=account_id, service_type=service_type, call_count=1))
                
                # 记录全局维度 (account_id = None)
                global_rec = db.query(ApiCallRecord).filter(
                    ApiCallRecord.call_date == today_str,
                    ApiCallRecord.account_id == None,
                    ApiCallRecord.service_type == service_type
                ).first()
                if global_rec:
                    global_rec.call_count += 1
                else:
                    db.add(ApiCallRecord(call_date=today_str, account_id=None, service_type=service_type, call_count=1))
                
                db.commit()
            except Exception as e:
                db.rollback()
                logger.debug(f"记录 API 统计回滚: {e}")
            finally:
                db.close()
        except Exception as db_err:
            logger.debug(f"持久化 API 计数异常: {db_err}")


def get_api_call_stats(db=None) -> dict:
    """获取 API 调用统计信息（支持 SQLite/MySQL 数据库持久化聚合，兼容 Redis）"""
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    services = ["ECS", "EIP", "Domain", "SSL"]
    past_7_dates = [(today - datetime.timedelta(days=i)).isoformat() for i in range(7)]
    today_str = today.isoformat()
    yesterday_str = yesterday.isoformat()

    close_db_after = False
    if db is None:
        from app.db.session import SessionLocal
        db = SessionLocal()
        close_db_after = True

    try:
        from app.models.account import CloudAccount
        from app.models.api_call import ApiCallRecord
        accounts = db.query(CloudAccount).all()

        # 1. 尝试从数据库加载近 7 天记录
        records = db.query(ApiCallRecord).filter(ApiCallRecord.call_date.in_(past_7_dates)).all()

        # 如果数据库有记录，直接聚合
        if records:
            week_total = 0
            today_total = 0
            yesterday_total = 0
            by_service = {s: 0 for s in services}
            by_account_map = {acc.id: {
                "account_id": acc.id,
                "account_alias": acc.account_alias,
                "week_total": 0,
                "today_total": 0,
                "yesterday_total": 0,
                "by_service": {s: 0 for s in services}
            } for acc in accounts}

            for r in records:
                if r.account_id is None:
                    # 全局记录
                    week_total += r.call_count
                    by_service[r.service_type] = by_service.get(r.service_type, 0) + r.call_count
                    if r.call_date == today_str:
                        today_total += r.call_count
                    elif r.call_date == yesterday_str:
                        yesterday_total += r.call_count
                else:
                    # 单账号记录
                    if r.account_id in by_account_map:
                        acc_data = by_account_map[r.account_id]
                        acc_data["week_total"] += r.call_count
                        acc_data["by_service"][r.service_type] = acc_data["by_service"].get(r.service_type, 0) + r.call_count
                        if r.call_date == today_str:
                            acc_data["today_total"] += r.call_count
                        elif r.call_date == yesterday_str:
                            acc_data["yesterday_total"] += r.call_count

            return {
                "week_total": week_total,
                "today_total": today_total,
                "yesterday_total": yesterday_total,
                "by_service": by_service,
                "by_account": list(by_account_map.values())
            }

        # 2. 数据库尚无记录时返回默认空结构
        return {
            "week_total": 0,
            "today_total": 0,
            "yesterday_total": 0,
            "by_service": {s: 0 for s in services},
            "by_account": [{
                "account_id": acc.id,
                "account_alias": acc.account_alias,
                "week_total": 0,
                "today_total": 0,
                "yesterday_total": 0,
                "by_service": {s: 0 for s in services}
            } for acc in accounts]
        }
    finally:
        if close_db_after:
            db.close()


class LockLostError(RuntimeError):
    """Raised when a sync can no longer prove it owns the account lock."""


class UnexpectedEmptyResultError(RuntimeError):
    """首次出现异常空结果时保留旧数据，等待下一次同步确认。"""


def _renew_lock_or_raise(lock: AccountSyncLock, service_name: str) -> None:
    if lock and not lock.renew():
        raise LockLostError(f"分布式锁续期失败，终止 {service_name} 同步任务以保护数据安全")

def create_client(ak: str, sk: str, endpoint: str, client_class, region_id: str = "cn-hangzhou"):
    """通用客户端创建函数"""
    config = open_api_models.Config(
        access_key_id=ak,
        access_key_secret=sk,
        endpoint=endpoint,
        region_id=region_id,
        connect_timeout=10000,
        read_timeout=30000
    )
    return client_class(config)


def classify_api_error(exc: Exception) -> str:
    data = getattr(exc, "data", None) or {}
    code = str(getattr(exc, "code", "") or data.get("Code") or data.get("code") or "")
    status_code = getattr(exc, "status_code", None) or data.get("statusCode") or data.get("status_code")
    text = f"{code} {exc}".lower()
    if any(value in text for value in ("accesspolicydenied", "accessdenied", "forbidden", "unauthorized", "nopermission")):
        return "access_denied"
    if code.lower() == "invalidaccesskeyid" or any(value in text for value in (
        "invalidaccesskeyid.notfound", "signaturedoesnotmatch", "invalidaccesskeysecret",
    )):
        return "invalid_credential"
    if any(value in text for value in ("throttl", "flowcontrol", "ratelimit", "too many requests")) or str(status_code) == "429":
        return "rate_limited"
    if str(status_code) in ("408", "500", "502", "503", "504") or any(value in text for value in (
        "timeout", "serviceunavailable", "internalerror", "connection reset",
        "ssl", "eof", "max retries exceeded", "connection refused", "connection broken",
    )):
        return "transient"
    return "unknown"


def _aliyun_call(label: str, operation, account_id: int = None):
    record_api_call(label, account_id=account_id)
    for attempt in range(3):
        try:
            return operation()
        except Exception as exc:
            category = classify_api_error(exc)
            if category not in ("rate_limited", "transient") or attempt == 2:
                raise
            delay = min(8.0, 2 ** attempt) + random.uniform(0, 0.25)
            logger.warning(f"{label} 调用失败，分类={category}，{delay:.2f} 秒后第 {attempt + 2} 次尝试: {exc}")
            time.sleep(delay)


def _replace_resources(db, account_id: int, resource_type: str, resources: list[Resource]) -> None:
    old_count = db.query(Resource).filter(
        Resource.account_id == account_id,
        Resource.resource_type == resource_type,
    ).count()
    if not EmptyResultGuard.allow_replace(account_id, resource_type, old_count, len(resources)):
        raise UnexpectedEmptyResultError(
            f"{resource_type} 首次返回空结果，已保留原有 {old_count} 条数据；下次同步仍为空才确认清空"
        )
    with db_write_lock:
        db.query(Resource).filter(
            Resource.account_id == account_id,
            Resource.resource_type == resource_type,
        ).delete()
        db.bulk_save_objects(resources)
        db.commit()

def sync_ecs(account_id: int, account_name: str, ak: str, sk: str, db, lock: AccountSyncLock = None, target_regions: set = None) -> tuple[int, set[str]]:
    try:
        _renew_lock_or_raise(lock, "ECS")
        global_client = create_client(ak, sk, 'ecs.aliyuncs.com', EcsClient, region_id='cn-hangzhou')
        region_req = ecs_models.DescribeRegionsRequest(accept_language='zh-CN')
        region_resp = _aliyun_call("ECS DescribeRegions", lambda: global_client.describe_regions(region_req), account_id=account_id)
        if not region_resp or not region_resp.body or not region_resp.body.regions:
            raise RuntimeError("无法获取阿里云 ECS 区域列表")
            
        region_map = {r.region_id: r.local_name for r in region_resp.body.regions.region}
        
        total_instances = 0
        resources_to_add = []
        failed_regions = []
        found_active_regions = set()

        for region_id, local_name in region_map.items():
            if target_regions is not None and region_id not in target_regions:
                continue

            _renew_lock_or_raise(lock, "ECS")
            try:
                client = create_client(ak, sk, f'ecs.{region_id}.aliyuncs.com', EcsClient, region_id=region_id)
                next_token = None
                while True:
                    _renew_lock_or_raise(lock, "ECS")
                    request = ecs_models.DescribeInstancesRequest(
                        region_id=region_id,
                        max_results=100,
                        next_token=next_token,
                    )
                    response = _aliyun_call(
                        f"ECS DescribeInstances {region_id}",
                        lambda: client.describe_instances(request),
                        account_id=account_id
                    )
                    if not response or not response.body:
                        raise RuntimeError(f"ECS {region_id} 返回无响应体")

                    instances = (
                        response.body.instances.instance
                        if response.body.instances and response.body.instances.instance
                        else []
                    )

                    for inst in instances:
                        found_active_regions.add(region_id)
                        public_ips = inst.public_ip_address.ip_address if inst.public_ip_address and inst.public_ip_address.ip_address else []
                        private_ips = []
                        if inst.vpc_attributes and inst.vpc_attributes.private_ip_address:
                            private_ips = inst.vpc_attributes.private_ip_address.ip_address
                        eip = inst.eip_address.ip_address if inst.eip_address and inst.eip_address.ip_address else ""

                        ips = public_ips + private_ips + ([eip] if eip else [])
                        search_key = ",".join(ips) + "," + (inst.instance_name or "")

                        details = {
                            "region_id": local_name,
                            "instance_id": inst.instance_id,
                            "instance_name": inst.instance_name,
                            "status": inst.status,
                            "public_ips": public_ips,
                            "eip": eip,
                            "private_ips": private_ips,
                            "creation_time": inst.creation_time,
                            "cpu": inst.cpu,
                            "memory": inst.memory,
                            "expired_time": inst.expired_time,
                            "charge_type": inst.instance_charge_type
                        }

                        resource = Resource(
                            account_id=account_id,
                            account_name=account_name,
                            resource_type='ECS',
                            search_key=search_key,
                            details=json.dumps(details, ensure_ascii=False)
                        )
                        resources_to_add.append(resource)
                        total_instances += 1

                    next_token = response.body.next_token
                    if not next_token:
                        break
            except LockLostError:
                raise
            except Exception as reg_exc:
                logger.warning(f"[{account_name}] ECS 区域 [{local_name} ({region_id})] 同步失败: {reg_exc}，跳过该区域继续同步其它区域")
                failed_regions.append(region_id)

        target_count = len(region_map) if target_regions is None else len([r for r in region_map if r in target_regions])
        if target_count > 0 and len(failed_regions) == target_count:
            raise RuntimeError(f"所有 ECS 选定区域均同步失败 ({len(failed_regions)} 个区域)")

        _replace_resources(db, account_id, "ECS", resources_to_add)
        if failed_regions:
            logger.warning(f"[{account_name}] ECS 部分区域同步成功, 获取到 {total_instances} 台实例 (失败区域: {failed_regions})。")
        else:
            logger.info(f"[{account_name}] ECS 同步成功, 获取到 {total_instances} 台实例。")
        return total_instances, found_active_regions
    except Exception as e:
        db.rollback()
        logger.error(f"[{account_name}] ECS 同步失败: {e}")
        raise e

def sync_eip(account_id: int, account_name: str, ak: str, sk: str, db, lock: AccountSyncLock = None, target_regions: set = None) -> tuple[int, set[str]]:
    try:
        _renew_lock_or_raise(lock, "EIP")
        ecs_client = create_client(ak, sk, 'ecs.aliyuncs.com', EcsClient, region_id='cn-hangzhou')
        region_req = ecs_models.DescribeRegionsRequest(accept_language='zh-CN')
        region_resp = _aliyun_call("EIP DescribeRegions", lambda: ecs_client.describe_regions(region_req), account_id=account_id)
        if not region_resp or not region_resp.body or not region_resp.body.regions:
            raise RuntimeError("无法获取阿里云 EIP 区域列表")
            
        region_map = {r.region_id: r.local_name for r in region_resp.body.regions.region}
        
        total_eips = 0
        resources_to_add = []
        failed_regions = []
        found_active_regions = set()

        for region_id, local_name in region_map.items():
            if target_regions is not None and region_id not in target_regions:
                continue

            _renew_lock_or_raise(lock, "EIP")
            try:
                client = create_client(ak, sk, f'vpc.{region_id}.aliyuncs.com', VpcClient, region_id=region_id)
                page_number = 1
                while True:
                    _renew_lock_or_raise(lock, "EIP")
                    request = vpc_models.DescribeEipAddressesRequest(region_id=region_id, page_size=100, page_number=page_number)
                    response = _aliyun_call(
                        f"EIP DescribeEipAddresses {region_id}",
                        lambda: client.describe_eip_addresses(request),
                        account_id=account_id
                    )
                    if not response or not response.body:
                        raise RuntimeError(f"EIP {region_id} 返回无响应体")

                    eips = (
                        response.body.eip_addresses.eip_address
                        if response.body.eip_addresses and response.body.eip_addresses.eip_address
                        else []
                    )

                    for eip in eips:
                        found_active_regions.add(region_id)
                        search_key = getattr(eip, "ip_address", "")
                        internet_charge_type = getattr(eip, "internet_charge_type", None) or getattr(eip, "charge_type", None) or getattr(eip, "instance_charge_type", None)
                        alloc_time = getattr(eip, "allocation_time", None) or getattr(eip, "create_time", None) or getattr(eip, "creation_time", None)

                        details = {
                            "allocation_id": getattr(eip, "allocation_id", ""),
                            "ip_address": getattr(eip, "ip_address", ""),
                            "status": getattr(eip, "status", ""),
                            "region_id": local_name,
                            "instance_id": getattr(eip, "instance_id", ""),
                            "bandwidth": getattr(eip, "bandwidth", ""),
                            "charge_type": internet_charge_type,
                            "internet_charge_type": internet_charge_type,
                            "allocation_time": alloc_time,
                            "creation_time": alloc_time
                        }
                        resource = Resource(
                            account_id=account_id,
                            account_name=account_name,
                            resource_type='EIP',
                            search_key=search_key,
                            details=json.dumps(details, ensure_ascii=False)
                        )
                        resources_to_add.append(resource)
                        total_eips += 1

                    if page_number * 100 >= int(response.body.total_count or 0):
                        break
                    page_number += 1
            except LockLostError:
                raise
            except Exception as reg_exc:
                logger.warning(f"[{account_name}] EIP 区域 [{local_name} ({region_id})] 同步失败: {reg_exc}，跳过该区域继续同步其它区域")
                failed_regions.append(region_id)

        target_count = len(region_map) if target_regions is None else len([r for r in region_map if r in target_regions])
        if target_count > 0 and len(failed_regions) == target_count:
            raise RuntimeError(f"所有 EIP 选定区域均同步失败 ({len(failed_regions)} 个区域)")

        _replace_resources(db, account_id, "EIP", resources_to_add)
        if failed_regions:
            logger.warning(f"[{account_name}] EIP 部分区域同步成功, 获取到 {total_eips} 个EIP (失败区域: {failed_regions})。")
        else:
            logger.info(f"[{account_name}] EIP 同步成功, 获取到 {total_eips} 个EIP。")
        return total_eips, found_active_regions
    except Exception as e:
        db.rollback()
        logger.error(f"[{account_name}] EIP 同步失败: {e}")
        raise e

def parse_domain_unicode(domain: str) -> str:
    if not domain:
        return ""
    try:
        if "xn--" in domain.lower():
            return domain.encode("ascii").decode("idna")
    except Exception:
        pass
    return domain


def sync_domain(account_id: int, account_name: str, ak: str, sk: str, db, lock: AccountSyncLock = None) -> int:
    try:
        _renew_lock_or_raise(lock, "Domain")
        client = create_client(ak, sk, 'domain.aliyuncs.com', DomainClient, region_id='cn-hangzhou')
        
        total_domains = 0
        resources_to_add = []
        page_num = 1
        while True:
            _renew_lock_or_raise(lock, "Domain")
            request = domain_models.QueryDomainListRequest(page_num=page_num, page_size=100)
            response = _aliyun_call("Domain QueryDomainList", lambda: client.query_domain_list(request), account_id=account_id)
            if not response or not response.body:
                raise RuntimeError("Domain 返回无响应体")

            domains = (
                response.body.data.domain
                if response.body.data and response.body.data.domain
                else []
            )
                
            for dom in domains:
                raw_domain = dom.domain_name or ""
                unicode_domain = parse_domain_unicode(raw_domain)
                registrant = getattr(dom, "ccompany", "") or getattr(dom, "zh_registrant_organization", "") or ""
                search_parts = [raw_domain]
                if unicode_domain and unicode_domain != raw_domain:
                    search_parts.append(unicode_domain)
                if registrant:
                    search_parts.append(registrant)
                search_key = ",".join(search_parts)
                details = {
                    "domain_name": raw_domain,
                    "domain_name_unicode": unicode_domain,
                    "registrant": registrant,
                    "domain_status": dom.domain_status,
                    "expiration_date": dom.expiration_date,
                    "registration_date": dom.registration_date
                }
                resource = Resource(
                    account_id=account_id,
                    account_name=account_name,
                    resource_type='Domain',
                    search_key=search_key,
                    details=json.dumps(details, ensure_ascii=False)
                )
                resources_to_add.append(resource)
                total_domains += 1
                
            if not response.body.next_page:
                break
            page_num += 1

        _replace_resources(db, account_id, "Domain", resources_to_add)
        logger.info(f"[{account_name}] 域名 同步成功, 获取到 {total_domains} 个域名。")
        return total_domains
    except Exception as e:
        db.rollback()
        logger.error(f"[{account_name}] 域名 同步失败: {e}")
        raise e

def sync_ssl(account_id: int, account_name: str, ak: str, sk: str, db, lock: AccountSyncLock = None) -> int:
    try:
        _renew_lock_or_raise(lock, "SSL")
        client = create_client(ak, sk, 'cas.aliyuncs.com', CasClient, region_id='cn-hangzhou')
        
        valid_certs_count = 0
        resources_to_add = []
        now = datetime.datetime.now()
        half_year_ago = now - datetime.timedelta(days=180)
        
        merged_certs = {}
        
        for ot in ["CERT", "UPLOAD"]:
            current_page = 1
            while True:
                _renew_lock_or_raise(lock, "SSL")
                request = cas_models.ListUserCertificateOrderRequest(
                    show_size=50, 
                    current_page=current_page,
                    order_type=ot
                )
                response = _aliyun_call(
                    f"SSL ListUserCertificateOrder {ot}",
                    lambda: client.list_user_certificate_order(request),
                    account_id=account_id
                )
                if not response or not response.body:
                    raise RuntimeError("SSL 返回无响应体")
                    
                certs = response.body.certificate_order_list
                if not certs:
                    break
                    
                for cert in certs:
                    inst_id = cert.instance_id
                    if not inst_id:
                        continue
                        
                    start_str = ""
                    end_str = ""
                    start_dt = None
                    end_dt = None
                    try:
                        if cert.cert_start_time:
                            start_ms = int(cert.cert_start_time)
                            start_dt = datetime.datetime.fromtimestamp(start_ms / 1000.0)
                            start_str = start_dt.strftime("%Y-%m-%d")
                        if cert.cert_end_time:
                            end_ms = int(cert.cert_end_time)
                            end_dt = datetime.datetime.fromtimestamp(end_ms / 1000.0)
                            end_str = end_dt.strftime("%Y-%m-%d")
                    except Exception:
                        if cert.cert_start_time:
                            start_str = str(cert.cert_start_time)[:10]
                        if cert.cert_end_time:
                            end_str = str(cert.cert_end_time)[:10]

                    if end_dt and end_dt < half_year_ago:
                        continue
                        
                    domain = cert.domain or getattr(cert, "common_name", None)
                    cert_name = cert.name or getattr(cert, "common_name", None) or cert.domain
                    
                    cert_type_val = "正式证书"
                    is_upload = getattr(cert, "upload", False) or ot == 'UPLOAD'
                    if is_upload:
                        cert_type_val = "自定义上传"
                    else:
                        is_free = False
                        if getattr(cert, "cert_type", None) == "FREE":
                            is_free = True
                        elif getattr(cert, "product_code", None) == "symantec-free-1-free":
                            is_free = True
                        elif getattr(cert, "product_name", None) == "Secure Site Starter":
                            is_free = True
                        elif start_dt and end_dt:
                            days_valid = (end_dt - start_dt).days
                            if 85 <= days_valid <= 95:
                                is_free = True
                        
                        if is_free:
                            cert_type_val = "个人测试"
                            
                    brand_val = getattr(cert, "root_brand", None) or getattr(cert, "issuer", None)
                    
                    if inst_id not in merged_certs:
                        merged_certs[inst_id] = {
                            "cert_name": cert_name,
                            "domain": domain,
                            "status": cert.status,
                            "buy_date": cert.buy_date,
                            "cert_start_time": start_str,
                            "cert_end_time": end_str,
                            "cert_type": cert_type_val,
                            "brand": brand_val
                        }
                    else:
                        existing = merged_certs[inst_id]
                        if not existing["cert_name"] and cert_name:
                            existing["cert_name"] = cert_name
                        if not existing["domain"] and domain:
                            existing["domain"] = domain
                        if not existing["status"] and cert.status:
                            existing["status"] = cert.status
                        if not existing["buy_date"] and cert.buy_date:
                            existing["buy_date"] = cert.buy_date
                        if not existing["cert_start_time"] and start_str:
                            existing["cert_start_time"] = start_str
                        if not existing["cert_end_time"] and end_str:
                            existing["cert_end_time"] = end_str
                        if existing["cert_type"] == "正式证书" and cert_type_val != "正式证书":
                            existing["cert_type"] = cert_type_val
                        if not existing["brand"] and brand_val:
                            existing["brand"] = brand_val
                            
                if current_page * 50 >= int(response.body.total_count or 0):
                    break
                current_page += 1
                    
        for inst_id, c_info in merged_certs.items():
            search_key = (c_info["domain"] or "") + "," + (c_info["cert_name"] or "")
            details = {
                "cert_name": c_info["cert_name"],
                "domain": c_info["domain"],
                "status": c_info["status"],
                "buy_date": c_info["buy_date"],
                "cert_start_time": c_info["cert_start_time"],
                "cert_end_time": c_info["cert_end_time"],
                "cert_type": c_info["cert_type"],
                "brand": c_info["brand"]
            }
            resource = Resource(
                account_id=account_id,
                account_name=account_name,
                resource_type='SSL',
                search_key=search_key,
                details=json.dumps(details, ensure_ascii=False)
            )
            resources_to_add.append(resource)
            valid_certs_count += 1
            
        _replace_resources(db, account_id, "SSL", resources_to_add)
        logger.info(f"[{account_name}] SSL 同步成功, 获取到 {valid_certs_count} 个符合条件的证书。")
        return valid_certs_count
    except Exception as e:
        db.rollback()
        logger.error(f"[{account_name}] SSL 同步整体失败: {e}")
        raise e

def sync_account_resources(account_id: int, lock_token_holder: AccountSyncLock = None, full_scan: bool = False):
    """
    同步指定云账号的所有资源 (包含 Redis 分布式锁与退避机制)
    """
    lock = lock_token_holder or AccountSyncLock(account_id)
    if not lock_token_holder and not lock.acquire():
        running_task = AccountSyncLock.get_running_task_id(account_id)
        msg = f"账号 ID [{account_id}] 正在同步中 (任务 ID: {running_task})"
        logger.info(msg)
        return {"status": "ALREADY_RUNNING", "message": msg, "task_id": running_task}

    db = SessionLocal()
    account = None
    try:
        account = db.query(CloudAccount).filter(CloudAccount.id == account_id).first()
        if not account:
            raise ValueError(f"同步失败: 未找到 ID 为 {account_id} 的云账号。")
        
        # 记录同步尝试时间
        account.last_attempted_at = datetime.datetime.now()
        db.commit()
        
        name = account.account_alias
        ak = account.access_key_id
        sk = account.get_secret()
        
        # 解析该账号既有的活跃地域缓存
        cached_active_regions = set()
        if getattr(account, "active_regions", None):
            try:
                cached_active_regions = set(json.loads(account.active_regions))
            except Exception:
                cached_active_regions = set()

        if not full_scan and (cached_active_regions or account.last_synced_at is not None):
            # 智能模式：仅扫描 [既有活跃地域 + 默认主地域]
            target_regions = cached_active_regions.union(DEFAULT_MAIN_REGIONS)
            logger.info(f"账号 [{name}] 开启智能活跃地域同步模式，目标地域 ({len(target_regions)}个): {sorted(list(target_regions))}")
        else:
            # 全量模式：扫描所有地域
            target_regions = None
            logger.info(f"账号 [{name}] 开启全量地域深度扫描模式...")

        logger.info(f"开始同步账号 [{name}] (ID: {account_id}) 的资源...")
        
        service_results = {}
        failed_services = []
        newly_found_active_regions = set()
        
        for sync_func, service_name in [
            (sync_ecs, "ECS"),
            (sync_eip, "EIP"),
            (sync_domain, "Domain"),
            (sync_ssl, "SSL")
        ]:
            try:
                if service_name in ("ECS", "EIP"):
                    res = sync_func(account_id, name, ak, sk, db, lock=lock, target_regions=target_regions)
                    if isinstance(res, tuple):
                        count, active_regs = res
                        newly_found_active_regions.update(active_regs)
                    else:
                        count = res
                else:
                    count = sync_func(account_id, name, ak, sk, db, lock=lock)
                service_results[service_name] = {"status": "success", "count": count}
                if service_name == "Domain":
                    trigger_domain_alert_check()
                _renew_lock_or_raise(lock, service_name)
            except LockLostError:
                raise
            except Exception as e:
                err_msg = str(e)[:1000]
                error_category = classify_api_error(e)
                logger.error(f"账号 [{name}] 同步子服务 [{service_name}] 失败: {err_msg}")
                service_results[service_name] = {
                    "status": "failure",
                    "error_category": error_category,
                    "error": err_msg,
                }
                failed_services.append(f"{service_name}: {err_msg}")

        # 实时更新该账号的活跃地域列表（全量深度模式下精确更新，智能模式下增量融合）
        if full_scan:
            account.active_regions = json.dumps(sorted(list(newly_found_active_regions)), ensure_ascii=False)
        elif newly_found_active_regions:
            merged_active = cached_active_regions.union(newly_found_active_regions)
            account.active_regions = json.dumps(sorted(list(merged_active)), ensure_ascii=False)

        if failed_services:
            permanent = any(
                result.get("error_category") in ("invalid_credential", "access_denied")
                for result in service_results.values()
            )
            AccountCooldown.set_cooldown(account_id, seconds=21600 if permanent else 900)
            err_summary = f"账号 [{name}] 同步失败，包含以下服务异常: {'; '.join(failed_services)}"
            result_status = "partial_failure" if len(failed_services) < len(service_results) else "failure"
            account.last_sync_status = result_status
            account.last_sync_error = err_summary[:2000]
            logger.error(err_summary)
        else:
            result_status = "success"
            account.last_synced_at = datetime.datetime.now()
            account.last_sync_status = "success"
            account.last_sync_error = None
            AccountCooldown.clear_cooldown(account_id)

        account.last_sync_details = json.dumps(service_results, ensure_ascii=False)
        db.commit()
        logger.info(f"账号 [{name}] 同步结束，状态={result_status}，数据统计: {service_results}")
        return {"status": result_status, "services": service_results}
    except Exception as e:
        if account is not None:
            try:
                account.last_sync_status = "failure"
                account.last_sync_error = str(e)[:2000]
                account.last_sync_details = json.dumps({
                    "system": {
                        "status": "failure",
                        "error_category": classify_api_error(e),
                        "error": str(e)[:1000],
                    }
                }, ensure_ascii=False)
                db.commit()
            except Exception as state_err:
                db.rollback()
                logger.error(f"账号 ID [{account_id}] 最近同步状态写入失败: {state_err}")
        raise
    finally:
        db.close()
        lock.release()

def sync_single_account_task(account_id: int, full_scan: bool = False):
    """同步指定云账号的所有资源 (线程级任务，带锁控制)"""
    lock = AccountSyncLock(account_id)
    if not lock.acquire():
        running_task = AccountSyncLock.get_running_task_id(account_id)
        msg = f"账号 ID [{account_id}] 已经在运行同步任务 ({running_task})，无需重复触发。"
        logger.info(msg)
        return {"status": "already_running", "running_task_id": running_task, "message": msg}

    try:
        res = sync_account_resources(account_id, lock_token_holder=lock, full_scan=full_scan)
        if isinstance(res, dict) and str(res.get("status", "")).lower() == "already_running":
            return res
        return {
            "status": res.get("status", "success"),
            "account_id": account_id,
            "results": res.get("services", res),
        }
    except Exception as e:
        logger.error(f"任务 sync_single_account_task [{account_id}] 运行失败: {e}")
        raise e


def sync_all_accounts_task():
    """同步所有已配置云账号的资源 (原生后台线程任务)"""
    logger.info("开始执行全局资源同步任务...")
    db = SessionLocal()
    try:
        accounts = db.query(CloudAccount).all()
        if not accounts:
            logger.warning("未配置任何云账号，跳过数据同步。")
            return {
                "status": "success",
                "total": 0,
                "success_count": 0,
                "failed_count": 0,
                "skipped_cooldown_count": 0,
                "already_running_count": 0,
                "details": {"success": [], "failed": [], "skipped_cooldown": [], "already_running": []}
            }
            
        account_ids = [acc.id for acc in accounts]
    finally:
        db.close()

    skipped_cooldown = []
    already_running = []
    success_accounts = []
    failed_accounts = []
    futures = {}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        for acc_id in account_ids:
            if AccountCooldown.is_in_cooldown(acc_id):
                logger.info(f"账号 ID [{acc_id}] 处于退避冷却期，全量同步自动跳过。")
                skipped_cooldown.append(acc_id)
                continue

            try:
                lock = AccountSyncLock(acc_id, timeout=1000)
                if not lock.acquire():
                    running_t = AccountSyncLock.get_running_task_id(acc_id)
                    logger.info(f"账号 ID [{acc_id}] 获取锁失败或已经在任务中运行，跳过全量触发。")
                    already_running.append(acc_id)
                    continue
            except Exception as lock_err:
                logger.error(f"账号 ID [{acc_id}] 锁异常: {lock_err}")
                failed_accounts.append({"account_id": acc_id, "error": str(lock_err)})
                continue

            f = executor.submit(sync_account_resources, acc_id, lock_token_holder=lock)
            futures[f] = acc_id
            time.sleep(1)
            
    for f in concurrent.futures.as_completed(futures):
        acc_id = futures[f]
        try:
            res = f.result()
            result_status = str(res.get("status", "")).lower() if isinstance(res, dict) else "success"
            if result_status == "already_running":
                already_running.append(acc_id)
            elif result_status in ("partial_failure", "failure"):
                failed_accounts.append({
                    "account_id": acc_id,
                    "status": result_status,
                    "services": res.get("services", {}),
                })
            else:
                success_accounts.append(acc_id)
                logger.info(f"账号 ID [{acc_id}] 资源同步完成。")
        except Exception as e:
            logger.error(f"账号 ID [{acc_id}] 资源同步失败: {e}")
            failed_accounts.append({"account_id": acc_id, "error": str(e)})
            
    status_str = "success"
    if failed_accounts:
        status_str = "partial_failure"
    elif len(success_accounts) < len(account_ids):
        if len(success_accounts) == 0:
            status_str = "completed_with_skips" if skipped_cooldown else "already_running"
        else:
            status_str = "partial_success"

    result = {
        "status": status_str,
        "total": len(account_ids),
        "success_count": len(success_accounts),
        "failed_count": len(failed_accounts),
        "skipped_cooldown_count": len(skipped_cooldown),
        "already_running_count": len(already_running),
        "details": {
            "success": success_accounts,
            "failed": failed_accounts,
            "skipped_cooldown": skipped_cooldown,
            "already_running": already_running
        }
    }
    if failed_accounts:
        logger.warning(f"全量同步完成，存在 {len(failed_accounts)} 个账号失败。")
    else:
        logger.info(f"全局资源同步任务完成，状态: {status_str}")
    return result


def cron_sync_accounts_by_interval_task(target_interval: int):
    """
    内置定时调度器整点派发相应周期的云账号同步任务（错峰多线程执行）
    """
    logger.info(f"[调度器] 整点触发 [{target_interval}小时周期] 的账号同步...")
    db = SessionLocal()
    triggered_count = 0
    try:
        accounts = db.query(CloudAccount).filter(CloudAccount.sync_interval == target_interval).all()
        for acc in accounts:
            if AccountCooldown.is_in_cooldown(acc.id):
                logger.info(f"账号 [{acc.account_alias}] 处于失败退避冷却中，跳过本次调度触发。")
                continue

            running_task = AccountSyncLock.get_running_task_id(acc.id)
            if running_task:
                logger.info(f"账号 [{acc.account_alias}] 正在执行同步，跳过重复调度。")
                continue

            # 错峰异步启动守护线程
            delay_sec = ((acc.id - 1) % 6) * 5
            def _delayed_sync(a_id=acc.id, d=delay_sec):
                if d > 0:
                    time.sleep(d)
                sync_account_resources(a_id, full_scan=False)

            threading.Thread(target=_delayed_sync, daemon=True).start()
            triggered_count += 1
            logger.info(f"[调度器] 已派发账号 [{acc.account_alias}] 的同步线程 (延迟 {delay_sec}s 错峰执行)")

        return f"Triggered {triggered_count} accounts for interval {target_interval}h"
    except Exception as e:
        logger.error(f"[调度器] 定时触发任务失败 (interval {target_interval}h): {e}")
        raise e
    finally:
        db.close()

