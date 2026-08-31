import time
import threading
import datetime
import logging
from app.db.session import SessionLocal
from app.models.account import CloudAccount
from app.tasks.sync_lock import AccountSyncLock, AccountCooldown
from app.tasks.aliyun_sync import sync_account_resources
from app.tasks.domain_alert import process_domain_alerts

logger = logging.getLogger("app.scheduler")

_scheduler_started = False
_scheduler_lock = threading.Lock()

def _run_scheduled_sync(target_interval: int):
    """触发指定小时周期的账号同步"""
    db = SessionLocal()
    try:
        accounts = db.query(CloudAccount).filter(CloudAccount.sync_interval == target_interval).all()
        for acc in accounts:
            if AccountCooldown.is_in_cooldown(acc.id):
                logger.info(f"[内置调度器] 账号 [{acc.account_alias}] 处于失败冷却期，跳过本次定时同步。")
                continue
            running_task = AccountSyncLock.get_running_task_id(acc.id)
            if running_task:
                logger.info(f"[内置调度器] 账号 [{acc.account_alias}] 正在同步中，跳过重复触发。")
                continue
            logger.info(f"[内置调度器] 定时触发账号 [{acc.account_alias}] 资源同步 (周期: {target_interval}小时)")
            threading.Thread(target=sync_account_resources, args=[acc.id], kwargs={"full_scan": False}, daemon=True).start()
    except Exception as e:
        logger.error(f"[内置调度器] 账号定时同步执行异常 ({target_interval}h): {e}")
    finally:
        db.close()

def _run_scheduled_domain_alert():
    """触发每日域名告警检查"""
    db = SessionLocal()
    try:
        logger.info("[内置调度器] 正在执行每日域名到期预警检查...")
        res = process_domain_alerts(db)
        logger.info(f"[内置调度器] 域名到期告警检查完成: {res}")
    except Exception as e:
        logger.error(f"[内置调度器] 域名到期告警检查异常: {e}")
    finally:
        db.close()

def _scheduler_loop():
    logger.info("[内置调度器] 单机轻量后台定时调度器已就绪并启动运行")
    last_triggered_hour = -1
    last_alert_triggered_date = None

    while True:
        try:
            now = datetime.datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            current_date = now.date()

            # 每小时整点触发 (current_minute == 0)
            if current_minute == 0 and current_hour != last_triggered_hour:
                last_triggered_hour = current_hour
                
                # 1小时周期账号同步
                _run_scheduled_sync(1)
                
                # 6小时周期 (0, 6, 12, 18点)
                if current_hour % 6 == 0:
                    _run_scheduled_sync(6)
                    
                # 12小时周期 (0, 12点)
                if current_hour % 12 == 0:
                    _run_scheduled_sync(12)
                    
                # 24小时周期 (每天 0点)
                if current_hour == 0:
                    _run_scheduled_sync(24)

            # 每天上午 9:00 执行域名到期钉钉预警检查
            if current_hour == 9 and current_minute == 0 and current_date != last_alert_triggered_date:
                last_alert_triggered_date = current_date
                _run_scheduled_domain_alert()

        except Exception as e:
            logger.error(f"[内置调度器] 调度循环异常: {e}")

        # 每 20 秒轮询检测
        time.sleep(20)

def start_lightweight_scheduler():
    """启动内置轻量调度线程（单例守护线程）"""
    global _scheduler_started
    with _scheduler_lock:
        if not _scheduler_started:
            _scheduler_started = True
            t = threading.Thread(target=_scheduler_loop, daemon=True, name="LightweightSchedulerThread")
            t.start()
