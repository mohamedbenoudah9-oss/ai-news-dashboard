#!/usr/bin/env python3
"""Daily AI Blog Digest — bilingual (ZH + EN) email."""

import os, re, json, smtplib, subprocess, datetime, pathlib, urllib.request, urllib.error
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SCRIPT_DIR   = pathlib.Path(__file__).parent
ENV_FILE     = SCRIPT_DIR / ".env"
SKILL_DIR    = pathlib.Path.home() / ".claude/skills/tessl__ai-daily-digest"
OUTPUT_DIR   = SCRIPT_DIR / "output"          # inside the repo → auto-pushed to GitHub
TODAY        = datetime.date.today().strftime("%Y%m%d")
TODAY_PRETTY = datetime.date.today().strftime("%A, %B %-d %Y")
OUTPUT_FILE  = OUTPUT_DIR / f"digest-{TODAY}.md"

AI_API_KEY  = "sk-SeWFO1SOvjxq6dZWDqjrdtMzcqEmcmPXQbVjlbBrNCAazdbx"
AI_API_BASE = "https://hiapi.online/v1"
AI_MODEL    = "gemini-2.5-flash"

# ── Load .env ─────────────────────────────────────────────────────────────────
def load_env():
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())

load_env()
GMAIL_ADDRESS      = os.environ["GMAIL_ADDRESS"]
GMAIL_APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
RECIPIENT_EMAIL    = os.environ["RECIPIENT_EMAIL"]

# ── Run digest.ts ─────────────────────────────────────────────────────────────
def run_digest() -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["OPENAI_API_KEY"]  = AI_API_KEY
    env["OPENAI_API_BASE"] = AI_API_BASE
    env["OPENAI_MODEL"]    = AI_MODEL
    cmd = [
        "npx", "-y", "bun", str(SKILL_DIR / "scripts/digest.ts"),
        "--hours", "24", "--top-n", "10", "--lang", "zh",
        "--output", str(OUTPUT_FILE),
    ]
    print("[send_digest] Running digest script...")
    result = subprocess.run(cmd, env=env, capture_output=True, text=True)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr)
        raise RuntimeError(f"digest.ts exited with code {result.returncode}")
    return OUTPUT_FILE.read_text()

# ── Parse markdown → structured data ─────────────────────────────────────────
CAT_ZH_MAP = {
    "AI / ML":             ["🤖 AI / ML", "AI / ML"],
    "Security":            ["🔒 安全", "安全"],
    "Engineering":         ["⚙️ 工程", "工程"],
    "Tools & Open Source": ["🛠 工具 / 开源", "工具 / 开源"],
    "Opinion":             ["💡 观点 / 杂谈", "观点 / 杂谈"],
    "Other":               ["📝 其他", "其他"],
}
CAT_COLORS = {
    "AI / ML":             "#6366f1",
    "Security":            "#ef4444",
    "Engineering":         "#f59e0b",
    "Tools & Open Source": "#10b981",
    "Opinion":             "#8b5cf6",
    "Other":               "#64748b",
}
CAT_EMOJI = {
    "AI / ML": "🤖", "Security": "🔒", "Engineering": "⚙️",
    "Tools & Open Source": "🛠", "Opinion": "💡", "Other": "📝",
}

def zh_cat_to_en(zh: str) -> str:
    zh_clean = re.sub(r'^[^\w]+', '', zh).strip()
    for en, variants in CAT_ZH_MAP.items():
        for v in variants:
            if zh_clean in v or v in zh:
                return en
    return "Other"

