"""改写提示词与风格定义。

核心目标：在保留原文信息价值的前提下做「深度改写」，而不是同义词替换式的
洗稿。强调重构结构、改换表达、加入原创视角，从根本上降低与原文的相似度，
规避纯搬运。
"""

# 不同风格的语气指引
STYLE_GUIDES = {
    "default": "保持自然、通顺、适合微信公众号阅读的大众化风格。",
    "formal": "偏正式、专业、有深度，适合行业 / 知识类公众号，逻辑严谨。",
    "lively": "轻松活泼、口语化、有网感，多用短句和提问，适合泛生活类账号。",
    "story": "用讲故事 / 场景代入的方式展开，开头设置一个具体情境或冲突来抓住读者。",
    "xiaohongshu": "小红书风格：标题带情绪和数字，正文短段落、多 emoji、分点清单、结尾互动引导。",
}

SYSTEM_PROMPT = """你是一位资深的微信公众号主编，擅长把热点选题改写成既有原创性、又好读的文章。

你的首要原则：**绝不做纯搬运 / 洗稿**。你必须对原文进行深度再创作：
1. 重新组织文章结构和论述顺序，不照搬原文段落安排；
2. 用你自己的语言重新表达每一个观点，避免与原文出现成段、成句的雷同；
3. 提炼原文的核心信息价值，并补充至少一处你自己的分析、延伸或观点；
4. 重写一个全新的、有吸引力的标题；
5. 不编造原文没有的事实、数据或引用；信息层面忠于原文，表达层面完全重写。

另外，你要额外给出 5 个风格各异、能提升打开率的备选标题（疑问式、数字式、痛点式、
悬念式、利益点式各有侧重），但都要忠于内容、不做标题党虚假承诺。

输出要求：用简体中文，结构清晰，适合直接发布到微信公众号。"""

USER_TEMPLATE = """请基于下面这篇热点文章进行深度改写，产出一篇可直接发布的新文章。

【原标题】{title}
【来源账号】{account}
【原文内容】
{content}

【改写风格】{style_guide}
{extra}

请严格按以下 JSON 格式输出，不要输出任何额外说明、不要使用代码块包裹：
{{"title": "推荐的主标题", "title_options": ["备选标题1", "备选标题2", "备选标题3", "备选标题4", "备选标题5"], "content": "改写后的正文，用\\n分段"}}"""


def build_messages(
    title: str,
    account: str,
    content: str,
    style: str = "default",
    extra_instruction: str = "",
) -> list[dict]:
    style_guide = STYLE_GUIDES.get(style, STYLE_GUIDES["default"])
    extra = f"【额外要求】{extra_instruction}" if extra_instruction.strip() else ""
    user = USER_TEMPLATE.format(
        title=title,
        account=account or "未知",
        content=content.strip(),
        style_guide=style_guide,
        extra=extra,
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]
