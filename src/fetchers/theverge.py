"""The Verge RSS 抓取器

使用 The Verge AI 频道的 RSS 源。
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from email.utils import parsedate_to_datetime

import httpx
import feedparser

from src.models import Article

# The Verge AI 频道 RSS（尝试 AI 专属 feed，不可用时回退主 feed）
VERGE_AI_RSS = "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"
VERGE_MAIN_RSS = "https://www.theverge.com/rss/index.xml"


async def fetch_theverge(
    client: Optional[httpx.AsyncClient] = None,
    max_results: int = 30,
    lookback_hours: int = 24,
) -> list[Article]:
    """从 The Verge AI 频道抓取最新文章。

    先尝试 AI 专属 RSS，404 则回退到主 feed（后续由 processor 的 AI 关键词过滤）。

    Args:
        client: httpx AsyncClient
        max_results: 最多返回条数
        lookback_hours: 往前看多少小时
    """
    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        close_client = True

    async def _fetch_url(url: str) -> str:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.text

    try:
        try:
            text = await _fetch_url(VERGE_AI_RSS)
        except httpx.HTTPStatusError:
            text = await _fetch_url(VERGE_MAIN_RSS)

        feed = feedparser.parse(text)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        articles: list[Article] = []
        for entry in feed.entries[:max_results]:
            raw_date = entry.get("published", "") or entry.get("updated", "")
            published = None
            if raw_date:
                try:
                    published = parsedate_to_datetime(raw_date)
                except (ValueError, TypeError):
                    pass
            if published and published < cutoff:
                continue

            # 提取纯文本摘要（去除 HTML 标签）
            import re
            summary = entry.get("summary", "") or entry.get("description", "")
            summary = re.sub(r"<[^>]+>", "", summary).strip()[:500]

            articles.append(
                Article(
                    title=entry.get("title", "").strip(),
                    url=entry.get("link", ""),
                    source="theverge",
                    published_at=published or datetime.now(timezone.utc),
                    summary=summary,
                    source_id=f"verge:{entry.get('id', entry.get('link', ''))}",
                )
            )

        return articles

    finally:
        if close_client:
            await client.aclose()
