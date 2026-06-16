"""抓取编排：调用数据源 → 去重 → 入库。"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..config import settings
from ..models import HotPost
from .base import BaseSource, RawPost
from .mock import MockSource
from .newrank import NewRankSource
from .sogou import SogouSource

logger = logging.getLogger(__name__)


def _build_primary_source() -> BaseSource:
    """按配置选择主数据源。"""
    if settings.crawl_source == "newrank":
        return NewRankSource(
            api_key=settings.newrank_api_key,
            endpoint=settings.newrank_endpoint,
            limit=settings.newrank_limit,
            timeout=settings.http_timeout,
        )
    return SogouSource(
        pages_per_keyword=settings.crawl_pages_per_keyword,
        timeout=settings.http_timeout,
    )


def _to_model(raw: RawPost) -> HotPost:
    return HotPost(
        title=raw.title,
        account=raw.account,
        url=raw.url,
        summary=raw.summary,
        content=raw.content,
        keyword=raw.keyword,
        source=raw.source,
        hotness=raw.hotness,
        published_at=raw.published_at,
        fingerprint=raw.fingerprint(),
    )


def refresh_hot_posts(db: Session) -> dict:
    """抓取一轮热点并写入数据库，返回统计信息。"""
    keywords = settings.keywords
    primary = _build_primary_source()
    raw_posts = primary.fetch(keywords)
    used_source = primary.name
    message = ""

    if not raw_posts and settings.use_mock_fallback:
        logger.info("%s 未返回数据，回退到内置示例数据源", primary.name)
        raw_posts = MockSource().fetch(keywords)
        used_source = "mock"
        message = f"{primary.name} 未返回数据（可能被拦截或未配置），已回退到内置示例数据。"

    # 同一批内部先按指纹去重，保留热度最高的一条
    dedup: dict[str, RawPost] = {}
    for rp in raw_posts:
        fp = rp.fingerprint()
        if fp not in dedup or rp.hotness > dedup[fp].hotness:
            dedup[fp] = rp

    new_count = 0
    for fp, rp in dedup.items():
        exists = db.query(HotPost).filter(HotPost.fingerprint == fp).first()
        if exists:
            # 已存在则更新热度（取较高值），不重复插入
            if rp.hotness > exists.hotness:
                exists.hotness = rp.hotness
            continue
        db.add(_to_model(rp))
        new_count += 1

    db.commit()
    return {
        "fetched": len(raw_posts),
        "new": new_count,
        "source": used_source,
        "message": message,
    }
