"""内容合规检测接口。"""
from __future__ import annotations

from fastapi import APIRouter

from ..moderation.sensitive import check
from ..schemas import TextCheckRequest

router = APIRouter(prefix="/api/moderation", tags=["moderation"])


@router.post("/check")
def check_text(body: TextCheckRequest):
    """扫描标题+正文中的敏感词 / 违规用语。"""
    combined = f"{body.title}\n{body.content}"
    return check(combined)
