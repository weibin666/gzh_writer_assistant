"""Pydantic 出入参模型。"""
import json
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class PostOut(BaseModel):
    id: int
    title: str
    account: str
    url: str
    summary: str
    keyword: str
    source: str
    hotness: float
    likes: int = -1
    shares: int = -1
    favorites: int = -1
    comments: int = -1
    published_at: Optional[datetime]
    fetched_at: datetime
    rewrite_count: int = 0

    model_config = {"from_attributes": True}


class PostDetail(PostOut):
    content: str


class RefreshRequest(BaseModel):
    # 本次抓取要覆盖的领域 / 关键词；为空则用配置里的默认
    domains: list[str] = []


class RefreshResult(BaseModel):
    fetched: int          # 本次抓到的总条数
    new: int              # 去重后新增条数
    source: str           # 实际使用的数据源（sogou / mock）
    message: str = ""


class RewriteRequest(BaseModel):
    style: str = "default"          # default / formal / lively / story / xiaohongshu
    extra_instruction: str = ""     # 额外的自定义要求


class RewriteOut(BaseModel):
    id: int
    post_id: int
    style: str
    new_title: str
    title_options: list[str] = []
    content: str
    similarity: float
    model: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("title_options", mode="before")
    @classmethod
    def _parse_options(cls, v):
        # ORM 里存的是 JSON 字符串，这里解析成列表
        if isinstance(v, str):
            try:
                return json.loads(v) if v.strip() else []
            except json.JSONDecodeError:
                return []
        return v or []


class CheckRequest(BaseModel):
    text: str = ""


class TextCheckRequest(BaseModel):
    title: str = ""
    content: str = ""


class ScheduleCreate(BaseModel):
    scheduled_at: datetime          # 本地时间(Asia/Shanghai)
    action: str = "draft"           # draft(存草稿) / publish(发表)
    title: str = ""                 # 可选：页面编辑后的标题/正文快照
    content: str = ""


class ScheduledPublishOut(BaseModel):
    id: int
    rewrite_id: int
    action: str
    scheduled_at: datetime
    status: str
    result: str
    title_snapshot: str
    created_at: datetime
    executed_at: Optional[datetime]

    model_config = {"from_attributes": True}
