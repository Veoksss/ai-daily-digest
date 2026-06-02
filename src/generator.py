"""HTML 生成器

使用 Jinja2 模板渲染日报网页。
"""

import os
from datetime import datetime, timezone

from jinja2 import Environment, FileSystemLoader

from src.models import Article

TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "templates")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "output")

SOURCE_LABELS = {
    "arxiv": "ArXiv",
    "paperswithcode": "Papers With Code",
    "theverge": "The Verge",
    "techcrunch": "TechCrunch",
}


def generate_html(articles: list[Article], output_dir: str = OUTPUT_DIR) -> str:
    """生成日报 HTML 文件。

    Args:
        articles: 处理后的文章列表（已含 cn_summary/tags/score）
        output_dir: 输出目录

    Returns:
        生成的 HTML 文件路径
    """
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=True,
    )
    template = env.get_template("index.html.j2")

    # 提取所有标签
    all_tags = sorted(set(tag for a in articles for tag in a.tags))

    # 计算平均分
    avg_score = sum(a.score for a in articles) / max(len(articles), 1)

    # 提取所有来源
    sources = sorted(set(a.source for a in articles))

    # 准备模板数据
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    articles_data = []
    for a in articles:
        articles_data.append({
            "title": a.title,
            "url": a.url,
            "source": a.source,
            "source_label": SOURCE_LABELS.get(a.source, a.source),
            "published_at": a.published_at.strftime("%Y-%m-%d %H:%M UTC"),
            "cn_summary": a.cn_summary,
            "tags": a.tags,
            "score": a.score,
        })

    html = template.render(
        date=date_str,
        articles=articles_data,
        total=len(articles_data),
        avg_score=round(avg_score, 1),
        all_tags=all_tags,
        sources=sources,
        generated_at=now.strftime("%Y-%m-%d %H:%M UTC"),
    )

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "index.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    return output_path
