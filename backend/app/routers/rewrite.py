"""改写相关接口。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import HotPost, Rewrite
from ..rewriter.service import LLMNotConfigured, rewrite as run_rewrite
from ..schemas import RewriteOut, RewriteRequest

router = APIRouter(prefix="/api/posts", tags=["rewrite"])


@router.post("/{post_id}/rewrite", response_model=RewriteOut)
def create_rewrite(
    post_id: int,
    body: RewriteRequest,
    db: Session = Depends(get_db),
):
    """对指定文章做一次改写，结果落库后返回。"""
    post = db.get(HotPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")

    source_text = post.content or post.summary or post.title
    try:
        result = run_rewrite(
            title=post.title,
            account=post.account,
            content=source_text,
            style=body.style,
            extra_instruction=body.extra_instruction,
        )
    except LLMNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception as exc:  # noqa: BLE001  把模型/网络错误转成可读信息
        raise HTTPException(status_code=502, detail=f"改写失败：{exc}")

    rw = Rewrite(
        post_id=post.id,
        style=body.style,
        new_title=result["new_title"],
        title_options=json.dumps(result.get("title_options", []), ensure_ascii=False),
        content=result["content"],
        similarity=result["similarity"],
        model=result["model"],
    )
    db.add(rw)
    db.commit()
    db.refresh(rw)
    return RewriteOut.model_validate(rw)


@router.get("/{post_id}/rewrites", response_model=list[RewriteOut])
def list_rewrites(post_id: int, db: Session = Depends(get_db)):
    post = db.get(HotPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")
    items = sorted(post.rewrites, key=lambda r: r.created_at, reverse=True)
    return [RewriteOut.model_validate(r) for r in items]
