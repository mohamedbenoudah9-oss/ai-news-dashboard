"""AI Blog Digest Dashboard — run with: streamlit run dashboard.py"""

import re
import json
import datetime
import pathlib
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

OUTPUT_DIR = pathlib.Path(__file__).parent / "output"

st.set_page_config(
    page_title="AI Blog Digest",
    page_icon="📰",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
  * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; }

  .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }

  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #0f3460 100%);
    border-right: none;
  }
  [data-testid="stSidebar"] * { color: #e2e8f0 !important; }
  [data-testid="stSidebar"] hr { border-color: rgba(255,255,255,0.1) !important; margin: 20px 0 !important; }

  .main .block-container { padding: 2rem 3rem; max-width: 1400px; margin: 0 auto; }

  h1 { color: #1a1a2e !important; font-weight: 700 !important; font-size: 2.2rem !important;
       letter-spacing: -0.02em !important; margin-bottom: 0.3rem !important; }
  h2, h3, h4 { color: #2d3748 !important; font-weight: 600 !important; letter-spacing: -0.01em !important; }

  .metric-card {
    background: rgba(255,255,255,0.92); backdrop-filter: blur(10px);
    border-radius: 16px; padding: 24px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08); border: 1px solid rgba(255,255,255,0.5);
    transition: all 0.3s ease; height: 100%;
  }
  .metric-card:hover { transform: translateY(-4px); box-shadow: 0 8px 30px rgba(0,0,0,0.12); }

  .article-card {
    background: rgba(255,255,255,0.95); backdrop-filter: blur(10px);
    border-radius: 12px; padding: 20px; margin-bottom: 14px;
    border: 1px solid rgba(255,255,255,0.6); box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    transition: all 0.3s ease;
  }
  .article-card:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,0,0,0.1); }
  .article-card a { color: #1a1a2e; font-weight: 600; text-decoration: none; font-size: 15px; line-height: 1.5; }
  .article-card a:hover { color: #0f3460; }

  .highlight-box {
    background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
    border-radius: 14px; padding: 24px 28px; color: white; margin-bottom: 24px;
    box-shadow: 0 8px 24px rgba(15,52,96,0.25);
  }

  .top3-card {
    background: rgba(255,255,255,0.95); border-radius: 12px; padding: 20px;
    border: 1px solid rgba(255,255,255,0.6); box-shadow: 0 4px 16px rgba(0,0,0,0.08);
    margin-bottom: 14px; transition: all 0.3s;
  }
  .top3-card:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.12); transform: translateY(-2px); }

  .score-badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 12px; font-weight: 600; background: #fef3c7; color: #92400e;
  }

  .cat-badge {
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 11px; font-weight: 500; margin-right: 6px;
  }

  .kw-tag {
    display: inline-block; padding: 3px 8px; border-radius: 6px;
    font-size: 11px; background: #f1f5f9; color: #475569;
    margin: 2px; border: 1px solid #e2e8f0;
  }

  .stButton > button {
    border-radius: 10px; font-weight: 500; padding: 0.5rem 1.5rem;
    border: none; background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
    color: white; transition: all 0.2s;
  }
  .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(15,52,96,0.35); }
