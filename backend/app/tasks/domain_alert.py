import base64
import datetime
import hashlib
import hmac
import json
import logging
import time
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from app.db.session import SessionLocal
from app.models.account import CloudAccount
from app.models.domain_alert import DomainAlertEvent, DomainAlertSetting
from app.models.resource import Resource
from app.tasks.celery_app import celery_app
from app.tasks.sync_lock import AccountSyncLock
from app.core.config import settings

logger = logging.getLogger(__name__)

LEVEL_RANK = {"reminder": 1, "warning": 2, "critical": 3}
LEVEL_LABEL = {
    "reminder": "提醒",
    "warning": "告警",
    "critical": "严重",
}


def _configured_dates(value: str) -> set[datetime.date]:
    dates = set()
    for item in filter(None, (part.strip() for part in value.split(","))):
        try:
            start_text, separator, end_text = item.partition(":")
            start = datetime.date.fromisoformat(start_text)
            end = datetime.date.fromisoformat(end_text) if separator else start
        except ValueError:
            logger.error(f"忽略无效的中国工作日历配置: {item}")
            continue
        while start <= end:
            dates.add(start)
            start += datetime.timedelta(days=1)
    return dates


def is_workday(day: datetime.date) -> bool:
    if day in _configured_dates(settings.CHINA_EXTRA_WORKDAYS):
        return True
    if day in _configured_dates(settings.CHINA_HOLIDAY_RANGES):
        return False
    return day.weekday() < 5


def parse_expiration_date(value) -> datetime.date | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.isdigit():
        timestamp = int(text)
        if timestamp > 10_000_000_000:
            timestamp //= 1000
        return datetime.datetime.fromtimestamp(timestamp).date()
    try:
        return datetime.datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def classify_domain(days: int, config: DomainAlertSetting) -> str | None:
    if days <= config.critical_days:
        return "critical"
    if days <= config.warning_days:
        return "warning"
    if days <= config.reminder_days:
        return "reminder"
    return None


def send_dingtalk_markdown(webhook: str, secret: str | None, title: str, markdown: str) -> None:
    url = webhook
    if secret:
        timestamp = str(round(time.time() * 1000))
        signature = hmac.new(
            secret.encode(),
            f"{timestamp}\n{secret}".encode(),
            digestmod=hashlib.sha256,
        ).digest()
        separator = "&" if "?" in webhook else "?"
        url = f"{webhook}{separator}timestamp={timestamp}&sign={quote_plus(base64.b64encode(signature))}"

    payload = json.dumps({
        "msgtype": "markdown",
        "markdown": {"title": title, "text": markdown},
    }, ensure_ascii=False).encode()
    request = Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=10) as response:
        result = json.loads(response.read().decode())
    if result.get("errcode") != 0:
        raise RuntimeError(result.get("errmsg") or "钉钉机器人返回失败")


def parse_domain_display(domain: str) -> str:
    if not domain:
        return ""
    if "xn--" in domain.lower():
        try:
            unicode_name = domain.encode("ascii").decode("idna")
            if unicode_name and unicode_name != domain:
                return f"{unicode_name} ({domain})"
        except Exception:
            pass
    return domain


LEVEL_EMOJI = {
    "critical": "🔴 紧急关注",
    "warning": "🟡 提醒关注",
    "reminder": "🔵 提前留意",
}

def build_markdown(items: list[dict], keyword: str) -> tuple[str, str]:
    highest = max(items, key=lambda item: LEVEL_RANK[item["level"]])["level"]
    title = f"{keyword}｜域名到期预警 ({len(items)})"
    today_str = datetime.date.today().strftime("%Y-%m-%d")

    lines = [
        f"### 🚨 {keyword} 域名到期预警通知",
        f"> **检测时间**：{today_str} ｜ **待处理**：{len(items)} 个域名",
        ""
    ]

    for level in ("critical", "warning", "reminder"):
        group = [item for item in items if item["level"] == level]
        if not group:
            continue
        tag = LEVEL_EMOJI.get(level, LEVEL_LABEL[level])
        lines.append(f"**{tag}（{len(group)}）**")

        for item in group:
            domain_str = parse_domain_display(item["domain_name"])
            days = item["days"]
            days_str = f"已过期 {-days} 天" if days < 0 else f"剩余 {days} 天"
            followup = " *(工作日补发)*" if item["kind"] == "followup" else ""

            lines.append(
                f"• **{domain_str}**{followup}\n"
                f"  `到期`: {item['expiration_date']} ｜ `状态`: **{days_str}** ｜ `账号`: {item['account_alias']}"
            )
        lines.append("")

    return title, "\n".join(lines).strip()


