"""内置示例数据源。

当搜狗被反爬拦截 / 无网络时回退到这里，保证整个「抓取 → 选稿 → 改写」流程
任何时候都能跑通，方便开发和演示。
"""
from __future__ import annotations

from datetime import datetime, timedelta

from .base import BaseSource, RawPost

_SEED = [
    {
        "title": "为什么越来越多年轻人开始「断舍离」式社交？",
        "account": "城市观察局",
        "keyword": "情感",
        "hotness": 95,
        "summary": "从无效饭局到点赞之交，年轻人正在重新定义社交的边界。",
        "content": (
            "最近一个词在年轻人中悄悄流行：社交断舍离。\n\n"
            "过去我们习惯用通讯录里好友的数量来衡量一个人的人脉，但越来越多人发现，"
            "真正能在深夜接你电话的人，可能一只手就数得过来。于是他们开始主动清理那些"
            "只会在朋友圈点赞、却从不真正关心你的关系。\n\n"
            "这并不是变得冷漠，而是把有限的精力，留给真正重要的人。心理学上把这种现象"
            "称为『社交节能』——当一个人的自我足够稳定，就不再需要靠庞大的社交圈来确认自己的价值。\n\n"
            "断舍离式社交的核心，不是断绝关系，而是分清主次。"
        ),
    },
    {
        "title": "AI 正在悄悄改变这 5 个普通职业，你的工作在其中吗？",
        "account": "科技前沿志",
        "keyword": "AI",
        "hotness": 92,
        "summary": "客服、文案、设计、翻译、数据录入……AI 落地最快的并不是程序员。",
        "content": (
            "提到 AI 取代工作，很多人第一反应是程序员，但现实恰恰相反。\n\n"
            "真正被 AI 改变最快的，是那些流程标准化、重复度高的岗位。\n\n"
            "第一是客服。智能客服已经能处理八成以上的常见咨询。\n"
            "第二是基础文案。营销短文、商品描述这类模板化写作，AI 几秒就能产出初稿。\n"
            "第三是平面设计的初稿环节。\n"
            "第四是翻译，尤其是非文学类的资料翻译。\n"
            "第五是数据录入与整理。\n\n"
            "但请注意：AI 改变的是『任务』，不是『职业』。会用 AI 的人，正在取代不会用 AI 的人。"
        ),
    },
    {
        "title": "医生提醒：这 3 个养生习惯，可能正在悄悄伤害你",
        "account": "健康每日谈",
        "keyword": "健康养生",
        "hotness": 88,
        "summary": "大量喝水、过度泡脚、盲目补钙，好心办坏事的养生误区。",
        "content": (
            "养生是好事，但方法不对，反而伤身。\n\n"
            "误区一：每天必须喝够 8 杯水。喝水量应因人而异，肾功能不好的人过量饮水反而加重负担。\n\n"
            "误区二：泡脚水越烫越好、时间越久越好。糖尿病患者尤其要警惕烫伤。\n\n"
            "误区三：盲目大量补钙。补钙过量可能增加结石和血管钙化风险，补之前最好先检测。\n\n"
            "真正的养生，是规律作息、均衡饮食和适度运动，而不是跟风某个单一习惯。"
        ),
    },
    {
        "title": "35 岁之后，最值钱的不是经验，而是这种能力",
        "account": "职场成长课",
        "keyword": "职场",
        "hotness": 85,
        "summary": "当经验开始贬值，真正决定职业天花板的是另一件事。",
        "content": (
            "很多人以为，工作越久越值钱，因为经验在积累。\n\n"
            "但现实是，单纯的『熟练』正在快速贬值。流程会被工具替代，行业会被周期重塑。\n\n"
            "35 岁之后真正稀缺的，是『把经验抽象成方法论，并迁移到新领域』的能力。\n\n"
            "同样做了十年运营，有人只是把一件事重复了十年，有人却沉淀出一套能复用到任何业务的底层逻辑。\n\n"
            "前者依赖岗位，后者拥有的是可迁移的资产。这才是抗风险的核心竞争力。"
        ),
    },
    {
        "title": "人工智能时代，普通人最该补的不是技术课，而是这门课",
        "account": "未来学习社",
        "keyword": "人工智能",
        "hotness": 83,
        "summary": "当工具越来越强，决定差距的反而是提问和判断的能力。",
        "content": (
            "AI 把『执行』的门槛大幅降低，写作、画图、编程都能一句话生成。\n\n"
            "这时很多人焦虑地去报各种技术速成班，但真正拉开差距的，其实是『提问与判断』。\n\n"
            "同样一个 AI，有人只能得到平庸答案，有人却能引导出惊艳结果，区别在于会不会提问。\n\n"
            "而拿到答案后，能不能判断它对不对、好不好、要不要用，又是另一层能力。\n\n"
            "在 AI 时代，清晰的思考、精准的表达和独立的判断，比任何具体工具都更保值。"
        ),
    },
]


class MockSource(BaseSource):
    name = "mock"

    def fetch(self, keywords: list[str]) -> list[RawPost]:
        now = datetime.utcnow()
        posts: list[RawPost] = []
        for i, item in enumerate(_SEED):
            h = float(item["hotness"])
            # 由热度派生一组示例互动数据，便于演示界面
            likes = int(h * 120)
            posts.append(
                RawPost(
                    title=item["title"],
                    account=item["account"],
                    url=f"https://example.com/mock/{i}",
                    summary=item["summary"],
                    content=item["content"],
                    keyword=item["keyword"],
                    source=self.name,
                    hotness=h,
                    likes=likes,
                    shares=int(likes * 0.35),
                    favorites=int(likes * 0.5),
                    comments=int(likes * 0.18),
                    published_at=now - timedelta(hours=i),
                )
            )
        return posts
