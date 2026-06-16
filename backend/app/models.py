"""数据模型。"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

from .database import Base


class HotPost(Base):
    """抓取到的热点文章。"""

    __tablename__ = "hot_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(512), nullable=False)
    account = Column(String(255), default="")          # 来源公众号 / 媒体
    url = Column(String(1024), default="")
    summary = Column(Text, default="")                 # 摘要 / 列表页文字
    content = Column(Text, default="")                 # 正文（如能抓到）
    keyword = Column(String(128), default="")          # 命中的关键词 / 话题
    source = Column(String(64), default="sogou")       # 数据源标识
    hotness = Column(Float, default=0.0)               # 热度启发式分（非真实点赞）
    published_at = Column(DateTime, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    # 用于去重的指纹（标题+账号归一化）
    fingerprint = Column(String(64), index=True, unique=True)

    rewrites = relationship("Rewrite", back_populates="post", cascade="all, delete-orphan")


class Rewrite(Base):
    """对某篇热点文章的一次改写结果。"""

    __tablename__ = "rewrites"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(Integer, ForeignKey("hot_posts.id"), nullable=False)
    style = Column(String(64), default="default")      # 改写风格
    new_title = Column(String(512), default="")
    title_options = Column(Text, default="[]")          # 备选标题，JSON 数组字符串
    content = Column(Text, default="")
    similarity = Column(Float, default=0.0)            # 与原文相似度 0-1（越低越原创）
    cover_url = Column(String(512), default="")        # 本地预览封面 URL
    cover_path = Column(String(1024), default="")      # 本地封面文件路径
    cover_media_id = Column(String(255), default="")   # 上传到公众号后的素材 media_id
    model = Column(String(128), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    post = relationship("HotPost", back_populates="rewrites")
    schedules = relationship("ScheduledPublish", back_populates="rewrite", cascade="all, delete-orphan")


class ScheduledPublish(Base):
    """定时发布任务：到点自动把某篇改写存草稿 / 发表。"""

    __tablename__ = "scheduled_publishes"

    id = Column(Integer, primary_key=True, index=True)
    rewrite_id = Column(Integer, ForeignKey("rewrites.id"), nullable=False)
    # 到点执行的动作：draft(存草稿) / publish(发表)
    action = Column(String(16), default="draft")
    scheduled_at = Column(DateTime, nullable=False, index=True)  # 本地时间(Asia/Shanghai)
    # pending(待执行) / done(已完成) / failed(失败) / canceled(已取消)
    status = Column(String(16), default="pending", index=True)
    result = Column(Text, default="")                 # 执行结果 / 错误信息
    # 执行时固化标题正文快照，避免之后改动影响已排期内容
    title_snapshot = Column(String(512), default="")
    content_snapshot = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime, nullable=True)

    rewrite = relationship("Rewrite", back_populates="schedules")
