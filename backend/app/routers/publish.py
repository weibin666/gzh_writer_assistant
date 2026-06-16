"""发布相关接口：把改写结果推送到公众号草稿箱。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Rewrite
from ..publisher.image import ImageError, generate_cover
from ..publisher.service import execute_publish
from ..publisher.wechat import WeChatError
from ..scheduler import schedule_status

router = APIRouter(prefix="/api", tags=["publish"])


class DraftBody(BaseModel):
    # 允许传入页面上手动编辑后的内容；不传则用库里的原始改写结果
    title: str = ""
    content: str = ""


class DraftResult(BaseModel):
    media_id: str
    message: str = "已存入公众号草稿箱，请到后台确认排版后群发。"


class CoverResult(BaseModel):
    url: str
    message: str = "封面已生成，存草稿时会自动用作文章封面。"


@router.post("/rewrites/{rewrite_id}/cover", response_model=CoverResult)
def make_cover(rewrite_id: int, db: Session = Depends(get_db)):
    """为改写结果生成 AI 封面图。"""
    rw = db.get(Rewrite, rewrite_id)
    if not rw:
        raise HTTPException(status_code=404, detail="改写结果不存在")
    try:
        cover = generate_cover(rw.new_title)
    except ImageError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"生成封面失败：{exc}")
    rw.cover_url = cover["url"]
    rw.cover_path = cover["path"]
    rw.cover_media_id = ""  # 重新生成后清掉旧的素材 id
    db.commit()
    return CoverResult(url=cover["url"])


@router.post("/rewrites/{rewrite_id}/draft", response_model=DraftResult)
def push_draft(rewrite_id: int, body: DraftBody = DraftBody(), db: Session = Depends(get_db)):
    rw = db.get(Rewrite, rewrite_id)
    if not rw:
        raise HTTPException(status_code=404, detail="改写结果不存在")
    try:
        result = execute_publish(db, rw, action="draft", title=body.title, content=body.content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except WeChatError as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"存草稿失败：{exc}")
    return DraftResult(media_id=result["media_id"])


@router.get("/schedule")
def get_schedule():
    """查看定时抓取状态与下次运行时间。"""
    return schedule_status()
