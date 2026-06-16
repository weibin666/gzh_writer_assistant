"""改写编排：调用大模型 → 解析 → 计算原创度。"""
from __future__ import annotations

import json
import logging
import re

from openai import OpenAI

from ..config import settings
from . import prompts
from .similarity import similarity

logger = logging.getLogger(__name__)


class LLMNotConfigured(Exception):
    pass


def _client() -> OpenAI:
    if not settings.llm_api_key:
        raise LLMNotConfigured(
            "未配置大模型 API Key。请在 backend/.env 中设置 LLM_API_KEY "
            "（默认对接 DeepSeek，可改 LLM_BASE_URL / LLM_MODEL 切换到通义等）。"
        )
    return OpenAI(api_key=settings.llm_api_key, base_url=settings.llm_base_url)


def _parse_output(text: str) -> tuple[str, list[str], str]:
    """从模型输出中解析出 title / title_options / content，对非严格 JSON 做容错。"""
    cleaned = text.strip()
    # 去掉可能的 ```json ``` 包裹
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", cleaned).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start != -1 and end != -1:
        candidate = cleaned[start : end + 1]
        data = None
        try:
            data = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            # 模型常在 JSON 字符串值里直接换行/制表，导致非法 JSON；转义后重试
            patched = candidate.replace("\r", "").replace("\n", "\\n").replace("\t", "\\t")
            try:
                data = json.loads(patched)
            except (json.JSONDecodeError, ValueError) as exc:
                logger.warning("改写输出非标准 JSON，使用降级解析: %s", exc)
        if data is not None:
            title = str(data.get("title", "")).strip()
            options = data.get("title_options", []) or []
            options = [str(o).strip() for o in options if str(o).strip()]
            return title, options, str(data.get("content", "")).strip()

    # 降级：第一行当标题，其余当正文
    lines = [l for l in cleaned.splitlines() if l.strip()]
    if not lines:
        return "", [], cleaned
    return lines[0].strip(), [], "\n".join(lines[1:]).strip() or cleaned


def rewrite(
    title: str,
    account: str,
    content: str,
    style: str = "default",
    extra_instruction: str = "",
) -> dict:
    if not content.strip():
        # 没抓到正文时，用摘要 / 标题兜底，至少能产出基于选题的稿子
        content = title

    messages = prompts.build_messages(title, account, content, style, extra_instruction)
    client = _client()
    resp = client.chat.completions.create(
        model=settings.llm_model,
        messages=messages,
        temperature=0.9,  # 稍高的温度提升改写的差异度
    )
    raw = resp.choices[0].message.content or ""
    new_title, title_options, new_content = _parse_output(raw)

    sim = similarity(content, new_content)
    # 主标题去重后并入候选，保证至少有一个可选项
    options = [new_title] + [o for o in title_options if o != new_title] if new_title else title_options
    return {
        "new_title": new_title or title,
        "title_options": options[:6],
        "content": new_content,
        "similarity": sim,
        "model": settings.llm_model,
    }
