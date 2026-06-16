"""热点文章相关接口。"""
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..crawler.service import refresh_hot_posts
from ..database import get_db
from ..models import HotPost
from ..schemas import PostDetail, PostOut, RefreshRequest, RefreshResult

router = APIRouter(prefix="/api/posts", tags=["posts"])


@router.post("/refresh", response_model=RefreshResult)
def refresh(
    body: Optional[RefreshRequest] = Body(default=None),
    db: Session = Depends(get_db),
):
    """抓取最新一轮热点文章。可在 body.domains 指定要抓取的领域。"""
    domains = body.domains if body else None
    result = refresh_hot_posts(db, keywords=domains)
    return RefreshResult(**result)


@router.get("", response_model=list[PostOut])
def list_posts(
    keyword: Optional[str] = Query(None, description="按关键词过滤"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """按热度倒序返回热点文章列表。"""
    q = db.query(HotPost)
    if keyword:
        q = q.filter(HotPost.keyword == keyword)
    posts = q.order_by(HotPost.hotness.desc(), HotPost.fetched_at.desc()).limit(limit).all()
    out = []
    for p in posts:
        item = PostOut.model_validate(p)
        item.rewrite_count = len(p.rewrites)
        out.append(item)
    return out


@router.get("/{post_id}", response_model=PostDetail)
def get_post(post_id: int, db: Session = Depends(get_db)):
    post = db.get(HotPost, post_id)
    if not post:
        raise HTTPException(status_code=404, detail="文章不存在")
    detail = PostDetail.model_validate(post)
    detail.rewrite_count = len(post.rewrites)
    return detail
