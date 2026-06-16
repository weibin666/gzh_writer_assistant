"""微信公众号草稿推送。

把改写后的文章通过公众号 API 存入「草稿箱」，你在后台确认排版后手动群发，
全程不自动发布，安全可控。

依赖（在 .env 配置）：
- WECHAT_APPID / WECHAT_SECRET：公众号的开发者凭证；
- WECHAT_DEFAULT_THUMB_MEDIA_ID：草稿封面图必填，需先在公众号素材库上传一张
  永久图片素材，拿到它的 media_id 填进来；
- 公众号后台需把本机出口 IP 加入「IP 白名单」，否则获取 access_token 会失败。

接口文档：草稿 draft/add，凭证 cgi-bin/token。
"""
from __future__ import annotations

import html
import logging
import time

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

TOKEN_URL = "https://api.weixin.qq.com/cgi-bin/token"
DRAFT_ADD_URL = "https://api.weixin.qq.com/cgi-bin/draft/add"
MATERIAL_ADD_URL = "https://api.weixin.qq.com/cgi-bin/material/add_material"
FREEPUBLISH_URL = "https://api.weixin.qq.com/cgi-bin/freepublish/submit"

# access_token 进程内缓存
_token_cache: dict = {"token": "", "expire_at": 0.0}


class WeChatError(Exception):
    pass


def _ensure_credentials():
    missing = [
        name
        for name, val in [
            ("WECHAT_APPID", settings.wechat_appid),
            ("WECHAT_SECRET", settings.wechat_secret),
        ]
        if not val
    ]
    if missing:
        raise WeChatError(f"公众号功能未配置：缺少 {', '.join(missing)}（见 backend/.env）")


def get_access_token(force: bool = False) -> str:
    _ensure_credentials()
    now = time.time()
    if not force and _token_cache["token"] and _token_cache["expire_at"] > now + 60:
        return _token_cache["token"]

    with httpx.Client(timeout=settings.http_timeout) as client:
        resp = client.get(
            TOKEN_URL,
            params={
                "grant_type": "client_credential",
                "appid": settings.wechat_appid,
                "secret": settings.wechat_secret,
            },
        )
        data = resp.json()
    if "access_token" not in data:
        raise WeChatError(f"获取 access_token 失败：{data}（常见原因：IP 未加白名单 / 凭证错误）")
    _token_cache["token"] = data["access_token"]
    _token_cache["expire_at"] = now + int(data.get("expires_in", 7200))
    return _token_cache["token"]


def _to_html(text: str) -> str:
    """把纯文本（\\n 分段）转成公众号可接受的简单 HTML。"""
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    return "".join(f"<p>{html.escape(p)}</p>" for p in paras)


def upload_thumb_material(image_path: str) -> str:
    """把本地图片上传为公众号永久图片素材，返回 media_id。"""
    token = get_access_token()
    p = Path(image_path)
    if not p.exists():
        raise WeChatError(f"封面图文件不存在：{image_path}")
    with httpx.Client(timeout=settings.http_timeout) as client:
        with p.open("rb") as f:
            resp = client.post(
                MATERIAL_ADD_URL,
                params={"access_token": token, "type": "image"},
                files={"media": (p.name, f, "image/png")},
            )
        data = resp.json()
    if "media_id" not in data:
        raise WeChatError(f"上传封面素材失败：{data}")
    return data["media_id"]


def add_draft(title: str, content: str, digest: str = "", thumb_media_id: str = "") -> dict:
    """新建一篇草稿，返回 {media_id}。"""
    token = get_access_token()
    thumb = thumb_media_id or settings.wechat_default_thumb_media_id
    if not thumb:
        raise WeChatError(
            "缺少封面图：请先用 AI 配图生成并上传封面，或在 .env 配置 "
            "WECHAT_DEFAULT_THUMB_MEDIA_ID。"
        )

    article = {
        "title": title[:64],  # 标题上限 64 字
        "author": settings.wechat_author,
        "digest": (digest or content)[:120].replace("\n", " "),
        "content": _to_html(content),
        "thumb_media_id": thumb,
        "need_open_comment": 0,
        "only_fans_can_comment": 0,
    }

    with httpx.Client(timeout=settings.http_timeout) as client:
        resp = client.post(
            DRAFT_ADD_URL,
            params={"access_token": token},
            json={"articles": [article]},
        )
        data = resp.json()

    if data.get("errcode", 0) != 0:
        # token 过期等情况重试一次
        if data.get("errcode") in (40001, 42001):
            token = get_access_token(force=True)
            with httpx.Client(timeout=settings.http_timeout) as client:
                resp = client.post(
                    DRAFT_ADD_URL, params={"access_token": token}, json={"articles": [article]}
                )
                data = resp.json()
        if data.get("errcode", 0) != 0:
            raise WeChatError(f"存草稿失败：{data}")

    return {"media_id": data.get("media_id", "")}


def freepublish(media_id: str) -> dict:
    """调用「发布接口」把一篇草稿正式发表，返回 {publish_id}。"""
    if not media_id:
        raise WeChatError("缺少草稿 media_id，无法发表")
    token = get_access_token()
    with httpx.Client(timeout=settings.http_timeout) as client:
        resp = client.post(FREEPUBLISH_URL, params={"access_token": token}, json={"media_id": media_id})
        data = resp.json()
    if data.get("errcode", 0) != 0:
        raise WeChatError(f"发表失败：{data}")
    return {"publish_id": data.get("publish_id", "")}