def parse_digest_md(text: str) -> dict:
    result = {"highlights_zh": "", "stats": {}, "articles": []}

    # Highlights
    m = re.search(r'##\s*📝\s*今日看点\s*\n+(.*?)(?:\n---|\n##)', text, re.DOTALL)
    if m:
        result["highlights_zh"] = m.group(1).strip()

    # Stats
    m = re.search(r'\|\s*(\d+)/(\d+)\s*\|.*?(\d{4,})\s*篇.*?(\d+)\s*篇.*?\|\s*(\d+)h', text)
    if m:
        result["stats"] = {
            "sources_ok": m.group(1), "sources_total": m.group(2),
            "fetched": m.group(3), "recent": m.group(4),
        }
    m2 = re.search(r'精选\s*\|\s*\*\*(\d+)\s*篇\*\*', text)
    if m2 and result["stats"]:
        result["stats"]["selected"] = m2.group(1)

    # Articles by category section
    cat_sec = re.compile(
        r'^## ((?:🤖|🔒|⚙️|🛠|💡|📝)[^\n]+)\n(.*?)(?=\n## |\Z)',
        re.MULTILINE | re.DOTALL
    )
    art_pat = re.compile(
        r'### \d+\.\s+(.+?)\n\n'
        r'\[(.+?)\]\((.+?)\)'
        r'\s*[—–-]+\s*\*\*(.+?)\*\*'
        r'\s*·\s*(.+?)\s*·\s*⭐\s*(\d+)/30'
        r'.*?\n\n> (.*?)\n\n'
        r'🏷️\s*(.+?)(?:\n\n---|\n\n##|\Z)',
        re.DOTALL
    )
    for cat_m in cat_sec.finditer(text):
        cat_zh = cat_m.group(1).strip()
        if any(x in cat_zh for x in ["今日看点", "今日必读", "数据概览"]):
            continue
        cat_en = zh_cat_to_en(cat_zh)
        for am in art_pat.finditer(cat_m.group(2)):
            kws = [k.strip() for k in re.split(r'[,，]', am.group(8).strip()) if k.strip()]
            result["articles"].append({
                "title_zh":   am.group(1).strip(),
                "title_en":   am.group(2).strip(),
                "url":        am.group(3).strip(),
                "source":     am.group(4).strip(),
                "time_ago":   am.group(5).strip(),
                "score":      int(am.group(6)),
                "category":   cat_en,
                "summary_zh": am.group(7).strip(),
                "summary_en": "",   # filled by translate step
                "keywords":   kws,
            })

    result["articles"].sort(key=lambda a: a["score"], reverse=True)
    return result

# ── AI translation (single batch call) ───────────────────────────────────────
def ai_call(prompt: str) -> str:
    payload = json.dumps({
        "model": AI_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }).encode()
    req = urllib.request.Request(
        f"{AI_API_BASE}/chat/completions",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {AI_API_KEY}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]

def translate_to_english(data: dict) -> dict:
    """Translate highlights + all summaries to English in a single API call."""
    items = []
    if data["highlights_zh"]:
        items.append({"id": "highlights", "text": data["highlights_zh"]})
    for i, a in enumerate(data["articles"]):
        if a["summary_zh"]:
            items.append({"id": f"article_{i}", "text": a["summary_zh"]})

    if not items:
        return data

    print(f"[send_digest] Translating {len(items)} items to English...")
    prompt = f"""Translate each Chinese text to concise, natural English (2-4 sentences max per item).
Return ONLY a JSON array in this exact format, no other text:
[{{"id":"<id>","en":"<english translation>"}}]

Items to translate:
{json.dumps(items, ensure_ascii=False, indent=2)}"""

    try:
        raw = ai_call(prompt)
        # Extract JSON array from response
        m = re.search(r'\[[\s\S]*\]', raw)
        if not m:
            raise ValueError("No JSON array found in response")
        translations = {item["id"]: item["en"] for item in json.loads(m.group())}

        if "highlights" in translations:
            data["highlights_en"] = translations["highlights"]
        for i, a in enumerate(data["articles"]):
            key = f"article_{i}"
            if key in translations:
                a["summary_en"] = translations[key]
    except Exception as e:
        print(f"[send_digest] Translation failed: {e} — falling back to Chinese only")
        data["highlights_en"] = data.get("highlights_zh", "")
        for a in data["articles"]:
            a["summary_en"] = a["summary_zh"]

    return data

