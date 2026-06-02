"""DeepSeek API 摘要与分类

使用 DeepSeek API（OpenAI 兼容接口）对文章进行：
- 中文摘要（2-3 句）
- 分类标签
- 重要性打分
"""

import json
import os
from typing import Optional

from openai import AsyncOpenAI

from src.models import Article

# DeepSeek 配置
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"

# 预定义分类标签（含中文描述，帮助模型准确分类）
VALID_TAGS = [
    "LLM / 大语言模型",
    "CV / 计算机视觉",
    "NLP / 自然语言处理",
    "Robotics / 机器人",
    "Product / 产品与商业",
    "Policy / 政策与伦理",
    "Research / 学术前沿",
    "Other / 其他",
]

# 简化标签名（用于匹配 DeepSeek 返回的标签）
TAG_ALIASES = {
    "llm": "LLM / 大语言模型",
    "大语言模型": "LLM / 大语言模型",
    "大模型": "LLM / 大语言模型",
    "cv": "CV / 计算机视觉",
    "计算机视觉": "CV / 计算机视觉",
    "视觉": "CV / 计算机视觉",
    "nlp": "NLP / 自然语言处理",
    "自然语言处理": "NLP / 自然语言处理",
    "自然语言": "NLP / 自然语言处理",
    "robotics": "Robotics / 机器人",
    "机器人": "Robotics / 机器人",
    "product": "Product / 产品与商业",
    "产品": "Product / 产品与商业",
    "商业": "Product / 产品与商业",
    "policy": "Policy / 政策与伦理",
    "政策": "Policy / 政策与伦理",
    "伦理": "Policy / 政策与伦理",
    "research": "Research / 学术前沿",
    "学术": "Research / 学术前沿",
    "论文": "Research / 学术前沿",
    "其他": "Other / 其他",
    "other": "Other / 其他",
}

SYSTEM_PROMPT = """你是一个 AI 技术日报的编辑。我给你一批英文文章（标题+摘要），请为每篇文章生成：

1. **cn_summary**: 2-3 句中文摘要，抓住核心观点或技术突破
2. **tags**: 1-2 个分类标签，从以下中选择：
   LLM / 大语言模型, CV / 计算机视觉, NLP / 自然语言处理,
   Robotics / 机器人, Product / 产品与商业, Policy / 政策与伦理,
   Research / 学术前沿, Other / 其他
3. **score**: 重要性打分 1-5
   - 5: 重大突破（GPT-5 发布、AlphaFold 级别成果）
   - 4: 重要进展（大厂核心产品更新、SOTA 刷新）
   - 3: 值得关注（新模型/工具发布、行业趋势）
   - 2: 一般信息（融资动态、常规报道）
   - 1: 边缘相关

严格输出 JSON 数组，不要任何其他文字。格式：
[{"id": "源ID", "cn_summary": "...", "tags": ["...", "..."], "score": N}, ...]

保留原文的 id 字段一一对应。"""


def get_client() -> AsyncOpenAI:
    """获取 DeepSeek API 客户端。"""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 环境变量未设置")

    return AsyncOpenAI(
        api_key=api_key,
        base_url=DEEPSEEK_BASE_URL,
    )


def _build_batch_prompt(articles: list[Article]) -> str:
    """构建批处理 prompt。"""
    lines = []
    for a in articles:
        lines.append(
            f'{{"id": "{a.source_id}", '
            f'"title": {json.dumps(a.title)}, '
            f'"summary": {json.dumps(a.summary[:800])}}}'
        )
    return "[\n" + ",\n".join(lines) + "\n]"


async def summarize_batch(
    articles: list[Article],
    client: Optional[AsyncOpenAI] = None,
) -> list[Article]:
    """对一批文章调用 DeepSeek 进行摘要、分类、打分。

    Args:
        articles: 待处理的文章列表
        client: AsyncOpenAI 客户端（可选）

    Returns:
        填充了 cn_summary / tags / score 的文章列表
    """
    if not articles:
        return articles

    if client is None:
        client = get_client()

    prompt = _build_batch_prompt(articles)

    resp = await client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=4096,
    )

    content = resp.choices[0].message.content or "[]"

    # 尝试从可能的 markdown 代码块中提取 JSON
    content = content.strip()
    if content.startswith("```"):
        # 去掉 ```json 和结尾 ```
        content = content.split("\n", 1)[-1]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

    try:
        results = json.loads(content)
    except json.JSONDecodeError:
        # 容错：返回原文，标记处理失败
        for a in articles:
            a.cn_summary = a.summary[:200]
            a.tags = ["Other / 其他"]
            a.score = 2
        return articles

    # 按 id 回填
    result_map = {r.get("id", ""): r for r in results if isinstance(r, dict)}
    for a in articles:
        r = result_map.get(a.source_id, {})
        a.cn_summary = r.get("cn_summary", a.summary[:200])
        tags = r.get("tags", [])
        if isinstance(tags, str):
            tags = [tags]
        # 用模糊匹配将 DeepSeek 返回的标签映射到预定义分类
        mapped_tags: list[str] = []
        for t in tags:
            t_lower = t.lower().strip()
            # 先精确匹配别名
            if t_lower in (k.lower() for k in TAG_ALIASES):
                for k, v in TAG_ALIASES.items():
                    if k.lower() == t_lower:
                        if v not in mapped_tags:
                            mapped_tags.append(v)
                        break
            else:
                # 再模糊匹配（标签中包含预定义分类关键词）
                for vt in VALID_TAGS:
                    if vt.lower().split("/")[0].strip() in t_lower:
                        if vt not in mapped_tags:
                            mapped_tags.append(vt)
                        break
        a.tags = mapped_tags or ["Other / 其他"]
        score = r.get("score", 2)
        if isinstance(score, (int, float)) and 1 <= score <= 5:
            a.score = int(score)
        else:
            a.score = 2

    return articles


async def summarize_all(
    articles: list[Article],
    batch_size: int = 15,
    client: Optional[AsyncOpenAI] = None,
) -> list[Article]:
    """分批处理全部文章。

    Args:
        articles: 全部文章
        batch_size: 每批数量（控制 token 消耗）
        client: AsyncOpenAI 客户端
    """
    if client is None:
        client = get_client()

    for i in range(0, len(articles), batch_size):
        batch = articles[i : i + batch_size]
        await summarize_batch(batch, client=client)

    return articles
