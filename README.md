# 公众号写作助手

一个微信公众号选题与改写平台：**抓取热点文章 → 选稿 → AI 深度改写润色 → 复制发布**，
并内置「原创度检测」帮助避免纯搬运 / 洗稿。

## 功能

- 🔥 **更新热点**：按关键词抓取最近的公众号热点文章，按热度排序。
- 📝 **选稿改写**：选中任意一篇，选择改写风格（大众/正式/活泼/故事/小红书），AI 深度重写。
- 🛡️ **避免搬运**：改写提示词强制重构结构、重写表达、补充原创观点；并对结果做相似度检测，给出「原创度」评分预警。
- ✂️ **编辑复制**：结果可直接在页面编辑，一键复制到公众号后台发布。

## 技术栈

- 后端：Python + FastAPI + SQLAlchemy（SQLite）
- 抓取：搜狗微信搜索（可插拔数据源，见 `backend/app/crawler/`）
- 改写：OpenAI 兼容大模型接口（默认 DeepSeek，可切换通义等）
- 前端：原生 HTML/CSS/JS（由后端静态托管）

## 快速开始

```bash
bash run.sh
```

首次运行会创建虚拟环境、安装依赖、并从 `.env.example` 生成 `backend/.env`。
**请在 `backend/.env` 中填入 `LLM_API_KEY`**，否则改写功能不可用（抓取仍可用）。

启动后访问 http://127.0.0.1:8000

## 关于数据源的重要说明

微信官方**没有**提供「高赞文章」开放接口；点赞/在看数据只有微信客户端或第三方
付费榜单（新榜、西瓜数据等）才有。本项目使用**搜狗微信搜索**，它只能按关键词
返回最近文章、**拿不到真实点赞量**，因此列表里的「🔥 热度」是基于排名+新近度的
**启发式估分**，并非真实点赞。

搜狗反爬较强，若被验证码拦截会**自动回退到内置示例数据**（`USE_MOCK_FALLBACK=true`），
保证流程随时可演示。

要接入**真实点赞榜单**，只需在 `backend/app/crawler/` 下新增一个实现了
`BaseSource` 接口的数据源（如对接新榜 API），并在 `service.py` 中替换即可，
上层代码无需改动。

## 进阶功能

### ① 接入真实点赞榜单
搜狗拿不到真实点赞。要用真实数据，在 `backend/.env` 设置：
```
CRAWL_SOURCE=newrank
NEWRANK_API_KEY=你的key
NEWRANK_ENDPOINT=你套餐文档里的榜单接口URL
```
适配器在 [crawler/newrank.py](backend/app/crawler/newrank.py)。各平台返回字段不同，若与默认
`_FIELD_MAP` 不一致，改一下映射即可（已兼容 `{data:{list:[]}}` 等常见包裹）。未配置/失败会自动回退。

### ② 定时每天自动更新热点
```
SCHEDULE_ENABLED=true
SCHEDULE_HOUR=8
SCHEDULE_MINUTE=0
```
启用后每天定点自动抓取（时区 Asia/Shanghai）。查看状态：`GET /api/schedule`。

### ③ 自动存公众号草稿
改写结果页点「📤 存公众号草稿」即可推送到草稿箱（**只存草稿，不自动群发**，安全可控）。
需在 `backend/.env` 配置：
```
WECHAT_APPID=...
WECHAT_SECRET=...
WECHAT_DEFAULT_THUMB_MEDIA_ID=...   # 草稿封面图必填：先在素材库上传一张永久图片取其 media_id
WECHAT_AUTHOR=...
```
注意：公众号后台需把**本机出口 IP 加入「IP 白名单」**，否则获取 access_token 会失败。
实现见 [publisher/wechat.py](backend/app/publisher/wechat.py)，推送的是页面上你**编辑后**的最新内容。

### ④ 定时发布（排期队列）
提前把多篇文章排好队、设好时间，系统到点自动执行。结果页「🕒 定时发布」选时间和动作；
顶栏「🕒 排期列表」查看 / 取消所有排期。两种动作：

- **到点存草稿**（默认，最安全）：到时间自动生成草稿，你再手动群发；
- **到点自动发表**：到时间调用公众号「发布接口」(freepublish) 自动发表。

> 微信 API **不支持**把"群发推送给所有粉丝"定到任意未来时间（群发有月次数限制且需审核）。
> 这里的定时由**本服务调度器**实现：每分钟检查队列、到点调用 API，排期时会快照当时的标题/正文。
> 需保持进程运行。实现见 [scheduler.py](backend/app/scheduler.py)、[publisher/service.py](backend/app/publisher/service.py)。

## 写作辅助功能

### 敏感词 / 违规检测
改写结果会自动扫描四类发布风险并高亮预警：**广告法违禁词**（最/第一/100%…）、
**站外导流词**（加微信/扫码…）、**诱导分享**（集赞/转发…）、**医疗夸大**（根治/治愈…）。
编辑后可点「🔍 重新检测」。词库在 [moderation/sensitive.py](backend/app/moderation/sensitive.py)
的 `WORDLISTS` 里可增删。仅供参考，不替代平台审核。

### 多标题候选
每次改写额外生成 5 个不同风格的备选标题（疑问/数字/痛点/悬念/利益点），点击即可替换主标题。

### AI 封面配图（需配置）
结果页点「🖼️ 生成封面」按标题生成封面图并预览；存草稿时会自动把它上传为公众号
永久素材并用作文章封面。在 `backend/.env` 配置：
```
IMAGE_PROVIDER=dashscope      # 通义万相；或 openai
IMAGE_API_KEY=你的key
IMAGE_MODEL=wanx2.1-t2i-turbo
```
未配置时其它功能不受影响。实现见 [publisher/image.py](backend/app/publisher/image.py)。

## 合规提醒

改写后的内容请确认信息真实、不侵犯原作者权益后再发布；本工具的「原创度」评分仅为
辅助参考，不替代平台查重与原创审核。

## 目录结构

```
backend/
  app/
    crawler/    # 数据源：base(接口) / sogou / mock / service(编排)
    rewriter/   # 改写：prompts / similarity(原创度) / service
    routers/    # API：posts / rewrite
    models.py schemas.py config.py database.py main.py
frontend/       # index.html / app.js / style.css
run.sh
```