</style>
""", unsafe_allow_html=True)

# ── Category config ────────────────────────────────────────────────────────────
CATEGORIES = {
    "AI / ML":              {"color": "#6366f1", "bg": "#eef2ff", "emoji": "🤖"},
    "Security":             {"color": "#ef4444", "bg": "#fef2f2", "emoji": "🔒"},
    "Engineering":          {"color": "#f59e0b", "bg": "#fffbeb", "emoji": "⚙️"},
    "Tools & Open Source":  {"color": "#10b981", "bg": "#ecfdf5", "emoji": "🛠"},
    "Opinion":              {"color": "#8b5cf6", "bg": "#f5f3ff", "emoji": "💡"},
    "Other":                {"color": "#64748b", "bg": "#f8fafc", "emoji": "📝"},
}

CAT_ZH_MAP = {
    "AI / ML":             ["🤖 AI / ML", "AI / ML", "ai-ml"],
    "Security":            ["🔒 安全", "安全", "security"],
    "Engineering":         ["⚙️ 工程", "工程", "engineering"],
    "Tools & Open Source": ["🛠 工具 / 开源", "工具 / 开源", "tools"],
    "Opinion":             ["💡 观点 / 杂谈", "观点 / 杂谈", "opinion"],
    "Other":               ["📝 其他", "其他", "other"],
}

def zh_cat_to_en(zh: str) -> str:
    zh_clean = re.sub(r'^[^\w]+', '', zh).strip()
    for en, variants in CAT_ZH_MAP.items():
        for v in variants:
            if zh_clean in v or v in zh or zh_clean == re.sub(r'^[^\w]+', '', v).strip():
                return en
    return "Other"

# ── Markdown parser ────────────────────────────────────────────────────────────
def load_sidecar(filepath: pathlib.Path) -> dict:
    """Load JSON sidecar with English translations (keyed by URL)."""
    sidecar = filepath.with_suffix(".json")
    if not sidecar.exists():
        return {}
    try:
        data = json.loads(sidecar.read_text())
        en_map = {a["url"]: a.get("summary_en", "") for a in data.get("articles", [])}
        en_map["__highlights_en__"] = data.get("highlights_en", "")
        en_map["__highlights_zh__"] = data.get("highlights_zh", "")
        return en_map
    except Exception:
        return {}


def parse_digest(filepath: pathlib.Path) -> dict:
    text = filepath.read_text(encoding="utf-8")
    result = {"date": None, "stats": {}, "highlights_zh": "", "highlights_en": "", "articles": []}
    en_map = load_sidecar(filepath)

    # Date from filename
    m = re.search(r'digest-(\d{4})(\d{2})(\d{2})\.md', filepath.name)
    if m:
        result["date"] = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # Highlights
    m = re.search(r'##\s*📝\s*今日看点\s*\n+(.*?)(?:\n---|\n##)', text, re.DOTALL)
    if m:
        result["highlights_zh"] = m.group(1).strip()
    result["highlights_en"] = en_map.get("__highlights_en__", "")

    # Stats table
    m = re.search(r'\|\s*(\d+)/(\d+)\s*\|.*?(\d{4,})\s*篇.*?(\d+)\s*篇.*?\|.*?(\d+)h', text)
    if m:
        result["stats"] = {
            "sources_ok": int(m.group(1)), "sources_total": int(m.group(2)),
            "fetched": int(m.group(3)), "recent": int(m.group(4)), "hours": int(m.group(5)),
        }
    # Also try: selected count from "精选 8 篇"
    m2 = re.search(r'精选\s*\|\s*\*\*(\d+)\s*篇\*\*', text)
    if m2 and result["stats"]:
        result["stats"]["selected"] = int(m2.group(1))

    # Articles — split by category sections then parse each article block
    # Split on ## headings that represent categories
    cat_section_pattern = re.compile(
        r'^## ((?:🤖|🔒|⚙️|🛠|💡|📝)[^\n]+)\n(.*?)(?=\n## |\Z)',
        re.MULTILINE | re.DOTALL
    )
    for cat_match in cat_section_pattern.finditer(text):
        cat_zh = cat_match.group(1).strip()
        # Skip non-article sections
        if any(x in cat_zh for x in ["今日看点", "今日必读", "数据概览"]):
            continue
        cat_en = zh_cat_to_en(cat_zh)
        section_body = cat_match.group(2)

        # Match individual article blocks
        art_pattern = re.compile(
            r'### \d+\.\s+(.+?)\n\n'           # zh title
            r'\[(.+?)\]\((.+?)\)'               # [orig title](url)
            r'\s*[—–-]+\s*\*\*(.+?)\*\*'        # source
            r'\s*·\s*(.+?)\s*·\s*⭐\s*(\d+)/30' # time · score
            r'.*?\n\n> (.*?)\n\n'               # summary
            r'🏷️\s*(.+?)(?:\n\n---|\n\n##|\Z)', # keywords
            re.DOTALL
        )
        for am in art_pattern.finditer(section_body):
            kw_raw = am.group(8).strip()
            keywords = [k.strip() for k in re.split(r'[,，]', kw_raw) if k.strip()]
            url = am.group(3).strip()
            result["articles"].append({
                "title_zh":   am.group(1).strip(),
                "title":      am.group(2).strip(),
                "url":        url,
                "source":     am.group(4).strip(),
                "time_ago":   am.group(5).strip(),
                "score":      int(am.group(6)),
                "category":   cat_en,
                "summary_zh": am.group(7).strip(),
                "summary_en": en_map.get(url, ""),
                "keywords":   keywords,
                "date":       result["date"],
            })

    result["articles"].sort(key=lambda a: a["score"], reverse=True)
    return result


@st.cache_data(ttl=300)
def load_all_digests() -> list[dict]:
    files = sorted(OUTPUT_DIR.glob("digest-*.md"), reverse=True)
    digests = []
    for f in files:
        try:
            d = parse_digest(f)
            if d["date"]:
                digests.append(d)
        except Exception:
            pass
    return digests


def all_articles_df(digests: list[dict]) -> pd.DataFrame:
    rows = []
    for d in digests:
        for a in d["articles"]:
            rows.append(a)
    return pd.DataFrame(rows) if rows else pd.DataFrame()


def score_color(score: int) -> str:
    if score >= 24: return "#16a34a"
    if score >= 18: return "#ca8a04"
    return "#64748b"


def cat_badge(cat: str) -> str:
    cfg = CATEGORIES.get(cat, CATEGORIES["Other"])
    return (f'<span class="cat-badge" style="background:{cfg["bg"]};color:{cfg["color"]};'
            f'border:1px solid {cfg["color"]}30">{cfg["emoji"]} {cat}</span>')


def kw_tags(keywords: list[str]) -> str:
    return " ".join(f'<span class="kw-tag">{k}</span>' for k in keywords[:6])


def article_card(a: dict, show_date: bool = False) -> str:
    score_c  = score_color(a["score"])
    date_str = f'&nbsp;·&nbsp; 📅 {a["date"]}' if show_date else ""
    s_zh = a.get("summary_zh", a.get("summary", ""))
    s_en = a.get("summary_en", "")
    s_zh_short = s_zh[:260] + ("…" if len(s_zh) > 260 else "")
    s_en_short = s_en[:260] + ("…" if len(s_en) > 260 else "") if s_en else ""

    # bilingual summary block — flex, no table
    if s_en_short:
        summary_block = (
            f'<div style="display:flex;gap:0;margin-top:10px;border-top:1px solid #f1f5f9;padding-top:10px">'
            f'<div style="flex:1;padding-right:10px;border-right:1px solid #f1f5f9">'
            f'<div style="font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px">EN</div>'
            f'<div style="font-size:13px;color:#475569;line-height:1.7">{s_en_short}</div>'
            f'</div>'
            f'<div style="flex:1;padding-left:10px">'
            f'<div style="font-size:10px;font-weight:700;color:#94a3b8;letter-spacing:1px;text-transform:uppercase;margin-bottom:4px">中文</div>'
            f'<div style="font-size:13px;color:#475569;line-height:1.7">{s_zh_short}</div>'
            f'</div>'
            f'</div>'
        )
    else:
        summary_block = f'<div style="font-size:13px;color:#475569;margin-top:10px;line-height:1.7">{s_zh_short}</div>'

    return f"""
    <div class="article-card">
      <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
        <div style="flex:1">
          {cat_badge(a['category'])}
          <a href="{a['url']}" target="_blank" style="display:block;margin-top:8px;font-size:15px;font-weight:700;color:#1a1a2e;text-decoration:none">{a['title']}</a>
          <div style="font-size:12px;color:#64748b;margin-top:3px;font-style:italic">{a['title_zh']}</div>
          {summary_block}
          <div style="margin-top:10px">{kw_tags(a['keywords'])}</div>
          <div style="margin-top:8px;font-size:11px;color:#94a3b8">
            🔗 {a['source']} &nbsp;·&nbsp; 🕐 {a['time_ago']}{date_str}
          </div>
        </div>
        <div style="text-align:center;min-width:52px">
          <div style="font-size:20px;font-weight:700;color:{score_c}">{a['score']}</div>
          <div style="font-size:10px;color:#94a3b8;letter-spacing:0.5px">/30</div>
        </div>
      </div>
    </div>"""

# ── Load data ─────────────────────────────────────────────────────────────────
digests = load_all_digests()
today_digest = digests[0] if digests else None

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📰 AI Blog Digest")
    st.markdown("*Karpathy's 90 Tech Blogs · Daily*")
    st.markdown("---")
    page = st.radio("Navigate", [
        "🏠 Today's Digest",
        "🔥 Hot Keywords",
        "📈 Trends",
        "🗂️ By Category",
        "🔍 Search",
        "📅 Archive",
    ])
    st.markdown("---")
    if digests:
        st.markdown(f"**Digests available:** {len(digests)}")
        st.markdown(f"**Latest:** {digests[0]['date']}")
        if len(digests) > 1:
            st.markdown(f"**Oldest:** {digests[-1]['date']}")
        total_arts = sum(len(d["articles"]) for d in digests)
        st.markdown(f"**Total articles:** {total_arts}")
    else:
        st.warning("No digest files found in ~/output/")

# ── Page: Today's Digest ──────────────────────────────────────────────────────
if page == "🏠 Today's Digest":
    st.title("📰 AI Blog Digest")
    st.markdown(f"*{datetime.date.today().strftime('%A, %B %-d %Y')} · Top tech blogs curated by Andrej Karpathy*")
    st.markdown("---")

    if not today_digest:
        st.warning("No digest found. Run `send_digest.py` to generate today's report.")
        st.stop()

    # Stats row
    stats = today_digest.get("stats", {})
    arts = today_digest["articles"]
    cats = list({a["category"] for a in arts})
    top_kw = ""
    if arts:
        all_kw = [k for a in arts for k in a["keywords"]]
        if all_kw:
            from collections import Counter
            top_kw = Counter(all_kw).most_common(1)[0][0].title()

    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, grad in [
        (c1, "Sources Scanned",  f"{stats.get('sources_ok','—')}/{stats.get('sources_total','—')}",
              "linear-gradient(135deg,#667eea,#764ba2)"),
        (c2, "Articles Fetched", stats.get("fetched", "—"),
              "linear-gradient(135deg,#f093fb,#f5576c)"),
        (c3, "Selected Today",   len(arts),
              "linear-gradient(135deg,#4facfe,#00f2fe)"),
        (c4, "Top Keyword",      top_kw or "—",
              "linear-gradient(135deg,#43e97b,#38f9d7)"),
    ]:
        col.markdown(f"""
        <div class="metric-card">
          <div style="font-size:11px;color:#718096;margin-bottom:12px;text-transform:uppercase;letter-spacing:1px;font-weight:600">{label}</div>
          <div style="font-size:30px;font-weight:700;background:{grad};-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;line-height:1.1">{val}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Today's Highlights — bilingual
    hi_zh = today_digest.get("highlights_zh", "")
    hi_en = today_digest.get("highlights_en", "")
    if hi_zh or hi_en:
        if hi_en:
            hi_body = (
                f'<div style="display:flex;gap:0">'
                f'<div style="flex:1;padding-right:14px;border-right:1px solid rgba(255,255,255,0.2)">'
                f'<div style="font-size:10px;color:#8892b0;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">EN</div>'
                f'<div style="font-size:14px;line-height:1.8;color:#e2e8f0">{hi_en}</div>'
                f'</div>'
                f'<div style="flex:1;padding-left:14px">'
                f'<div style="font-size:10px;color:#8892b0;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">中文</div>'
                f'<div style="font-size:14px;line-height:1.8;color:#e2e8f0">{hi_zh}</div>'
                f'</div>'
                f'</div>'
            )
        else:
            hi_body = f'<div style="font-size:14px;line-height:1.8;color:#e2e8f0">{hi_zh}</div>'
        st.markdown(f"""
        <div class="highlight-box">
          <div style="font-size:11px;color:#a8b2d8;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px">
            ✨ Today's Highlights · 今日看点
          </div>
          {hi_body}
        </div>""", unsafe_allow_html=True)

    # Top articles
    st.markdown("### 🏆 Top Articles Today")
    if not arts:
        st.info("No articles found in today's digest.")
    else:
        for a in arts[:10]:
            st.markdown(article_card(a), unsafe_allow_html=True)

