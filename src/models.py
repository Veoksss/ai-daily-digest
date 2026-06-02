"""统一数据模型"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Article:
    """抓取后的原始文章，所有 fetcher 统一输出此结构"""

    title: str
    url: str
    source: str  # arxiv / paperswithcode / theverge / techcrunch
    published_at: datetime
    summary: str  # 原始摘要或导语
    content: str = ""  # 正文（如果有）
    source_id: str = ""  # 源站唯一 ID，用于去重

    # LLM 处理后填充
    cn_summary: str = ""
    tags: list[str] = field(default_factory=list)
    score: int = 0  # 1-5 重要性
    plain_explanation: str = ""  # 通俗解读：用大白话解释含义、未来走向、发展潜力
