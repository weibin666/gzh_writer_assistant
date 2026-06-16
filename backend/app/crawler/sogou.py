"""搜狗微信搜索数据源。

说明（重要）：搜狗微信搜索按关键词返回最近发布的公众号文章，但**不提供真实
点赞/在看数据**。因此 hotness 只能用启发式（时间新近度 + 是否在多个关键词下重复
命中）估算。若需要真实点赞榜单，请实现一个对接新榜 / 西瓜数据 API 的 Source。

搜狗反爬较强（验证码、需要 cookie、详情链接为带签名的跳转）。本实现做了：
- 合理的浏览器请求头；
- 解析失败 / 命中验证码时返回空列表（由上层决定是否回退到 mock）。
"""
from __future__ import annotations

import logging
from datetime import datetime
from urllib.parse import quote

import httpx
from bs4 import BeautifulSoup

from .base import BaseSource, RawPost

logger = logging.getLogger(__name__)

SEARCH_URL = "https://weixin.sogou.com/weixin?type=2&query={query}&page={page}&ie=utf8"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Referer": "https://weixin.sogou.com/",
}


class SogouSource(BaseSource):
    name = "sogou"

    def __init__(self, pages_per_keyword: int = 1, timeout: float = 15.0):
        self.pages_per_keyword = max(1, pages_per_keyword)
        self.timeout = timeout

    def fetch(self, keywords: list[str]) -> list[RawPost]:
        posts: list[RawPost] = []
        with httpx.Client(headers=HEADERS, timeout=self.timeout, follow_redirects=True) as client:
            for kw in keywords:
                for page in range(1, self.pages_per_keyword + 1):
                    try:
                        posts.extend(self._fetch_one(client, kw, page))
                    except Exception as exc:  # noqa: BLE001  单次失败不应中断整体
                        logger.warning("搜狗抓取失败 keyword=%s page=%s: %s", kw, page, exc)
        return posts

    def _fetch_one(self, client: httpx.Client, keyword: str, page: int) -> list[RawPost]:
        url = SEARCH_URL.format(query=quote(keyword), page=page)
        resp = client.get(url)
        resp.raise_for_status()
        html = resp.text

        if "请输入验证码" in html or "antispider" in html:
            logger.warning("搜狗触发反爬验证码 keyword=%s", keyword)
            return []

        soup = BeautifulSoup(html, "lxml")
        items = soup.select("ul.news-list li")
        results: list[RawPost] = []
        for idx, li in enumerate(items):
            title_el = li.select_one("h3 a")
            if not title_el:
                continue
            title = title_el.get_text(strip=True)
            href = title_el.get("href", "")
            if href.startswith("/link?"):
                href = "https://weixin.sogou.com" + href

            summary_el = li.select_one(".txt-info")
            account_el = (
                li.select_one(".account")
                or li.select_one(".s-p")
                or li.select_one("a[id^=account]")
            )
            summary = summary_el.get_text(strip=True) if summary_el else ""
            account = account_el.get_text(strip=True) if account_el else ""

            # 热度启发式：靠前的搜索结果 + 关键词命中，给一个 0-100 的估分。
            hotness = max(0.0, 100.0 - idx * 5 - (page - 1) * 20)

            results.append(
                RawPost(
                    title=title,
                    account=account,
                    url=href,
                    summary=summary,
                    keyword=keyword,
                    source=self.name,
                    hotness=hotness,
                    published_at=datetime.utcnow(),
                )
            )
        return results