# ── Build bilingual HTML email ────────────────────────────────────────────────
def score_bar(score: int) -> str:
    pct = int(score / 30 * 100)
    color = "#16a34a" if score >= 24 else "#ca8a04" if score >= 18 else "#94a3b8"
    return (f'<div style="display:inline-flex;align-items:center;gap:6px">'
            f'<div style="background:#f1f5f9;border-radius:4px;height:6px;width:60px">'
            f'<div style="background:{color};width:{pct}%;height:6px;border-radius:4px"></div></div>'
            f'<span style="font-size:12px;color:{color};font-weight:700">{score}/30</span></div>')

def kw_tags_html(keywords: list) -> str:
    tags = "".join(
        f'<span style="display:inline-block;padding:2px 8px;border-radius:5px;'
        f'font-size:11px;background:#f1f5f9;color:#475569;border:1px solid #e2e8f0;'
        f'margin:2px 2px 2px 0">{k}</span>'
        for k in keywords[:6]
    )
    return f'<div style="margin-top:8px">{tags}</div>'

def article_block_html(a: dict, rank: int) -> str:
    color  = CAT_COLORS.get(a["category"], "#64748b")
    emoji  = CAT_EMOJI.get(a["category"], "📝")
    medal  = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"][rank] if rank < 10 else f"#{rank+1}"
    summary_zh = a["summary_zh"][:280] + ("…" if len(a["summary_zh"]) > 280 else "")
    summary_en = a["summary_en"][:280] + ("…" if len(a["summary_en"]) > 280 else "") if a["summary_en"] else ""

    return f"""
    <table width="100%" cellpadding="0" cellspacing="0" border="0"
           style="border:1px solid #e2e8f0;border-radius:12px;margin-bottom:16px;
                  background:#ffffff;border-left:4px solid {color};overflow:hidden">
      <tr>
        <td style="padding:20px 22px">

          <!-- rank + category + score -->
          <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:10px">
            <tr>
              <td>
                <span style="font-size:18px">{medal}</span>
                <span style="display:inline-block;padding:3px 10px;border-radius:20px;
                             font-size:11px;font-weight:600;margin-left:6px;
                             background:{color}18;color:{color};border:1px solid {color}40">
                  {emoji} {a['category']}
                </span>
              </td>
              <td align="right">{score_bar(a['score'])}</td>
            </tr>
          </table>

          <!-- EN title -->
          <div style="margin-bottom:4px">
            <a href="{a['url']}" target="_blank"
               style="font-size:15px;font-weight:700;color:#1a1a2e;text-decoration:none;line-height:1.5">
              {a['title_en']}
            </a>
          </div>
          <!-- ZH title -->
          <div style="font-size:13px;color:#64748b;margin-bottom:12px">{a['title_zh']}</div>

          <!-- Bilingual summaries -->
          <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:10px">
            <tr valign="top">
              <!-- English -->
              <td width="50%" style="padding-right:10px;border-right:1px solid #e2e8f0">
                <div style="font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:1px;
                            text-transform:uppercase;margin-bottom:5px">EN</div>
                <div style="font-size:13px;color:#334155;line-height:1.7">{summary_en or "<em style='color:#94a3b8'>—</em>"}</div>
              </td>
              <!-- Chinese -->
              <td width="50%" style="padding-left:10px">
                <div style="font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:1px;
                            text-transform:uppercase;margin-bottom:5px">中文</div>
                <div style="font-size:13px;color:#334155;line-height:1.7">{summary_zh}</div>
              </td>
            </tr>
          </table>

          {kw_tags_html(a['keywords'])}

          <!-- meta -->
          <div style="margin-top:10px;font-size:11px;color:#94a3b8">
            🔗 {a['source']} &nbsp;·&nbsp; 🕐 {a['time_ago']}
          </div>

        </td>
      </tr>
    </table>"""

