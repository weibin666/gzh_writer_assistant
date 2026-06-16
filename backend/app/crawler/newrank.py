"""真实榜单数据源（新榜 / 西瓜数据等第三方付费平台）。

这类平台才有**真实的点赞 / 在看 / 阅读**数据。各家接口字段不同，这里做成一个
**通用适配器**：通过环境变量配置端点和鉴权，再把返回的 JSON 映射成统一的 RawPost。

接入步骤：
1. 在 .env 设置 NEWRANK_API_KEY 和 NEWRANK_ENDPOINT（你的套餐文档给的榜单接口 URL）；
2. 把 config.crawl_source 改成 "newrank"；
3. 如果对方返回字段名和下面 _FIELD_MAP 不一致，改一下映射即可。

未配置或请求失败时返回空列表，由上层 service 决定是否回退。
"""
from __future__ import annotations

import logging
from datetime import datetime

import httpx

from .base import BaseSource, RawPost

logger = logging.getLogger(__name__)

# 第三方返回字段 -> 统一字段。按你的实际接口调整右侧的候选键名。
_FIELD_MAP = {
    "title": ["title", "articleTitle", "name"],
    "account": ["account", "wxName", "nickname", "accountName"],
    "url": ["url", "articleUrl", "link"],
    "summary": ["summary", "digest", "desc"],
    "likes": ["like_num", "likeCount", "zan", "like"],
    "reads": ["read_num", "readCount", "read"],
}


def _pick(item: dict, keys: list[str], default=""):
    for k in keys:
        if k in item and item[k] not in (None, ""):
            return item[k]
    return default


class NewRankSource(BaseSource):
    name = "newrank"

    def __init__(self, api_key: str, endpoint: str, limit: int = 30, timeout: float = 15.0):
        self.api_key = api_key
        self.endpoint = endpoint
        self.limit = limit
        self.timeout = timeout

    def fetch(self, keywords: list[str]) -> list[RawPost]:
        if not (self.api_key and self.endpoint):
            logger.warning("newrank 数据源未配置 NEWRANK_API_KEY / NEWRANK_ENDPOINT")
            return []
        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.get(
                    self.endpoint,
                    headers={"key": self.api_key, "Authorization": f"Bearer {self.api_key}"},
                    params={"size": self.limit},
                )
                resp.raise_for_status()
                payload = resp.json()
        except Exception as exc:  # noqa: BLE001
            logger.warning("newrank 抓取失败：%s", exc)
            return []

        # 兼容 {data: {list: [...]}} / {data: [...]} / [...] 几种常见包裹
        items = payload
        for key in ("data", "list", "articles", "rankList"):
            if isinstance(items, dict) and key in items:
                items = items[key]
        if not isinstance(items, list):
            logger.warning("newrank 返回结构无法识别，请检查 _FIELD_MAP / 解包逻辑")
            return []

        results: list[RawPost] = []
        for it in items:
            if not isinstance(it, dict):
                continue
            likes = float(_pick(it, _FIELD_MAP["likes"], 0) or 0)
            reads = float(_pick(it, _FIELD_MAP["reads"], 0) or 0)
            # 真实热度：点赞为主，阅读为辅
            hotness = likes + reads * 0.1
            results.append(
                RawPost(
                    title=str(_pick(it, _FIELD_MAP["title"])),
                    account=str(_pick(it, _FIELD_MAP["account"])),
                    url=str(_pick(it, _FIELD_MAP["url"])),
                    summary=str(_pick(it, _FIELD_MAP["summary"])),
                    keyword="榜单",
                    source=self.name,
                    hotness=hotness,
                    published_at=datetime.utcnow(),
                    extra={"likes": likes, "reads": reads},
                )
            )
        return results
