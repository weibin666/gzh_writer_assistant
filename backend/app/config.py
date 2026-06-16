"""应用配置。所有可调项通过环境变量 / .env 注入。"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # 数据库
    database_url: str = "sqlite:///./gzh_writer.db"

    # 大模型（OpenAI 兼容接口；默认 DeepSeek，可改成通义等）
    llm_api_key: str = ""
    llm_base_url: str = "https://api.deepseek.com"
    llm_model: str = "deepseek-chat"

    # 爬虫
    # 主数据源：sogou(搜狗微信) / newrank(新榜等真实榜单)
    crawl_source: str = "sogou"
    # 抓取热点时使用的关键词 / 话题；逗号分隔。搜狗微信按关键词返回最近文章。
    crawl_keywords: str = "AI,人工智能,职场,健康养生,情感"
    crawl_pages_per_keyword: int = 1
    # 搜狗失败（验证码/封禁）时是否回退到内置示例数据，保证流程可跑通
    use_mock_fallback: bool = True

    # 抓取请求超时（秒）
    http_timeout: float = 15.0

    # ---- ① 真实榜单 API（新榜 / 西瓜等，OpenAPI 风格，可配置端点）----
    newrank_api_key: str = ""
    newrank_endpoint: str = ""          # 榜单接口完整 URL（由你的套餐文档提供）
    newrank_limit: int = 30

    # ---- ② 定时自动更新热点 ----
    schedule_enabled: bool = False
    schedule_hour: int = 8              # 每天几点抓（0-23，本地时区）
    schedule_minute: int = 0

    # ---- ② AI 配图 / 封面 ----
    # 文生图提供方：dashscope(通义万相) / openai(OpenAI 兼容 images) / none
    image_provider: str = "none"
    image_api_key: str = ""
    image_model: str = "wanx2.1-t2i-turbo"
    image_base_url: str = ""            # openai 兼容方式时填
    image_size: str = "1024*1024"

    # ---- ③ 微信公众号草稿 ----
    wechat_appid: str = ""
    wechat_secret: str = ""
    # 草稿封面图必填，需先在公众号素材库上传一张永久图片，把 media_id 填这里
    wechat_default_thumb_media_id: str = ""
    wechat_author: str = ""

    @property
    def keywords(self) -> list[str]:
        return [k.strip() for k in self.crawl_keywords.split(",") if k.strip()]


settings = Settings()
