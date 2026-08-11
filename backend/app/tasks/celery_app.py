import logging
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "assetvista_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    imports=["app.tasks.aliyun_sync", "app.tasks.domain_alert"],
    beat_schedule={
        "cron-sync-every-1-hour": {
            "task": "app.tasks.aliyun_sync.cron_sync_accounts_by_interval_task",
            "schedule": crontab(minute=0),  # 每小时整点触发 (如 1:00, 2:00)
            "args": [1],
        },
        "cron-sync-every-6-hours": {
            "task": "app.tasks.aliyun_sync.cron_sync_accounts_by_interval_task",
            "schedule": crontab(minute=0, hour="*/6"),  # 每 6 小时整点触发 (0:00, 6:00, 12:00, 18:00)
            "args": [6],
        },
        "cron-sync-every-12-hours": {
            "task": "app.tasks.aliyun_sync.cron_sync_accounts_by_interval_task",
            "schedule": crontab(minute=0, hour="*/12"),  # 每 12 小时整点触发 (0:00, 12:00)
            "args": [12],
        },
        "cron-sync-every-24-hours": {
            "task": "app.tasks.aliyun_sync.cron_sync_accounts_by_interval_task",
            "schedule": crontab(minute=0, hour=0),  # 每天凌晨 0 点触发
            "args": [24],
        },
        "check-domain-alert-every-day": {
            "task": "app.tasks.domain_alert.check_domain_alert_task",
            "schedule": crontab(hour=9, minute=0),
        },
    }
)


def enqueue_domain_alert_check() -> None:
    try:
        celery_app.send_task("app.tasks.domain_alert.check_domain_alert_task")
    except Exception:
        logger.exception("域名告警检查任务入队失败。")
