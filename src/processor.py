"""去重与关键词过滤

合并四个源的文章后：
1. 按标题相似度去重（同一篇文章被多个源转发）
2. 按 AI 关键词过滤不相关内容
3. 只保留过去 24 小时的文章（fetcher 已做一轮，这里二次确保）
"""

from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher

from src.models import Article

# 必须包含至少一个 AI 关键词
AI_KEYWORDS = [
    "ai", "artificial intelligence", "machine learning", "deep learning",
    "llm", "large language model", "gpt", "chatgpt", "openai", "gemini",
    "claude", "transformer", "neural network", "nlp", "natural language",
    "computer vision", "cv", "robot", "robotics", "autonomous",
    "reinforcement learning", "rl", "diffusion model", "stable diffusion",
    "generative ai", "gen ai", "genai", "copilot", "copilot",
    "anthropic", "deepseek", "deepmind", "mistral", "llama", "falcon",
    "rag", "retrieval augmented", "fine-tun", "prompt engineer",
    "multimodal", "agent", "embedding", "vector database",
    "text-to-image", "text-to-video", "speech recognition", "tts",
    "foundation model", "frontier model",
    # Agent / 智能体 相关
    "ai agent", "intelligent agent", "autonomous agent", "agentic",
    "multi-agent", "agent framework", "tool use", "function calling",
    "agent workflow", "agent orchestration", "agent swarm",
    "computer use", "browser agent", "coding agent",
    "agent evaluation", "agent benchmark",
    # 中文关键词（以防 RSS 源有中文标题）
    "人工智能", "大模型", "机器学习", "深度学习", "自然语言",
    "计算机视觉", "自动驾驶", "智能体", "人形机器人",
    "agent", "代理", "自主决策", "多智能体",
]


def similarity(a: str, b: str) -> float:
    """计算两个字符串的相似度 (0.0 ~ 1.0)。"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def is_ai_related(article: Article) -> bool:
    """判断文章是否与 AI 相关。"""
    text = f"{article.title} {article.summary}".lower()
    for kw in AI_KEYWORDS:
        if kw in text:
            return True
    return False


def process_articles(
    articles: list[Article],
    dedup_threshold: float = 0.85,
    lookback_hours: int = 24,
) -> list[Article]:
    """去重、过滤、排序。

    Args:
        articles: 四个源抓取的全部文章
        dedup_threshold: 标题相似度阈值，超过视为重复
        lookback_hours: 时间窗口

    Returns:
        按时间倒序排列的干净文章列表
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    # 1. 时间窗口过滤
    articles = [a for a in articles if a.published_at >= cutoff]

    # 2. AI 关键词过滤
    articles = [a for a in articles if is_ai_related(a)]

    # 3. 去重：标题相似度 > threshold 视为重复，保留先出现的
    deduped: list[Article] = []
    seen_ids: set[str] = set()

    for article in articles:
        # 同源 ID 去重
        if article.source_id and article.source_id in seen_ids:
            continue
        if article.source_id:
            seen_ids.add(article.source_id)

        # 标题相似度去重
        is_dup = False
        for existing in deduped:
            if similarity(article.title, existing.title) >= dedup_threshold:
                is_dup = True
                break
        if not is_dup:
            deduped.append(article)

    # 4. 按发布时间倒序
    deduped.sort(key=lambda a: a.published_at, reverse=True)

    return deduped
