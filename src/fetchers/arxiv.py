"""ArXiv API 抓取器

使用 ArXiv 官方 API，查询 AI 相关分类的最新论文。
API 文档: https://info.arxiv.org/help/api/
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx
import feedparser

from src.models import Article

# AI 相关分类
ARXIV_CATEGORIES = [
    "cs.AI",   # Artificial Intelligence
    "cs.CL",   # Computation and Language (NLP)
    "cs.CV",   # Computer Vision
    "cs.LG",   # Machine Learning
    "cs.NE",   # Neural and Evolutionary Computing
    "cs.MA",   # Multiagent Systems
    "cs.RO",   # Robotics
]

ARXIV_API = "https://export.arxiv.org/api/query"


async def fetch_arxiv(
    client: Optional[httpx.AsyncClient] = None,
    max_results: int = 50,
    lookback_hours: int = 24,
) -> list[Article]:
    """从 ArXiv 抓取近期 AI 论文。

    Args:
        client: httpx AsyncClient（复用连接）
        max_results: 最多返回条数
        lookback_hours: 往前看多少小时
    """
    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        close_client = True

    try:
        # 构造查询：多个分类 OR 连接
        cat_query = "+OR+".join(f"cat:{c}" for c in ARXIV_CATEGORIES)
        query = f"({cat_query})"
        url = (
            f"{ARXIV_API}?search_query={query}"
            f"&sortBy=submittedDate&sortOrder=descending"
            f"&start=0&max_results={max_results}"
        )

        resp = await client.get(url)
        resp.raise_for_status()

        feed = feedparser.parse(resp.text)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        articles: list[Article] = []
        for entry in feed.entries:
            published = _parse_date(entry.get("published", ""))
            if published and published < cutoff:
                continue

            # ArXiv ID 从 URL 中提取
            arxiv_id = entry.get("id", "").split("/abs/")[-1]

            articles.append(
                Article(
                    title=entry.get("title", "").strip().replace("\n", " "),
                    url=entry.get("link", ""),
                    source="arxiv",
                    published_at=published or datetime.now(timezone.utc),
                    summary=entry.get("summary", "").strip().replace("\n", " "),
                    source_id=f"arxiv:{arxiv_id}",
                )
            )

        return articles

    finally:
        if close_client:
            await client.aclose()


def _parse_date(date_str: str) -> Optional[datetime]:
    """解析 ArXiv 返回的日期字符串。"""
    if not date_str:
        return None
    # RFC 2822 格式，如 "Wed, 01 Jan 2025 00:00:00 GMT"
    try:
        from email.utils import parsedate_to_datetime
        return parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        pass
    # 尝试 ISO 格式
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
