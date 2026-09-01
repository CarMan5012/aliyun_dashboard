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

def _smooth_batch_sync(account_ids: list[int], interval_label: str):
    """
    后台异步平滑队列：按序推进多账号同步，并在账号之间提供微缓冲，
    防止多账号瞬时并发击穿阿里云 OpenAPI 限流及 SQLite 数据库写锁。
    """
    total = len(account_ids)
    logger.info(f"[内置调度器] 开始平滑执行【{interval_label}】异步同步队列，共 {total} 个账号...")
    
    for idx, acc_id in enumerate(account_ids, start=1):
        try:
            if AccountCooldown.is_in_cooldown(acc_id):
                logger.info(f"[内置调度器] 账号 ID={acc_id} ({idx}/{total}) 处于失败退避冷却期，跳过本次定时同步。")
                continue
            
            running_task = AccountSyncLock.get_running_task_id(acc_id)
            if running_task:
                logger.info(f"[内置调度器] 账号 ID={acc_id} ({idx}/{total}) 正在执行同步中，跳过重复调度。")
                continue
            
            logger.info(f"[内置调度器] 正在执行账号 ID={acc_id} ({idx}/{total}) 资产同步...")
            sync_account_resources(acc_id, full_scan=False)
            
            # 账号间预留 1.5 秒微缓冲，避免触发 QPS 尖峰
            if idx < total:
                time.sleep(1.5)
        except Exception as e:
            logger.error(f"[内置调度器] 账号 ID={acc_id} 同步执行异常: {e}")
            
    logger.info(f"[内置调度器] 【{interval_label}】异步同步队列全部处理完毕。")


def _run_scheduled_sync(target_interval: int, interval_label: str = None):
    """筛选目标周期的云账号并派发到单 Worker 异步平滑队列"""
    if interval_label is None:
        interval_label = f"{target_interval}小时周期"

    db = SessionLocal()
    try:
        accounts = db.query(CloudAccount).filter(CloudAccount.sync_interval == target_interval).all()
        if accounts:
            account_ids = [acc.id for acc in accounts]
            logger.info(f"[内置调度器] 捕获到 {len(account_ids)} 个账号需执行【{interval_label}】定时同步，派发异步平滑队列...")
            threading.Thread(
                target=_smooth_batch_sync,
                args=[account_ids, interval_label],
                daemon=True,
                name=f"SchedulerBatchSync-{target_interval}"
            ).start()
        else:
            logger.debug(f"[内置调度器] 当前无配置为【{interval_label}】的账号，跳过执行。")
    except Exception as e:
        logger.error(f"[内置调度器] 派发定时同步任务异常 ({interval_label}): {e}")
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
    last_night_sync_date = None
    last_alert_triggered_date = None

    while True:
        try:
            now = datetime.datetime.now()
            current_hour = now.hour
            current_minute = now.minute
            current_date = now.date()

            # 每天凌晨 03:00 整点触发低频/避峰同步检查 (current_hour == 3 and current_minute == 0)
            if current_hour == 3 and current_minute == 0 and current_date != last_night_sync_date:
                last_night_sync_date = current_date
                logger.info(f"[内置调度器] 触发凌晨 03:00 业务低峰期定时同步检查 (日期: {current_date})...")

                # 1. 每天凌晨自动同步 (sync_interval = 24)
                _run_scheduled_sync(24, "每天凌晨同步")

                # 2. 每周一凌晨同步 (sync_interval = 168, weekday == 0 为周一)
                if now.weekday() == 0:
                    logger.info("[内置调度器] 今日为周一，派发每周一凌晨自动同步任务...")
                    _run_scheduled_sync(168, "每周一凌晨同步")

                # 3. 每月 1 号凌晨同步 (sync_interval = 720, day == 1 为每月第一天)
                if now.day == 1:
                    logger.info("[内置调度器] 今日为当月 1 号，派发每月 1 号凌晨自动同步任务...")
                    _run_scheduled_sync(720, "每月 1 号凌晨同步")

            # 每天上午 09:00 执行域名到期钉钉预警检查
            if current_hour == 9 and current_minute == 0 and current_date != last_alert_triggered_date:
                last_alert_triggered_date = current_date
                _run_scheduled_domain_alert()

        except Exception as e:
            logger.error(f"[内置调度器] 调度主循环异常: {e}")

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
