"""后台定时任务：
1. 每天自动抓取一轮热点（可选，SCHEDULE_ENABLED）；
2. 每分钟检查定时发布队列，到点自动存草稿 / 发表（始终开启）。
"""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .config import settings
from .crawler.service import refresh_hot_posts
from .database import SessionLocal

logger = logging.getLogger(__name__)

TZ = ZoneInfo("Asia/Shanghai")
_scheduler: BackgroundScheduler | None = None
REFRESH_JOB_ID = "daily_refresh"
PUBLISH_JOB_ID = "due_publishes"


def now_local() -> datetime:
    """当前本地时间（Asia/Shanghai，naive，便于与库里 scheduled_at 比较）。"""
    return datetime.now(TZ).replace(tzinfo=None)


def _refresh_job():
    db = SessionLocal()
    try:
        result = refresh_hot_posts(db)
        logger.info("定时抓取完成：%s", result)
    except Exception as exc:  # noqa: BLE001  定时任务异常不应让进程挂掉
        logger.exception("定时抓取失败：%s", exc)
    finally:
        db.close()


def _publish_job():
    """执行所有已到期的定时发布任务。"""
    from .models import ScheduledPublish
    from .publisher.service import execute_publish

    db = SessionLocal()
    try:
        due = (
            db.query(ScheduledPublish)
            .filter(
                ScheduledPublish.status == "pending",
                ScheduledPublish.scheduled_at <= now_local(),
            )
            .all()
        )
        for sp in due:
            try:
                result = execute_publish(
                    db,
                    sp.rewrite,
                    action=sp.action,
                    title=sp.title_snapshot,
                    content=sp.content_snapshot,
                )
                sp.status = "done"
                sp.result = result.get("message", "完成")
            except Exception as exc:  # noqa: BLE001  单条失败不影响其它
                sp.status = "failed"
                sp.result = f"{exc}"
                logger.warning("定时发布失败 id=%s: %s", sp.id, exc)
            sp.executed_at = now_local()
            db.commit()
        if due:
            logger.info("定时发布处理 %d 条", len(due))
    except Exception as exc:  # noqa: BLE001
        logger.exception("定时发布轮询失败：%s", exc)
    finally:
        db.close()


def start_scheduler():
    global _scheduler
    if _scheduler:
        return
    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")

    # 定时发布队列：每分钟检查一次
    _scheduler.add_job(
        _publish_job, trigger=IntervalTrigger(seconds=60), id=PUBLISH_JOB_ID, replace_existing=True
    )

    # 每日抓取（可选）
    if settings.schedule_enabled:
        _scheduler.add_job(
            _refresh_job,
            trigger=CronTrigger(hour=settings.schedule_hour, minute=settings.schedule_minute),
            id=REFRESH_JOB_ID,
            replace_existing=True,
        )
        logger.info(
            "定时抓取已启用：每天 %02d:%02d（Asia/Shanghai）",
            settings.schedule_hour,
            settings.schedule_minute,
        )
    else:
        logger.info("定时抓取未启用（SCHEDULE_ENABLED=false）")

    _scheduler.start()
    logger.info("定时发布队列已启动（每分钟检查）")


def schedule_status() -> dict:
    running = bool(_scheduler and _scheduler.running)
    next_run = None
    if running:
        job = _scheduler.get_job(REFRESH_JOB_ID)
        if job and job.next_run_time:
            next_run = job.next_run_time.isoformat()
    return {
        "enabled": settings.schedule_enabled,
        "running": running,
        "hour": settings.schedule_hour,
        "minute": settings.schedule_minute,
        "next_run": next_run,
    }
