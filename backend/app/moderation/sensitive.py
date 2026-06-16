"""敏感词 / 违规用语检测。

针对公众号最常见的三类发布风险做本地扫描，给作者预警（不替代平台审核）：
1. ad_law   —— 广告法绝对化 / 夸大违禁词（最、第一、100%、根治…），易被判违规广告；
2. divert   —— 导流词（加微信、扫码、私信…），公众号严禁站外导流，易限流封号；
3. induce   —— 诱导分享 / 集赞（转发、集赞、关注后…），违反诱导分享规则；
4. medical  —— 医疗保健夸大（治愈、特效、包好…），医疗类尤其敏感。

词库可按需在 WORDLISTS 里增删。命中后返回类别、建议和出现次数。
"""
from __future__ import annotations

import re
from dataclasses import dataclass

CATEGORY_LABEL = {
    "ad_law": "广告法违禁词",
    "divert": "站外导流词",
    "induce": "诱导分享",
    "medical": "医疗夸大",
}

CATEGORY_ADVICE = {
    "ad_law": "广告法禁止绝对化用语，建议改成相对、可证实的表述。",
    "divert": "公众号严禁站外导流，建议删除或改为站内引导。",
    "induce": "诱导分享/集赞违规，建议去掉相关引导。",
    "medical": "医疗保健类夸大表述风险高，建议删除或弱化。",
}

WORDLISTS: dict[str, list[str]] = {
    "ad_law": [
        "最佳", "最好", "最强", "最优", "最低", "最高", "最大", "最便宜",
        "第一", "全网第一", "全国第一", "唯一", "独一无二", "顶级", "极致",
        "国家级", "世界级", "百分百", "100%", "绝对", "永久", "万能", "完美",
    ],
    "divert": [
        "加微信", "加我微信", "微信号", "vx", "VX", "v信", "扫码", "扫一扫加",
        "私信我", "私我", "加群", "进群", "加QQ", "联系方式", "二维码加",
    ],
    "induce": [
        "转发到朋友圈", "集赞", "点赞领", "分享给好友", "关注后领取",
        "转发可得", "点击关注", "求转发", "求点赞", "投票", "助力",
    ],
    "medical": [
        "根治", "治愈", "特效", "药到病除", "包好", "无副作用",
        "百分百治愈", "永不复发", "包治", "立竿见影",
    ],
}


@dataclass
class Hit:
    word: str
    category: str
    label: str
    advice: str
    count: int


def check(text: str) -> dict:
    """扫描文本，返回命中列表与汇总。"""
    text = text or ""
    hits: list[Hit] = []
    total = 0
    for category, words in WORDLISTS.items():
        for w in words:
            count = len(re.findall(re.escape(w), text, flags=re.IGNORECASE))
            if count:
                hits.append(
                    Hit(
                        word=w,
                        category=category,
                        label=CATEGORY_LABEL[category],
                        advice=CATEGORY_ADVICE[category],
                        count=count,
                    )
                )
                total += count
    # 高风险（导流/医疗/诱导）排前面
    order = {"divert": 0, "medical": 1, "induce": 2, "ad_law": 3}
    hits.sort(key=lambda h: (order.get(h.category, 9), -h.count))
    return {
        "risk": total,
        "hits": [h.__dict__ for h in hits],
        "ok": total == 0,
    }
