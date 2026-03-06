"""AI News Dashboard — run with: streamlit run dashboard.py"""

import datetime
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(
    page_title="AI News Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  [data-testid="stSidebar"] { background: #1a1a2e; }
  [data-testid="stSidebar"] * { color: #a8b2d8 !important; }
  .metric-card {
    background: #ffffff; border-radius: 12px; padding: 20px 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07); border-left: 4px solid;
  }
  .article-card {
    background: #f8f9fc; border-radius: 10px; padding: 14px 18px;
    margin-bottom: 10px; border-left: 4px solid #6C63FF;
  }
  .article-card a { color: #1a1a2e; font-weight: 600; text-decoration: none; }
  .article-card .source { font-size:12px; color:#6C63FF; margin-top:4px; }
  h1, h2, h3 { color: #1a1a2e; }
</style>
""", unsafe_allow_html=True)

SECTION_COLORS = {
    "Top AI News":          "#6C63FF",
    "Model & Research":     "#00BFA5",
    "Regulation & Policy":  "#FF6B6B",
    "Investment & Funding": "#FFA940",
}

# ── DB connection (Supabase in cloud, SQLite locally) ─────────────────────────
@st.cache_resource
def get_conn():
    try:
        import psycopg2
        cfg = st.secrets["supabase"]
        conn = psycopg2.connect(
            host=cfg["host"], port=cfg["port"],
            dbname=cfg["database"], user=cfg["user"], password=cfg["password"],
            sslmode="require",
        )
        return conn, "pg"
    except Exception:
        import sqlite3
        from pathlib import Path
        db_path = Path(__file__).parent / "ai_news.db"
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn, "sqlite"

def query(sql: str, params=()) -> pd.DataFrame:
    conn, mode = get_conn()
    if mode == "pg":
        # psycopg2 uses %s placeholders
        sql = sql.replace("?", "%s")
        sql = sql.replace("date('now', '", "NOW() - INTERVAL '")
        sql = sql.replace("days')", "days'")
    return pd.read_sql_query(sql, conn, params=params if params else None)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 AI News")
    st.markdown("---")
    page = st.radio("Navigate", [
        "🏠 Overview",
        "🔥 Hot Topics",
        "📈 Trends Over Time",
        "🗂️ By Section",
        "🔍 Search",
        "📅 Archive",
    ])

    st.markdown("---")
    runs = query("SELECT scan_date FROM scan_runs ORDER BY scan_date DESC")
    if not runs.empty:
        st.markdown(f"**Total scans:** {len(runs)}")
        st.markdown(f"**Latest:** {runs['scan_date'].iloc[0]}")
        st.markdown(f"**Since:** {runs['scan_date'].iloc[-1]}")

# ── Page: Overview ────────────────────────────────────────────────────────────
if page == "🏠 Overview":
    st.title("🤖 AI News Dashboard")
    st.markdown(f"*{datetime.date.today().strftime('%A, %B %-d %Y')}*")
    st.markdown("---")

    total_articles = query("SELECT COUNT(*) AS n FROM articles").iloc[0]["n"]
    total_scans    = query("SELECT COUNT(*) AS n FROM scan_runs").iloc[0]["n"]
    total_sources  = query("SELECT COUNT(DISTINCT source_domain) AS n FROM articles").iloc[0]["n"]
    top_kw         = query("SELECT keyword FROM keywords GROUP BY keyword ORDER BY SUM(frequency) DESC LIMIT 1")
    top_word       = top_kw.iloc[0]["keyword"].upper() if not top_kw.empty else "—"

    c1, c2, c3, c4 = st.columns(4)
    for col, label, value, color in [
        (c1, "Total Articles", total_articles, "#6C63FF"),
        (c2, "Days Tracked",   total_scans,    "#00BFA5"),
        (c3, "Unique Sources", total_sources,  "#FF6B6B"),
        (c4, "Top Keyword",    top_word,       "#FFA940"),
    ]:
        col.markdown(f"""
        <div class="metric-card" style="border-color:{color}">
          <div style="font-size:13px;color:#888;margin-bottom:4px">{label}</div>
          <div style="font-size:28px;font-weight:700;color:{color}">{value}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("### Today's Articles")
    latest = query("""
        SELECT a.section, a.title, a.url, a.source_domain, a.snippet
        FROM articles a
        JOIN scan_runs r ON a.run_id = r.id
        WHERE r.scan_date = (SELECT MAX(scan_date) FROM scan_runs)
        ORDER BY a.section
    """)
    if latest.empty:
        st.info("No data yet. Run daily_ai_news.py to populate.")
    else:
        for section in latest["section"].unique():
            color = SECTION_COLORS.get(section, "#6C63FF")
            st.markdown(f"<h4 style='color:{color}'>{section}</h4>", unsafe_allow_html=True)
            for _, row in latest[latest["section"] == section].iterrows():
                st.markdown(f"""
                <div class="article-card" style="border-color:{color}">
                  <a href="{row.url}" target="_blank">{row.title}</a>
                  <div style="font-size:13px;color:#555;margin-top:6px">{row.snippet[:200]}…</div>
                  <div class="source" style="color:{color}">🔗 {row.source_domain}</div>
                </div>""", unsafe_allow_html=True)

# ── Page: Hot Topics ──────────────────────────────────────────────────────────
elif page == "🔥 Hot Topics":
    st.title("🔥 Hot Topics")

    period = st.selectbox("Period", ["Last 7 days", "Last 30 days", "All time"])
    days = {"Last 7 days": 7, "Last 30 days": 30, "All time": 9999}[period]

    _, mode = get_conn()
    if mode == "pg":
        date_filter = f"r.scan_date >= NOW() - INTERVAL '{days} days'"
    else:
        date_filter = f"r.scan_date >= date('now', '-{days} days')"

    kw_df = query(f"""
        SELECT k.keyword, SUM(k.frequency) AS total
        FROM keywords k
        JOIN articles a ON k.article_id = a.id
        JOIN scan_runs r ON a.run_id = r.id
        WHERE {date_filter}
        GROUP BY k.keyword
        ORDER BY total DESC
        LIMIT 40
    """)

    if kw_df.empty:
        st.info("Not enough data yet — run the daily scan for a few days.")
    else:
        col1, col2 = st.columns([2, 1])
        with col1:
            fig = px.bar(
                kw_df.head(20), x="total", y="keyword",
                orientation="h", color="total",
                color_continuous_scale="Purples",
                title=f"Top 20 Keywords — {period}",
                labels={"total": "Mentions", "keyword": ""},
            )
            fig.update_layout(yaxis=dict(autorange="reversed"),
                              coloraxis_showscale=False,
                              plot_bgcolor="#f8f9fc", paper_bgcolor="#f8f9fc")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("### Top 40 Keywords")
            max_v = kw_df["total"].max()
            for _, row in kw_df.iterrows():
                pct = int(row.total / max_v * 100)
                st.markdown(f"""
                <div style="margin-bottom:6px">
                  <span style="font-size:13px;font-weight:600">{row.keyword}</span>
                  <span style="float:right;font-size:12px;color:#888">{int(row.total)}</span>
                  <div style="background:#eee;border-radius:4px;height:6px;margin-top:3px">
                    <div style="background:#6C63FF;width:{pct}%;height:6px;border-radius:4px"></div>
                  </div>
                </div>""", unsafe_allow_html=True)

# ── Page: Trends Over Time ────────────────────────────────────────────────────
elif page == "📈 Trends Over Time":
    st.title("📈 Trends Over Time")

    daily = query("""
        SELECT r.scan_date, a.section, COUNT(*) AS n
        FROM articles a JOIN scan_runs r ON a.run_id = r.id
        GROUP BY r.scan_date, a.section
        ORDER BY r.scan_date
    """)

    if daily.empty:
        st.info("Not enough data yet.")
    else:
        fig = px.bar(daily, x="scan_date", y="n", color="section",
                     color_discrete_map=SECTION_COLORS,
                     title="Articles per Day by Section",
                     labels={"scan_date": "Date", "n": "Articles", "section": "Section"})
        fig.update_layout(plot_bgcolor="#f8f9fc", paper_bgcolor="#f8f9fc")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("### Keyword Trend Tracker")

    all_kws = query("SELECT keyword FROM keywords GROUP BY keyword ORDER BY SUM(frequency) DESC LIMIT 100")
    if not all_kws.empty:
        default = all_kws["keyword"].head(5).tolist()
        selected = st.multiselect("Track keywords", all_kws["keyword"].tolist(), default=default)

        if selected:
            placeholders = ",".join(["?"] * len(selected))
            trend = query(f"""
                SELECT r.scan_date, k.keyword, SUM(k.frequency) AS mentions
                FROM keywords k
                JOIN articles a ON k.article_id = a.id
                JOIN scan_runs r ON a.run_id = r.id
                WHERE k.keyword IN ({placeholders})
                GROUP BY r.scan_date, k.keyword
                ORDER BY r.scan_date
            """, tuple(selected))

            if not trend.empty:
                fig2 = px.line(trend, x="scan_date", y="mentions", color="keyword",
                               title="Keyword Mentions Over Time",
                               labels={"scan_date": "Date", "mentions": "Mentions", "keyword": "Keyword"},
                               markers=True)
                fig2.update_layout(plot_bgcolor="#f8f9fc", paper_bgcolor="#f8f9fc")
                st.plotly_chart(fig2, use_container_width=True)

# ── Page: By Section ──────────────────────────────────────────────────────────
elif page == "🗂️ By Section":
    st.title("🗂️ By Section")

    section_counts = query("""
        SELECT a.section, COUNT(*) AS total
        FROM articles a
        GROUP BY a.section
    """)

    if not section_counts.empty:
        colors = [SECTION_COLORS.get(s, "#6C63FF") for s in section_counts["section"]]
        fig = go.Figure(go.Pie(
            labels=section_counts["section"],
            values=section_counts["total"],
            hole=0.5,
            marker_colors=colors,
        ))
        fig.update_layout(title="Total Articles by Section (All Time)",
                          paper_bgcolor="#f8f9fc")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    section = st.selectbox("Browse section", list(SECTION_COLORS.keys()))
    color   = SECTION_COLORS[section]

    top_sources = query("""
        SELECT source_domain, COUNT(*) AS n FROM articles
        WHERE section = ? GROUP BY source_domain ORDER BY n DESC LIMIT 10
    """, (section,))

    recent_articles = query("""
        SELECT a.title, a.url, a.source_domain, a.snippet, r.scan_date
        FROM articles a JOIN scan_runs r ON a.run_id = r.id
        WHERE a.section = ?
        ORDER BY r.scan_date DESC LIMIT 20
    """, (section,))

    col1, col2 = st.columns([1, 2])
    with col1:
        st.markdown("#### Top Sources")
        if not top_sources.empty:
            fig = px.bar(top_sources, x="n", y="source_domain", orientation="h",
                         color_discrete_sequence=[color],
                         labels={"n": "Articles", "source_domain": ""})
            fig.update_layout(yaxis=dict(autorange="reversed"),
                              plot_bgcolor="#f8f9fc", paper_bgcolor="#f8f9fc")
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### Recent Articles")
        for _, row in recent_articles.iterrows():
            st.markdown(f"""
            <div class="article-card" style="border-color:{color}">
              <div style="font-size:11px;color:#aaa;margin-bottom:4px">{row.scan_date}</div>
              <a href="{row.url}" target="_blank">{row.title}</a>
              <div style="font-size:12px;color:#555;margin-top:4px">{str(row.snippet)[:180]}…</div>
              <div class="source" style="color:{color}">🔗 {row.source_domain}</div>
            </div>""", unsafe_allow_html=True)

# ── Page: Search ──────────────────────────────────────────────────────────────
elif page == "🔍 Search":
    st.title("🔍 Search Articles")

    q = st.text_input("Search keyword or phrase", placeholder="e.g. OpenAI, regulation, funding…")
    if q:
        results = query("""
            SELECT a.title, a.url, a.source_domain, a.snippet, a.section, r.scan_date
            FROM articles a JOIN scan_runs r ON a.run_id = r.id
            WHERE a.title LIKE ? OR a.snippet LIKE ?
            ORDER BY r.scan_date DESC
        """, (f"%{q}%", f"%{q}%"))

        st.markdown(f"**{len(results)} results** for *{q}*")
        for _, row in results.iterrows():
            color = SECTION_COLORS.get(row.section, "#6C63FF")
            st.markdown(f"""
            <div class="article-card" style="border-color:{color}">
              <div style="font-size:11px;color:#aaa">{row.scan_date} &nbsp;·&nbsp;
                <span style="color:{color}">{row.section}</span></div>
              <a href="{row.url}" target="_blank">{row.title}</a>
              <div style="font-size:12px;color:#555;margin-top:4px">{str(row.snippet)[:220]}…</div>
              <div class="source" style="color:{color}">🔗 {row.source_domain}</div>
            </div>""", unsafe_allow_html=True)

# ── Page: Archive ─────────────────────────────────────────────────────────────
elif page == "📅 Archive":
    st.title("📅 Archive")

    dates = query("SELECT scan_date FROM scan_runs ORDER BY scan_date DESC")
    if dates.empty:
        st.info("No archive yet.")
    else:
        selected_date = st.selectbox("Select date", dates["scan_date"].tolist())
        articles = query("""
            SELECT a.section, a.title, a.url, a.source_domain, a.snippet
            FROM articles a JOIN scan_runs r ON a.run_id = r.id
            WHERE r.scan_date = ?
            ORDER BY a.section
        """, (selected_date,))

        st.markdown(f"### {selected_date} — {len(articles)} articles")
        for section in articles["section"].unique():
            color = SECTION_COLORS.get(section, "#6C63FF")
            st.markdown(f"<h4 style='color:{color}'>{section}</h4>", unsafe_allow_html=True)
            for _, row in articles[articles["section"] == section].iterrows():
                st.markdown(f"""
                <div class="article-card" style="border-color:{color}">
                  <a href="{row.url}" target="_blank">{row.title}</a>
                  <div style="font-size:12px;color:#555;margin-top:4px">{str(row.snippet)[:200]}…</div>
                  <div class="source" style="color:{color}">🔗 {row.source_domain}</div>
                </div>""", unsafe_allow_html=True)
