"""邮件发送

使用 SMTP 发送每日 AI 日报到指定邮箱。
支持 QQ 邮箱和 Gmail 等主流 SMTP 服务。
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timezone
from typing import Optional

from src.models import Article

# 来源中文名
SOURCE_LABELS = {
    "arxiv": "ArXiv",
    "paperswithcode": "Papers With Code",
    "theverge": "The Verge",
    "techcrunch": "TechCrunch",
}


def _build_email_html(articles: list[Article], date_str: str) -> str:
    """构建邮件正文 HTML（精简版，适合邮件客户端）。"""
    rows = []
    for a in articles[:30]:  # 邮件最多展示 30 条
        tags_html = " ".join(
            f'<span style="background:#e8eaf6;color:#3949ab;padding:2px 8px;border-radius:10px;font-size:12px;margin-right:4px;">{t}</span>'
            for t in a.tags
        )
        stars = "★" * a.score + "☆" * (5 - a.score)
        rows.append(f"""
        <tr>
            <td style="padding:12px 0;border-bottom:1px solid #eee;">
                <a href="{a.url}" style="color:#1a0dab;text-decoration:none;font-size:15px;font-weight:600;">
                    {a.title}
                </a>
                <div style="margin-top:4px;font-size:12px;color:#888;">
                    {SOURCE_LABELS.get(a.source, a.source)} · {a.published_at.strftime('%H:%M')} · {stars}
                    {tags_html}
                </div>
                <div style="margin-top:6px;font-size:13px;color:#555;">
                    {a.cn_summary}
                </div>
                <div style="margin-top:6px;font-size:12px;color:#6b5b3a;padding:8px 12px;background:#fffdf5;border-left:3px solid #f0c040;border-radius:0 6px 6px 0;">
                    💡 {a.plain_explanation}
                </div>
            </td>
        </tr>
        """)

    return f"""
    <html>
    <body style="font-family:-apple-system,BlinkMacSystemFont,sans-serif;max-width:650px;margin:0 auto;padding:20px;background:#f9f9f9;">
        <div style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:30px;border-radius:12px;text-align:center;margin-bottom:20px;">
            <h1 style="margin:0;font-size:24px;">🤖 AI Daily Digest</h1>
            <p style="margin:8px 0 0;opacity:0.85;">{date_str} · 共 {len(articles)} 篇</p>
        </div>
        <div style="background:white;padding:20px;border-radius:12px;">
            <table style="width:100%;border-collapse:collapse;">
                {''.join(rows)}
            </table>
        </div>
        <p style="text-align:center;color:#aaa;font-size:12px;margin-top:20px;">
            查看完整版：<a href="#" style="color:#667eea;">AI Daily Digest Web</a><br>
            由 AI Daily Digest 自动生成
        </p>
    </body>
    </html>
    """


def build_email_content(articles: list[Article]) -> tuple[str, str]:
    """构建邮件标题和 HTML 正文。

    Returns:
        (subject, html_body)
    """
    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")

    # 标题：取评分最高的 3 篇标题关键词
    top = sorted(articles, key=lambda a: a.score, reverse=True)[:3]
    highlights = " · ".join(a.title[:30] for a in top) if top else "今日 AI 速递"

    subject = f"🤖 AI 日报 {date_str} | {highlights}..."
    if len(subject) > 200:
        subject = subject[:197] + "..."

    body = _build_email_html(articles, date_str)

    return subject, body


def send_email(
    articles: list[Article],
    to_email: Optional[str] = None,
) -> bool:
    """发送日报邮件。

    从环境变量读取 SMTP 配置：
    - SMTP_HOST: SMTP 服务器地址
    - SMTP_PORT: 端口（默认 587）
    - SMTP_USER: 发件人邮箱
    - SMTP_PASS: SMTP 密码/授权码
    - SMTP_TO: 收件人（可逗号分隔多个）
    - SMTP_FROM_NAME: 发件人显示名（默认 "AI Daily Digest"）

    Returns:
        是否发送成功
    """
    smtp_host = os.environ.get("SMTP_HOST") or "smtp.qq.com"
    smtp_port_str = os.environ.get("SMTP_PORT") or "587"
    try:
        smtp_port = int(smtp_port_str)
    except (ValueError, TypeError):
        smtp_port = 587
    smtp_user = os.environ.get("SMTP_USER") or ""
    smtp_pass = os.environ.get("SMTP_PASS") or ""
    to_email = to_email or os.environ.get("SMTP_TO") or ""
    from_name = os.environ.get("SMTP_FROM_NAME") or "AI Daily Digest"

    if not smtp_user or not smtp_pass or not to_email:
        print("[mailer] SMTP 配置不完整，跳过邮件发送")
        print(f"  SMTP_USER={bool(smtp_user)}, SMTP_PASS={bool(smtp_pass)}, SMTP_TO={bool(to_email)}")
        return False

    subject, body = build_email_content(articles)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{from_name} <{smtp_user}>"
    msg["To"] = to_email
    msg.attach(MIMEText(body, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email.split(","), msg.as_string())
        print(f"[mailer] 邮件已发送到 {to_email}")
        return True
    except Exception as e:
        print(f"[mailer] 邮件发送失败: {e}")
        return False
