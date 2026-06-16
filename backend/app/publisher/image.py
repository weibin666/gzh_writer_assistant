"""AI 封面图生成。

支持两类提供方（在 .env 用 IMAGE_PROVIDER 选择）：
- dashscope：阿里云通义万相，异步「提交任务→轮询」模式；
- openai：任何 OpenAI 兼容的 images.generate 接口。

生成的图片会保存到 frontend/covers/ 下，通过 /static/covers/xxx.png 访问预览。
未配置时抛出友好错误，不影响其他功能。
"""
from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

COVERS_DIR = Path(__file__).resolve().parents[2] / "frontend" / "covers"

DASHSCOPE_SUBMIT = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text2image/image-synthesis"
DASHSCOPE_TASK = "https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}"


class ImageError(Exception):
    pass


def build_cover_prompt(title: str) -> str:
    """根据标题构造一个适合做公众号封面的文生图提示词。"""
    return (
        f"为一篇主题为《{title}》的微信公众号文章设计一张简洁现代的封面插画，"
        "扁平插画风格，构图干净，主题鲜明，留有放标题的空间，高质量，无文字。"
    )


def _save_image(content: bytes, ext: str = "png") -> tuple[str, Path]:
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    path = COVERS_DIR / name
    path.write_bytes(content)
    return f"/static/covers/{name}", path


def _gen_dashscope(prompt: str) -> bytes:
    headers = {
        "Authorization": f"Bearer {settings.image_api_key}",
        "Content-Type": "application/json",
        "X-DashScope-Async": "enable",
    }
    body = {
        "model": settings.image_model,
        "input": {"prompt": prompt},
        "parameters": {"size": settings.image_size, "n": 1},
    }
    with httpx.Client(timeout=settings.http_timeout) as client:
        resp = client.post(DASHSCOPE_SUBMIT, headers=headers, json=body)
        data = resp.json()
        task_id = data.get("output", {}).get("task_id")
        if not task_id:
            raise ImageError(f"提交文生图任务失败：{data}")

        # 轮询任务结果（万相通常几秒到十几秒）
        poll_headers = {"Authorization": f"Bearer {settings.image_api_key}"}
        for _ in range(30):
            time.sleep(2)
            t = client.get(DASHSCOPE_TASK.format(task_id=task_id), headers=poll_headers).json()
            status = t.get("output", {}).get("task_status")
            if status == "SUCCEEDED":
                results = t["output"].get("results", [])
                if not results:
                    raise ImageError("文生图成功但无结果")
                img_url = results[0]["url"]
                return client.get(img_url).content
            if status in ("FAILED", "CANCELED"):
                raise ImageError(f"文生图任务失败：{t}")
        raise ImageError("文生图任务超时")


def _gen_openai(prompt: str) -> bytes:
    from openai import OpenAI

    client = OpenAI(api_key=settings.image_api_key, base_url=settings.image_base_url or None)
    resp = client.images.generate(model=settings.image_model, prompt=prompt, n=1)
    item = resp.data[0]
    if getattr(item, "url", None):
        return httpx.get(item.url, timeout=settings.http_timeout).content
    if getattr(item, "b64_json", None):
        import base64

        return base64.b64decode(item.b64_json)
    raise ImageError("OpenAI 图像接口未返回 url/b64")


def generate_cover(title: str) -> dict:
    """生成封面图，返回 {url, path}。"""
    if settings.image_provider == "none" or not settings.image_api_key:
        raise ImageError(
            "AI 配图未配置。请在 backend/.env 设置 IMAGE_PROVIDER（dashscope/openai）"
            "和 IMAGE_API_KEY。"
        )
    prompt = build_cover_prompt(title)
    if settings.image_provider == "dashscope":
        content = _gen_dashscope(prompt)
    elif settings.image_provider == "openai":
        content = _gen_openai(prompt)
    else:
        raise ImageError(f"不支持的 IMAGE_PROVIDER：{settings.image_provider}")
    url, path = _save_image(content)
    return {"url": url, "path": str(path)}