def build_bilingual_html(data: dict) -> str:
    stats    = data.get("stats", {})
    articles = data.get("articles", [])
    hi_zh    = data.get("highlights_zh", "")
    hi_en    = data.get("highlights_en", "")

    # Stats row
    stat_items = [
        ("Sources",  f"{stats.get('sources_ok','—')}/{stats.get('sources_total','—')}"),
        ("Fetched",  stats.get("fetched", "—")),
        ("Selected", stats.get("selected", len(articles))),
        ("Period",   "24h"),
    ]
    stats_cells = "".join(
        f'<td align="center" style="padding:0 20px;border-right:1px solid #e2e8f0">'
        f'<div style="font-size:11px;color:#64748b;margin-bottom:4px;text-transform:uppercase;letter-spacing:1px;font-weight:600">{label}</div>'
        f'<div style="font-size:22px;font-weight:700;color:#1a1a2e">{val}</div></td>'
        for label, val in stat_items
    )

    # Highlights block
    highlights_html = ""
    if hi_zh or hi_en:
        highlights_html = f"""
        <table width="100%" cellpadding="0" cellspacing="0" border="0"
               style="background:#f8fafc;border-radius:10px;border:1px solid #e2e8f0;margin-bottom:24px">
          <tr>
            <td style="padding:18px 20px">
              <div style="font-size:11px;font-weight:700;color:#94a3b8;letter-spacing:2px;
                          text-transform:uppercase;margin-bottom:12px">✨ Today's Highlights</div>
              <table width="100%" cellpadding="0" cellspacing="0" border="0">
                <tr valign="top">
                  <td width="50%" style="padding-right:12px;border-right:1px solid #e2e8f0">
                    <div style="font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:1px;
                                text-transform:uppercase;margin-bottom:6px">EN</div>
                    <div style="font-size:14px;color:#334155;line-height:1.75">{hi_en or hi_zh}</div>
                  </td>
                  <td width="50%" style="padding-left:12px">
                    <div style="font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:1px;
                                text-transform:uppercase;margin-bottom:6px">中文</div>
                    <div style="font-size:14px;color:#334155;line-height:1.75">{hi_zh}</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>"""

    articles_html = "".join(article_block_html(a, i) for i, a in enumerate(articles))

    return f"""<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0f2f8;font-family:'Segoe UI',Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f0f2f8;padding:28px 0">
  <tr><td align="center">
  <table width="680" cellpadding="0" cellspacing="0" border="0" style="max-width:680px;width:100%">

    <!-- Dashboard link banner -->
    <tr>
      <td style="background:#1a1a2e;border-radius:10px 10px 0 0;padding:12px 24px;text-align:center">
        <span style="font-size:13px;color:#a8b2d8">🖥️ View full dashboard: </span>
        <a href="http://localhost:8501" target="_blank"
           style="font-size:13px;color:#7dd3fc;font-weight:600;text-decoration:none;
                  border-bottom:1px solid #7dd3fc30">
          http://localhost:8501
        </a>
      </td>
    </tr>

    <!-- Header -->
    <tr>
      <td style="background:#ffffff;border-top:3px solid #1a1a2e;
                 padding:28px 36px 24px">
        <p style="margin:0 0 4px;font-size:11px;color:#1a1a2e;
                  letter-spacing:2px;text-transform:uppercase;font-weight:600">Daily Briefing · AI Tech Blogs</p>
        <h1 style="margin:0 0 6px;font-size:26px;font-weight:700;color:#1a1a2e;letter-spacing:-0.5px">
          📰 AI 博客每日精选 · Daily Digest
        </h1>
        <p style="margin:0 0 20px;font-size:14px;color:#1a1a2e">{TODAY_PRETTY}</p>
        <!-- Stats -->
        <table cellpadding="0" cellspacing="0" border="0">
          <tr>{stats_cells}</tr>
        </table>
      </td>
    </tr>

    <!-- Body -->
    <tr>
      <td style="background:#ffffff;border-radius:0 0 14px 14px;padding:4px 36px 28px 36px;border-top:1px solid #e2e8f0">

        {highlights_html}

        <div style="font-size:16px;font-weight:700;color:#1a1a2e;
                    margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid #e2e8f0">
          🏆 Top Articles Today · 今日精选
        </div>

        {articles_html}

        <!-- Footer -->
        <hr style="border:none;border-top:1px solid #e2e8f0;margin:24px 0 16px">
        <p style="font-size:11px;color:#94a3b8;text-align:center;line-height:1.9;margin:0">
          Generated on {datetime.date.today()} &nbsp;·&nbsp;
          Based on <a href="https://refactoringenglish.com/tools/hn-popularity/" style="color:#94a3b8">
          Karpathy's 90 Top Tech Blogs</a><br>
          由「懂点儿AI」制作 &nbsp;·&nbsp; 每日 09:00 自动发送至 {RECIPIENT_EMAIL}
        </p>
      </td>
    </tr>

  </table>
  </td></tr>
</table>
</body>
</html>"""

