"""原创度检测：用字符级 n-gram 的 Jaccard 相似度，衡量改写后与原文的雷同程度。

相似度越低 → 原创度越高。这是一个轻量的本地启发式，用来在「避免纯搬运」上给
作者一个直观警示，并不等同于专业的查重系统。
"""
from __future__ import annotations

import re


def _normalize(text: str) -> str:
    # 去掉空白和标点，只保留中文 / 字母 / 数字，避免排版差异干扰判断
    return re.sub(r"[^一-龥a-zA-Z0-9]", "", text)


def _ngrams(text: str, n: int = 4) -> set[str]:
    if len(text) < n:
        return {text} if text else set()
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def similarity(original: str, rewritten: str, n: int = 4) -> float:
    """返回 0-1 的 Jaccard 相似度。"""
    a = _ngrams(_normalize(original), n)
    b = _ngrams(_normalize(rewritten), n)
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return round(inter / union, 4) if union else 0.0
