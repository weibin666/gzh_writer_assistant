"""数据源抽象层。

所有热点来源（搜狗微信、RSS、第三方榜单 API…）都实现同一个接口，
上层 service 只面向 RawPost 工作，换源时只需新增一个 Source 实现。
"""
from __future__ import annotations

import hashlib
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class RawPost:
    """数据源产出的统一文章结构。"""

    title: str
    account: str = ""
    url: str = ""
    summary: str = ""
    content: str = ""
    keyword: str = ""
    source: str = ""
    hotness: float = 0.0
    published_at: Optional[datetime] = None
    extra: dict = field(default_factory=dict)

    def fingerprint(self) -> str:
        """标题+账号归一化后的指纹，用于跨次抓取去重。"""
        norm = re.sub(r"\s+", "", f"{self.title}|{self.account}").lower()
        return hashlib.sha1(norm.encode("utf-8")).hexdigest()


class BaseSource(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self, keywords: list[str]) -> list[RawPost]:
        """根据关键词列表抓取热点文章。"""
        raise NotImplementedError
