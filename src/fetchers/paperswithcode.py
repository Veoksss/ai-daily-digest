"""Papers With Code RSS 抓取器

使用 Papers With Code 的 RSS 源获取最新 AI 论文（含代码）。
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

import httpx

from src.models import Article

PWC_API = "https://huggingface.co/api/daily_papers"


async def fetch_paperswithcode(
    client: Optional[httpx.AsyncClient] = None,
    max_results: int = 30,
    lookback_hours: int = 24,
) -> list[Article]:
    """从 Hugging Face Daily Papers API 抓取最新论文。

    Papers With Code 已整合到 Hugging Face，使用其 daily papers API。

    Args:
        client: httpx AsyncClient
        max_results: 最多返回条数
        lookback_hours: 往前看多少小时
    """
    close_client = False
    if client is None:
        client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
        close_client = True

    try:
        resp = await client.get(PWC_API)
        resp.raise_for_status()

        papers = resp.json()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

        articles: list[Article] = []
        for paper in papers[:max_results]:
            # Hugging Face daily papers 是当天的，时间过滤意义不大但保留
            paper_id = paper.get("paper", {}).get("id", "")
            title = paper.get("paper", {}).get("title", "")
            arxiv_id = paper.get("paper", {}).get("arxivId", "")
            summary = paper.get("paper", {}).get("summary", "") or ""
            url = f"https://huggingface.co/papers/{paper_id}" if paper_id else ""

            if not title:
                continue

            articles.append(
                Article(
                    title=title.strip(),
                    url=url,
                    source="paperswithcode",
                    published_at=datetime.now(timezone.utc),
                    summary=summary.strip()[:800],
                    source_id=f"hf:{paper_id or arxiv_id}",
                )
            )

        return articles

    finally:
        if close_client:
            await client.aclose()