def process_domain_alerts(db, today: datetime.date | None = None) -> dict:
    today = today or datetime.date.today()
    config = db.query(DomainAlertSetting).filter(DomainAlertSetting.id == 1).first()
    if config is None or not config.enabled:
        return {"status": "disabled", "sent_count": 0}
    webhook = config.get_webhook()
    if not webhook:
        logger.warning("域名告警已启用，但尚未配置钉钉 Webhook。")
        return {"status": "not_configured", "sent_count": 0}

    states = {}
    rows = (
        db.query(Resource, CloudAccount.account_alias)
        .join(CloudAccount, CloudAccount.id == Resource.account_id)
        .filter(Resource.resource_type == "Domain")
        .all()
    )
    for resource, account_alias in rows:
        try:
            details = json.loads(resource.details or "{}")
        except (TypeError, json.JSONDecodeError):
            continue
        domain_name = details.get("domain_name") or resource.search_key
        expiration = parse_expiration_date(details.get("expiration_date"))
        if not domain_name or expiration is None:
            continue
        days = (expiration - today).days
        level = classify_domain(days, config)
        if level is None:
            continue
        identity = (resource.account_id, domain_name, expiration.isoformat())
        states[identity] = {
            "identity": identity,
            "account_id": resource.account_id,
            "account_alias": account_alias,
            "domain_name": domain_name,
            "expiration_date": expiration.isoformat(),
            "days": days,
            "level": level,
        }

    existing = db.query(DomainAlertEvent).all()
    existing_keys = {
        (event.account_id, event.domain_name, event.expiration_date, event.level)
        for event in existing
    }
    new_items = [
        {**state, "kind": "initial"}
        for state in states.values()
        if (*state["identity"], state["level"]) not in existing_keys
    ]

    pending = [event for event in existing if event.needs_workday_followup]
    followups = {}
    if is_workday(today):
        new_identities = {item["identity"] for item in new_items}
        for event in pending:
            identity = (event.account_id, event.domain_name, event.expiration_date)
            state = states.get(identity)
            if state is None or identity in new_identities:
                continue
            current = followups.get(identity)
            if current is None or LEVEL_RANK[state["level"]] > LEVEL_RANK[current["level"]]:
                followups[identity] = {**state, "kind": "followup"}

    items = sorted(
        new_items + list(followups.values()),
        key=lambda item: (-LEVEL_RANK[item["level"]], item["days"], item["domain_name"]),
    )[:50]
    sent_identities = {item["identity"] for item in items}

    if not items:
        if is_workday(today):
            for event in pending:
                identity = (event.account_id, event.domain_name, event.expiration_date)
                if identity not in states:
                    event.needs_workday_followup = False
                    event.workday_followup_sent_at = datetime.datetime.now()
            db.commit()
        return {"status": "no_new_alerts", "sent_count": 0}

    title, markdown = build_markdown(items, config.keyword)
    send_dingtalk_markdown(webhook, config.get_secret(), title, markdown)
    now = datetime.datetime.now()
    for item in items:
        if item["kind"] == "initial":
            db.add(DomainAlertEvent(
                account_id=item["account_id"],
                account_alias=item["account_alias"],
                domain_name=item["domain_name"],
                expiration_date=item["expiration_date"],
                level=item["level"],
                first_sent_at=now,
                needs_workday_followup=not is_workday(today),
            ))
    if is_workday(today):
        for event in pending:
            identity = (event.account_id, event.domain_name, event.expiration_date)
            if identity in sent_identities or identity not in states:
                event.needs_workday_followup = False
                event.workday_followup_sent_at = now
    db.commit()
    return {"status": "sent", "sent_count": len(items)}


@celery_app.task(name="app.tasks.domain_alert.check_domain_alert_task")
def check_domain_alert_task():
    lock = AccountSyncLock("domain-alert", timeout=300)
    if not lock.acquire():
        return {"status": "already_running", "sent_count": 0}
    db = SessionLocal()
    try:
        return process_domain_alerts(db)
    except Exception:
        db.rollback()
        logger.exception("域名到期钉钉告警任务执行失败。")
        raise
    finally:
        db.close()
        lock.release()