# ── Plain-text fallback ───────────────────────────────────────────────────────
def build_plain(data: dict) -> str:
    lines = [
        f"AI Blog Daily Digest — {TODAY_PRETTY}",
        f"AI 博客每日精选 — {TODAY_PRETTY}",
        "=" * 60,
    ]
    if data.get("highlights_en"):
        lines += ["", "TODAY'S HIGHLIGHTS", data["highlights_en"],
                  "", "今日看点", data["highlights_zh"], ""]
    for i, a in enumerate(data["articles"]):
        lines += [
            f"\n{'─'*50}",
            f"{i+1}. {a['title_en']}",
            f"   {a['title_zh']}",
            f"   {a['url']}",
            f"   Source: {a['source']}  Score: {a['score']}/30  [{a['category']}]",
            f"   EN: {a['summary_en']}",
            f"   中文: {a['summary_zh']}",
            f"   Tags: {', '.join(a['keywords'][:5])}",
        ]
    lines += ["", "─" * 50,
              f"Powered by Karpathy's 90 Tech Blogs + Gemini 2.5 Flash",
              f"由「懂点儿AI」制作 · {datetime.date.today()}"]
    return "\n".join(lines)

# ── Send email ────────────────────────────────────────────────────────────────
def send_email(subject: str, html: str, plain: str):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"AI Blog Digest <{GMAIL_ADDRESS}>"
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_ADDRESS, GMAIL_APP_PASSWORD)
        server.sendmail(GMAIL_ADDRESS, RECIPIENT_EMAIL, msg.as_string())
    print(f"[send_digest] Email sent to {RECIPIENT_EMAIL}")

# ── Save JSON sidecar (for dashboard) ────────────────────────────────────────
def save_sidecar(data: dict):
    sidecar = OUTPUT_DIR / f"digest-{TODAY}.json"
    payload = {
        "highlights_en": data.get("highlights_en", ""),
        "highlights_zh": data.get("highlights_zh", ""),
        "articles": [
            {
                "url":        a["url"],
                "summary_en": a.get("summary_en", ""),
            }
            for a in data["articles"]
        ],
    }
    sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"[send_digest] Sidecar saved: {sidecar.name}")

# ── Push output files to GitHub (updates deployed dashboard) ─────────────────
def git_push():
    try:
        cmds = [
            ["git", "-C", str(SCRIPT_DIR), "add", "output/"],
            ["git", "-C", str(SCRIPT_DIR), "commit", "-m",
             f"digest: add {TODAY} report"],
            ["git", "-C", str(SCRIPT_DIR), "push"],
        ]
        for cmd in cmds:
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0 and "nothing to commit" not in r.stdout + r.stderr:
                print(f"[send_digest] git warning: {r.stderr.strip()}")
        print("[send_digest] Pushed to GitHub → dashboard updated")
    except Exception as e:
        print(f"[send_digest] git push failed: {e}")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    md_text  = run_digest()
    data     = parse_digest_md(md_text)
    data     = translate_to_english(data)
    save_sidecar(data)
    git_push()
    html     = build_bilingual_html(data)
    plain    = build_plain(data)
    subject  = f"📰 AI Digest · AI 博客精选 — {datetime.date.today()}"
    send_email(subject, html, plain)
