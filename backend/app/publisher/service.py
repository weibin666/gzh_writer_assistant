"""发布执行：把一篇改写存草稿 / 发表，供即时发布和定时任务共用。"""
from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..models import Rewrite
from .wechat import add_draft, freepublish, upload_thumb_material

logger = logging.getLogger(__name__)


def execute_publish(
    db: Session,
    rewrite: Rewrite,
    action: str = "draft",
    title: str = "",
    content: str = "",
) -> dict:
    """执行一次发布。

    action=draft  仅存入草稿箱；
    action=publish 存草稿后再调用发布接口正式发表。
    返回 {media_id, publish_id, message}。
    """
    title = (title or rewrite.new_title).strip()
    content = (content or rewrite.content).strip()
    if not title or not content:
        raise ValueError("标题或正文为空")

    # 若已生成 AI 封面但尚未上传素材，先上传拿到 media_id
    if rewrite.cover_path and not rewrite.cover_media_id:
        rewrite.cover_media_id = upload_thumb_material(rewrite.cover_path)
        db.commit()

    draft = add_draft(title=title, content=content, thumb_media_id=rewrite.cover_media_id)
    media_id = draft["media_id"]

    publish_id = ""
    if action == "publish":
        publish_id = freepublish(media_id)["publish_id"]
        message = "已自动发表。"
    else:
        message = "已存入草稿箱，请到后台确认排版后群发。"

    return {"media_id": media_id, "publish_id": publish_id, "message": message}
