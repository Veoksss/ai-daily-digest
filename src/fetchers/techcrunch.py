"""TechCrunch RSS 抓取器

使用 TechCrunch AI 频道的 RSS 源。
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from email.utils import parsedate_to_datetime

import httpx
import feedparser

from src.models import Article

TC_AI_RSS = "https://techcrunch.com/category/artificial-intelligence/feed/"


async def fetch_techcrunch(
    client: Optional[httpx.AsyncClient] = None,
    max_results: int = 30,
    lookback_hours: int = 24,
) -> list[Article]:
    """从 TechCrunch AI 频道抓取最新文章。

    Args:
        client: httpx AsyncClient
        max_results: 最多返回条数
        lookback_hours: 往前看多少小时
    """
    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0)
        close_client = True

    try:
        resp = await client.get(TC_AI_RSS)
        resp.raise_for_status()

        feed = feedparser.parse(resp.text)
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

            import re
            summary = entry.get("summary", "") or entry.get("description", "")
            summary = re.sub(r"<[^>]+>", "", summary).strip()[:500]

            articles.append(
                Article(
                    title=entry.get("title", "").strip(),
                    url=entry.get("link", ""),
                    source="techcrunch",
                    published_at=published or datetime.now(timezone.utc),
                    summary=summary,
                    source_id=f"tc:{entry.get('id', entry.get('link', ''))}",
                )
            )

        return articles

    finally:
        if close_client:
            await client.aclose()
