"""定时发布队列接口。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Rewrite, ScheduledPublish
from ..scheduler import now_local
from ..schemas import ScheduleCreate, ScheduledPublishOut

router = APIRouter(prefix="/api", tags=["schedule"])


@router.post("/rewrites/{rewrite_id}/schedule", response_model=ScheduledPublishOut)
def create_schedule(rewrite_id: int, body: ScheduleCreate, db: Session = Depends(get_db)):
    """为一篇改写排期定时发布。"""
    rw = db.get(Rewrite, rewrite_id)
    if not rw:
        raise HTTPException(status_code=404, detail="改写结果不存在")
    if body.action not in ("draft", "publish"):
        raise HTTPException(status_code=400, detail="action 只能是 draft 或 publish")
    # 允许略早于当前 1 分钟内的时间（时钟误差），更早则拒绝
    sched = body.scheduled_at.replace(tzinfo=None)
    if (sched - now_local()).total_seconds() < -60:
        raise HTTPException(status_code=400, detail="发布时间不能早于当前时间")

    sp = ScheduledPublish(
        rewrite_id=rw.id,
        action=body.action,
        scheduled_at=sched,
        status="pending",
        title_snapshot=(body.title or rw.new_title).strip(),
        content_snapshot=(body.content or rw.content).strip(),
    )
    db.add(sp)
    db.commit()
    db.refresh(sp)
    return ScheduledPublishOut.model_validate(sp)


@router.get("/schedules", response_model=list[ScheduledPublishOut])
def list_schedules(db: Session = Depends(get_db)):
    """列出所有定时发布任务，按计划时间排序。"""
    items = db.query(ScheduledPublish).order_by(ScheduledPublish.scheduled_at.asc()).all()
    return [ScheduledPublishOut.model_validate(i) for i in items]


@router.delete("/schedules/{schedule_id}")
def cancel_schedule(schedule_id: int, db: Session = Depends(get_db)):
    """取消一个待执行的定时任务。"""
    sp = db.get(ScheduledPublish, schedule_id)
    if not sp:
        raise HTTPException(status_code=404, detail="任务不存在")
    if sp.status != "pending":
        raise HTTPException(status_code=400, detail=f"任务已 {sp.status}，无法取消")
    sp.status = "canceled"
    db.commit()
    return {"ok": True}