# ── Page: Hot Keywords ────────────────────────────────────────────────────────
elif page == "🔥 Hot Keywords":
    st.title("🔥 Hot Keywords")

    df = all_articles_df(digests)
    if df.empty or "keywords" not in df.columns:
        st.info("Not enough data yet — run the digest for a few days.")
        st.stop()

    from collections import Counter
    all_kw = [k for kws in df["keywords"] for k in kws]
    kw_counts = Counter(all_kw).most_common(40)
    kw_df = pd.DataFrame(kw_counts, columns=["keyword", "count"])

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = px.bar(
            kw_df.head(20), x="count", y="keyword", orientation="h",
            title="Top 20 Keywords (All Time)",
            labels={"count": "Mentions", "keyword": ""},
            color="count", color_continuous_scale=["#c7d2fe", "#4338ca"],
        )
        fig.update_layout(
            yaxis=dict(autorange="reversed"), coloraxis_showscale=False,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter", size=12, color="#2a2a2a"),
            title_font=dict(size=18, color="#1a1a1a"),
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("### All Keywords")
        max_v = kw_df["count"].max() if not kw_df.empty else 1
        for _, row in kw_df.iterrows():
            pct = int(row["count"] / max_v * 100)
            st.markdown(f"""
            <div style="margin-bottom:7px;padding:9px 12px;background:white;border-radius:8px;border:1px solid #f0f0f0">
              <span style="font-size:13px;font-weight:600;color:#1a1a1a">{row.keyword}</span>
              <span style="float:right;font-size:12px;color:#888;font-weight:500">{int(row['count'])}</span>
              <div style="background:#f5f5f5;border-radius:4px;height:5px;margin-top:7px">
                <div style="background:#667eea;width:{pct}%;height:5px;border-radius:4px"></div>
              </div>
            </div>""", unsafe_allow_html=True)

# ── Page: Trends ──────────────────────────────────────────────────────────────
elif page == "📈 Trends":
    st.title("📈 Trends Over Time")

    df = all_articles_df(digests)
    if df.empty or len(digests) < 2:
        st.info("Need at least 2 days of digests to show trends.")
        st.stop()

    df["date"] = pd.to_datetime(df["date"])

    # Articles per day
    daily = df.groupby("date").size().reset_index(name="count")
    fig1 = px.bar(
        daily, x="date", y="count", title="Articles per Day",
        labels={"date": "Date", "count": "Articles"},
        color_discrete_sequence=["#6366f1"],
    )
    fig1.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=12), title_font=dict(size=18),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Score distribution over time
    avg_score = df.groupby("date")["score"].mean().reset_index()
    avg_score.columns = ["date", "avg_score"]
    fig2 = px.line(
        avg_score, x="date", y="avg_score",
        title="Average Article Score per Day",
        labels={"date": "Date", "avg_score": "Avg Score"},
        markers=True,
    )
    fig2.update_traces(line_color="#0f3460", marker=dict(size=7, color="#0f3460"))
    fig2.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=12), title_font=dict(size=18),
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Articles by category over time
    cat_daily = df.groupby(["date", "category"]).size().reset_index(name="count")
    color_map = {cat: cfg["color"] for cat, cfg in CATEGORIES.items()}
    fig3 = px.line(
        cat_daily, x="date", y="count", color="category",
        title="Articles by Category Over Time",
        labels={"date": "Date", "count": "Articles"},
        markers=True, color_discrete_map=color_map,
    )
    fig3.update_traces(marker=dict(size=6), line=dict(width=2))
    fig3.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=12), title_font=dict(size=18),
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig3, use_container_width=True)

