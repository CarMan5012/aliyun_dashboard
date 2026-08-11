import logging
from datetime import timedelta
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
        "check-and-trigger-sync-every-5-minutes": {
            "task": "app.tasks.aliyun_sync.check_and_trigger_sync_task",
            "schedule": timedelta(minutes=5),
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
