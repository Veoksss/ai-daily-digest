"""AI Daily Digest — 主入口

流程：
1. 并行抓取四个数据源
2. 去重、过滤、排序
3. DeepSeek API 摘要、分类、打分
4. 生成 HTML 日报页面
5. 发送邮件日报
"""

import asyncio
import os
import sys
from datetime import datetime, timezone

import httpx

from src.fetchers import (
    fetch_arxiv,
    fetch_paperswithcode,
    fetch_theverge,
    fetch_techcrunch,
)
from src.processor import process_articles
from src.summarizer import summarize_all
from src.generator import generate_html
from src.mailer import send_email


async def main():
    print("=" * 50)
    print(f"🤖 AI Daily Digest — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 50)

    # 1. 并行抓取
    print("\n📡 [1/5] 抓取数据源...")
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        results = await asyncio.gather(
            fetch_arxiv(client=client),
            fetch_paperswithcode(client=client),
            fetch_theverge(client=client),
            fetch_techcrunch(client=client),
            return_exceptions=True,
        )

    all_articles = []
    names = ["ArXiv", "Papers With Code", "The Verge", "TechCrunch"]
    for name, result in zip(names, results):
        if isinstance(result, Exception):
            print(f"  ❌ {name}: {result}")
        else:
            print(f"  ✅ {name}: {len(result)} 篇")
            all_articles.extend(result)

    if not all_articles:
        print("\n⚠️  没有抓取到任何文章，生成空页面。")
        from src.generator import OUTPUT_DIR
        import os as _os
        _os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(_os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write("<html><body><h2>今日无 AI 资讯</h2><p>请稍后再来</p></body></html>")
        return

    # 2. 去重过滤
    print(f"\n🔍 [2/5] 去重过滤 (输入 {len(all_articles)} 篇)...")
    clean = process_articles(all_articles)
    print(f"  ✅ 保留 {len(clean)} 篇")

    if not clean:
        print("⚠️  过滤后无文章，生成空页面。")
        from src.generator import OUTPUT_DIR
        import os as _os
        _os.makedirs(OUTPUT_DIR, exist_ok=True)
        with open(_os.path.join(OUTPUT_DIR, "index.html"), "w", encoding="utf-8") as f:
            f.write("<html><body><h2>今日无 AI 资讯</h2><p>请稍后再来</p></body></html>")
        return

    # 3. DeepSeek 摘要分类
    print(f"\n🧠 [3/5] DeepSeek 摘要分类 ({len(clean)} 篇)...")
    if not os.environ.get("DEEPSEEK_API_KEY"):
        print("  ⚠️  DEEPSEEK_API_KEY 未设置，跳过 LLM 处理（保留原文摘要）")
        for a in clean:
            a.cn_summary = a.summary[:200]
            a.tags = ["Other / 其他"]
            a.score = 2
    else:
        try:
            await summarize_all(clean)
            print(f"  ✅ 摘要完成")
        except Exception as e:
            print(f"  ⚠️  DeepSeek API 调用失败: {e}")
            print(f"  ⚠️  降级为原文摘要")
            for a in clean:
                a.cn_summary = a.summary[:200]
                a.tags = ["Other / 其他"]
                a.score = 2

    # 4. 生成 HTML
    print(f"\n📄 [4/5] 生成 HTML...")
    html_path = generate_html(clean)
    print(f"  ✅ {html_path}")

    # 5. 发送邮件
    print(f"\n📧 [5/5] 发送邮件...")
    send_email(clean)

    # 汇总
    print("\n" + "=" * 50)
    print("📊 今日汇总")
    print("=" * 50)
    sources = {}
    for a in clean:
        sources[a.source] = sources.get(a.source, 0) + 1
    for src, count in sources.items():
        print(f"  {src}: {count} 篇")

    top = sorted(clean, key=lambda a: a.score, reverse=True)[:5]
    if top:
        print("\n🏆 Top 5:")
        for i, a in enumerate(top, 1):
            print(f"  {i}. [{a.score}★] {a.title[:60]}...")

    print(f"\n✅ 完成！共 {len(clean)} 篇 AI 资讯")


if __name__ == "__main__":
    asyncio.run(main())