# ── Page: By Category ─────────────────────────────────────────────────────────
elif page == "🗂️ By Category":
    st.title("🗂️ Browse by Category")

    df = all_articles_df(digests)
    if df.empty:
        st.info("No articles yet.")
        st.stop()

    # Donut chart
    cat_counts = df["category"].value_counts().reset_index()
    cat_counts.columns = ["category", "total"]
    colors = [CATEGORIES.get(c, CATEGORIES["Other"])["color"] for c in cat_counts["category"]]

    fig = go.Figure(go.Pie(
        labels=cat_counts["category"], values=cat_counts["total"],
        hole=0.55, marker=dict(colors=colors, line=dict(color="white", width=2)),
        textinfo="label+percent", textfont=dict(size=13, family="Inter"),
    ))
    fig.update_layout(
        title="All-time Articles by Category",
        paper_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter", size=12),
        title_font=dict(size=18), margin=dict(l=20, r=20, t=50, b=20), showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    cat_choice = st.selectbox(
        "Browse category",
        list(CATEGORIES.keys()),
        format_func=lambda c: f"{CATEGORIES[c]['emoji']} {c}",
    )
    filtered = df[df["category"] == cat_choice].sort_values("score", ascending=False)
    st.markdown(f"#### {CATEGORIES[cat_choice]['emoji']} {cat_choice} — {len(filtered)} articles")
    for _, row in filtered.head(20).iterrows():
        st.markdown(article_card(row.to_dict(), show_date=True), unsafe_allow_html=True)

# ── Page: Search ──────────────────────────────────────────────────────────────
elif page == "🔍 Search":
    st.title("🔍 Search Articles")

    q = st.text_input("Search by title, keyword, or source", placeholder="e.g. OpenAI, security, Claude…")
    df = all_articles_df(digests)

    if q and not df.empty:
        ql = q.lower()
        mask = (
            df["title"].str.lower().str.contains(ql, na=False) |
            df["title_zh"].str.lower().str.contains(ql, na=False) |
            df["summary_zh"].str.lower().str.contains(ql, na=False) |
            df["summary_en"].str.lower().str.contains(ql, na=False) |
            df["source"].str.lower().str.contains(ql, na=False) |
            df["keywords"].apply(lambda kws: any(ql in k.lower() for k in kws))
        )
        results = df[mask].sort_values("score", ascending=False)
        st.markdown(f"**{len(results)} results** for *{q}*")
        for _, row in results.iterrows():
            st.markdown(article_card(row.to_dict(), show_date=True), unsafe_allow_html=True)
    elif q:
        st.info("No articles found.")

# ── Page: Archive ─────────────────────────────────────────────────────────────
elif page == "📅 Archive":
    st.title("📅 Archive")

    if not digests:
        st.info("No digest files found.")
        st.stop()

    date_options = [d["date"] for d in digests]
    selected_date = st.selectbox(
        "Select date",
        date_options,
        format_func=lambda d: d.strftime("%A, %B %-d %Y"),
    )

    selected = next((d for d in digests if d["date"] == selected_date), None)
    if not selected:
        st.warning("Digest not found.")
        st.stop()

    st.markdown(f"### {selected_date.strftime('%B %-d, %Y')} — {len(selected['articles'])} articles")

    arc_zh = selected.get("highlights_zh", "")
    arc_en = selected.get("highlights_en", "")
    if arc_zh or arc_en:
        if arc_en:
            arc_body = (
                f'<div style="display:flex;gap:0">'
                f'<div style="flex:1;padding-right:14px;border-right:1px solid rgba(255,255,255,0.2)">'
                f'<div style="font-size:10px;color:#8892b0;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">EN</div>'
                f'<div style="font-size:14px;line-height:1.8;color:#e2e8f0">{arc_en}</div>'
                f'</div>'
                f'<div style="flex:1;padding-left:14px">'
                f'<div style="font-size:10px;color:#8892b0;letter-spacing:1px;text-transform:uppercase;margin-bottom:6px">中文</div>'
                f'<div style="font-size:14px;line-height:1.8;color:#e2e8f0">{arc_zh}</div>'
                f'</div>'
                f'</div>'
            )
        else:
            arc_body = f'<div style="font-size:14px;line-height:1.8;color:#e2e8f0">{arc_zh}</div>'
        st.markdown(f"""
        <div class="highlight-box">
          <div style="font-size:11px;color:#a8b2d8;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px">
            ✨ Highlights · 今日看点
          </div>
          {arc_body}
        </div>""", unsafe_allow_html=True)

    for cat_name, cfg in CATEGORIES.items():
        cat_arts = [a for a in selected["articles"] if a["category"] == cat_name]
        if not cat_arts:
            continue
        with st.expander(f"{cfg['emoji']} {cat_name} ({len(cat_arts)})", expanded=True):
            for a in sorted(cat_arts, key=lambda x: x["score"], reverse=True):
                st.markdown(article_card(a), unsafe_allow_html=True)
