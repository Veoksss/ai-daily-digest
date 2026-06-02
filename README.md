# AI Daily Digest

每天早上 8:00（北京时间）自动抓取 AI 领域一手资讯，生成中文摘要网页 + 邮件日报。

## 数据源

| 来源 | 类型 | 说明 |
|------|------|------|
| ArXiv | API | cs.AI / cs.CL / cs.CV / cs.LG 等分类最新论文 |
| Papers With Code | RSS | 带开源代码的 AI 论文 |
| The Verge | RSS | AI 频道科技新闻 |
| TechCrunch | RSS | AI 频道行业动态 |

## 一键部署（推荐）

### 1. Fork 本仓库

点击右上角 **Fork**，然后 `git clone` 你的 fork。

### 2. 获取 DeepSeek API Key

1. 注册 [DeepSeek 开放平台](https://platform.deepseek.com/)
2. 进入 [API Keys](https://platform.deepseek.com/api_keys) 创建 Key
3. 充值 ¥10（够用半年+）

### 3. 配置 GitHub Secrets

在 Fork 仓库的 **Settings → Secrets and variables → Actions → New repository secret** 中添加：

| Secret | 说明 |
|--------|------|
| `DEEPSEEK_API_KEY` | DeepSeek API Key（**必填**） |
| `SMTP_HOST` | SMTP 服务器（默认 smtp.qq.com） |
| `SMTP_PORT` | SMTP 端口（默认 587） |
| `SMTP_USER` | 发件人邮箱 |
| `SMTP_PASS` | SMTP 授权码 |
| `SMTP_TO` | 收件人邮箱 |

### 4. 启用 GitHub Pages

**Settings → Pages → Source** 选择 `Deploy from a branch`，分支选 `gh-pages`，目录 `/ (root)`，点击 Save。

### 5. 手动触发第一次运行

**Actions → AI Daily Digest → Run workflow**，等待约 2 分钟后，访问 `https://<你的用户名>.github.io/ai-daily-digest/` 查看效果。

之后每天早上 8:00 自动运行，无需任何操作。

## 本地运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key

# 3. 加载环境变量并运行
export $(cat .env | xargs)  # Linux/macOS
python -m src.main

# 4. 打开 output/index.html 查看结果
```

## 成本

| 项目 | 费用 |
|------|------|
| DeepSeek API | ≈ ¥0.06/天（50篇）≈ **¥2/月** |
| GitHub Actions | 免费（公开仓库无限） |
| GitHub Pages | 免费 |
| SMTP 邮件 | 免费（QQ/Gmail 每日限额够用） |

## 项目结构

```
ai-daily-digest/
├── .github/workflows/daily.yml   # GitHub Actions 定时任务
├── src/
│   ├── fetchers/                 # 四个数据源抓取器
│   │   ├── arxiv.py
│   │   ├── paperswithcode.py
│   │   ├── theverge.py
│   │   └── techcrunch.py
│   ├── processor.py              # 去重 + AI 关键词过滤
│   ├── summarizer.py             # DeepSeek 摘要/分类/打分
│   ├── generator.py              # Jinja2 HTML 生成
│   ├── mailer.py                 # SMTP 邮件发送
│   ├── models.py                 # Article 数据模型
│   └── main.py                   # 主入口
├── templates/index.html.j2       # HTML 模板
├── output/index.html             # 生成的日报页面
├── requirements.txt
└── README.md
```

## 自定义

- **增加数据源**：在 `src/fetchers/` 下新增文件，遵循 `fetch_xxx(client) -> list[Article]` 接口
- **调整分类标签**：编辑 `src/summarizer.py` 中的 `VALID_TAGS`
- **修改运行频率**：编辑 `.github/workflows/daily.yml` 中的 `cron` 表达式
- **更换 LLM**：修改 `src/summarizer.py` 中的 `DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL`（兼容 OpenAI API 的任何模型）

## License

MIT
