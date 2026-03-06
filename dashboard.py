"""AI News Dashboard — run with: streamlit run dashboard.py"""

import datetime
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import requests

st.set_page_config(
    page_title="AI News Dashboard",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  /* Import modern font */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  /* Global styles */
  * { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important; }

  /* Main background - clean white */
  .stApp {
    background: #fafafa;
  }

  /* Sidebar styling - minimal dark */
  [data-testid="stSidebar"] {
    background: #1a1a1a;
    border-right: 1px solid #e5e5e5;
  }
  [data-testid="stSidebar"] * { color: #e0e0e0 !important; }
  [data-testid="stSidebar"] .stRadio > label {
    font-size: 14px !important;
    font-weight: 500 !important;
    padding: 10px 0 !important;
    transition: color 0.2s;
  }
  [data-testid="stSidebar"] .stRadio > label:hover {
    color: #ffffff !important;
  }
  [data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.1) !important;
    margin: 24px 0 !important;
  }

  /* Main content container */
  .main .block-container {
    padding: 3rem 4rem;
    max-width: 1400px;
    background: transparent;
    margin: 0 auto;
  }

  /* Headers - clean and minimal */
  h1 {
    color: #1a1a1a !important;
    font-weight: 700 !important;
    font-size: 2.5rem !important;
    margin-bottom: 0.5rem !important;
    letter-spacing: -0.02em !important;
  }
  h2, h3, h4 {
    color: #2a2a2a !important;
    font-weight: 600 !important;
    letter-spacing: -0.01em !important;
  }

  /* Metric cards - clean card style */
  .metric-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    border: 1px solid #f0f0f0;
    transition: all 0.2s ease;
    height: 100%;
  }
  .metric-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    transform: translateY(-2px);
  }

  /* Article cards - gallery style */
  .article-card {
    background: #ffffff;
    border-radius: 10px;
    padding: 20px;
    margin-bottom: 16px;
    border: 1px solid #f0f0f0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: all 0.2s ease;
  }
  .article-card:hover {
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    transform: translateY(-2px);
    border-color: #e0e0e0;
  }
  .article-card a {
    color: #1a1a1a;
    font-weight: 600;
    text-decoration: none;
    font-size: 15px;
    line-height: 1.5;
  }
  .article-card a:hover {
    color: #4a4a4a;
  }
  .article-card .source {
    font-size: 12px;
    color: #888;
    margin-top: 8px;
    font-weight: 500;
  }

  /* Section headers - minimal badge */
  .section-header {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 14px;
    margin: 20px 0 16px 0;
    background: #f5f5f5;
    color: #2a2a2a;
  }

  /* Buttons */
  .stButton > button {
    border-radius: 8px;
    font-weight: 500;
    padding: 0.5rem 1.5rem;
    transition: all 0.2s;
    border: 1px solid #e0e0e0;
  }
  .stButton > button:hover {
    border-color: #1a1a1a;
    background: #1a1a1a;
    color: white;
  }

  /* Expander */
  .streamlit-expanderHeader {
    background: #ffffff;
    border: 1px solid #f0f0f0;
    border-radius: 8px;
    font-weight: 600;
    padding: 12px 16px;
  }

  /* Info boxes */
  .stAlert {
    border-radius: 8px;
    border: 1px solid #e0e0e0;
  }

  /* Input fields */
  .stTextInput > div > div > input {
    border-radius: 8px;
    border: 1px solid #e0e0e0;
  }

  /* Select boxes */
  .stSelectbox > div > div {
    border-radius: 8px;
  }

  /* Remove default streamlit padding */
  .main > div {
    padding-top: 2rem;
  }
</style>
""", unsafe_allow_html=True)

SECTION_COLORS = {
    "Top AI News":          "#6C63FF",
    "Model & Research":     "#00BFA5",
    "Regulation & Policy":  "#FF6B6B",
    "Investment & Funding": "#FFA940",
}

# ── Supabase REST API connection ──────────────────────────────────────────────
@st.cache_data(ttl=60)
def query_supabase(table: str, select: str = "*", filters: dict = None, order: str = None, limit: int = None):
    try:
        cfg = st.secrets["supabase"]
        url = f"{cfg['url']}/rest/v1/{table}"
        headers = {
            "apikey": cfg["anon_key"],
            "Authorization": f"Bearer {cfg['anon_key']}",
        }
        params = {"select": select}
        if filters:
            for k, v in filters.items():
                params[k] = v
        if order:
            params["order"] = order
        if limit:
            params["limit"] = limit
        
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        return pd.DataFrame(resp.json())
    except Exception as e:
        st.error(f"Supabase API error: {e}")
        return pd.DataFrame()

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
    runs = query_supabase("scan_runs", select="scan_date", order="scan_date.desc")
    if not runs.empty:
        st.markdown(f"**Total scans:** {len(runs)}")
        st.markdown(f"**Latest:** {runs['scan_date'].iloc[0]}")
        st.markdown(f"**Since:** {runs['scan_date'].iloc[-1]}")

# ── Page: Overview ────────────────────────────────────────────────────────────
if page == "🏠 Overview":
    st.title("🤖 AI News Dashboard")
    st.markdown(f"*{datetime.date.today().strftime('%A, %B %-d %Y')}*")
    st.markdown("---")

    articles = query_supabase("articles", select="id,source_domain")
    keywords = query_supabase("keywords", select="keyword,frequency")
    
    total_articles = len(articles)
    total_scans = len(runs)
    total_sources = articles["source_domain"].nunique() if not articles.empty else 0
    
    if not keywords.empty:
        top_word = keywords.groupby("keyword")["frequency"].sum().idxmax().upper()
    else:
        top_word = "—"

    c1, c2, c3, c4 = st.columns(4)
    metrics = [
        (c1, "Total Articles", total_articles, "#1a1a1a"),
        (c2, "Days Tracked",   total_scans,    "#1a1a1a"),
        (c3, "Unique Sources", total_sources,  "#1a1a1a"),
        (c4, "Top Keyword",    top_word,       "#1a1a1a"),
    ]

    for col, label, value, color in metrics:
        col.markdown(f"""
        <div class="metric-card">
          <div style="font-size:11px;color:#888;margin-bottom:8px;text-transform:uppercase;letter-spacing:1px;font-weight:600">{label}</div>
          <div style="font-size:36px;font-weight:700;color:{color};line-height:1">{value}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### Today's Articles")

    # Get latest scan
    if not runs.empty:
        latest_date = runs['scan_date'].iloc[0]
        latest_run = query_supabase("scan_runs", select="id", filters={"scan_date": f"eq.{latest_date}"})

        if not latest_run.empty:
            run_id = latest_run['id'].iloc[0]
            latest = query_supabase("articles",
                                   select="section,title,url,source_domain,snippet",
                                   filters={"run_id": f"eq.{run_id}"},
                                   order="section")

            if latest.empty:
                st.info("No data yet. Run daily_ai_news.py to populate.")
            else:
                for section in latest["section"].unique():
                    st.markdown(f"""
                    <div class="section-header">
                      {section}
                    </div>""", unsafe_allow_html=True)

                    for _, row in latest[latest["section"] == section].iterrows():
                        snippet = str(row.snippet)[:200] if pd.notna(row.snippet) else ""
                        st.markdown(f"""
                        <div class="article-card">
                          <a href="{row.url}" target="_blank">{row.title}</a>
                          <div style="font-size:13px;color:#666;margin-top:10px;line-height:1.6">{snippet}…</div>
                          <div class="source">{row.source_domain}</div>
                        </div>""", unsafe_allow_html=True)

# ── Page: Hot Topics ──────────────────────────────────────────────────────────
elif page == "🔥 Hot Topics":
    st.title("🔥 Hot Topics")
    
    keywords = query_supabase("keywords", select="keyword,frequency", limit=1000)
    
    if keywords.empty:
        st.info("Not enough data yet — run the daily scan for a few days.")
    else:
        kw_df = keywords.groupby("keyword")["frequency"].sum().reset_index()
        kw_df.columns = ["keyword", "total"]
        kw_df = kw_df.sort_values("total", ascending=False).head(40)
        
        col1, col2 = st.columns([2, 1])
        with col1:
            fig = px.bar(
                kw_df.head(20), x="total", y="keyword",
                orientation="h",
                title="Top 20 Keywords",
                labels={"total": "Mentions", "keyword": ""},
            )
            fig.update_traces(marker_color='#1a1a1a', marker_line_width=0)
            fig.update_layout(
                yaxis=dict(autorange="reversed"),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", size=12, color="#2a2a2a"),
                title_font=dict(size=20, color="#1a1a1a", family="Inter"),
                margin=dict(l=20, r=20, t=60, b=20),
                hoverlabel=dict(bgcolor="white", font_size=13, bordercolor="#e0e0e0"),
                hovermode="closest",
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("### Top 40 Keywords")
            max_v = kw_df["total"].max()
            for _, row in kw_df.iterrows():
                pct = int(row.total / max_v * 100)
                st.markdown(f"""
                <div style="margin-bottom:8px;padding:10px;background:white;border-radius:8px;border:1px solid #f0f0f0">
                  <span style="font-size:13px;font-weight:600;color:#1a1a1a">{row.keyword}</span>
                  <span style="float:right;font-size:12px;color:#888;font-weight:500">{int(row.total)}</span>
                  <div style="background:#f5f5f5;border-radius:4px;height:6px;margin-top:8px">
                    <div style="background:#1a1a1a;width:{pct}%;height:6px;border-radius:4px"></div>
                  </div>
                </div>""", unsafe_allow_html=True)

# ── Page: Trends Over Time ────────────────────────────────────────────────────
elif page == "📈 Trends Over Time":
    st.title("📈 Trends Over Time")

    runs = query_supabase("scan_runs", select="id,scan_date", order="scan_date.asc")

    if runs.empty or len(runs) < 2:
        st.info("Not enough data yet — need at least 2 days of scans to show trends.")
    else:
        # Get all articles with run info
        articles = query_supabase("articles", select="run_id,section", limit=5000)

        if not articles.empty:
            # Merge to get dates
            df = articles.merge(runs, left_on="run_id", right_on="id", how="left")

            # Articles per day
            daily_counts = df.groupby("scan_date").size().reset_index(name="count")
            daily_counts["scan_date"] = pd.to_datetime(daily_counts["scan_date"])

            fig1 = px.line(
                daily_counts, x="scan_date", y="count",
                title="Articles Per Day",
                labels={"scan_date": "Date", "count": "Articles"},
                markers=True,
            )
            fig1.update_traces(
                line_color="#1a1a1a",
                marker=dict(size=6, color="#1a1a1a"),
            )
            fig1.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", size=12, color="#2a2a2a"),
                title_font=dict(size=20, color="#1a1a1a"),
                margin=dict(l=20, r=20, t=60, b=20),
                hovermode="x unified",
            )
            st.plotly_chart(fig1, use_container_width=True)

            # Articles by section over time
            section_daily = df.groupby(["scan_date", "section"]).size().reset_index(name="count")
            section_daily["scan_date"] = pd.to_datetime(section_daily["scan_date"])

            # Use grayscale colors for minimal look
            gray_colors = {
                "Top AI News": "#1a1a1a",
                "Model & Research": "#4a4a4a",
                "Regulation & Policy": "#6a6a6a",
                "Investment & Funding": "#8a8a8a",
            }

            fig2 = px.line(
                section_daily, x="scan_date", y="count", color="section",
                title="Articles by Section Over Time",
                labels={"scan_date": "Date", "count": "Articles"},
                markers=True,
                color_discrete_map=gray_colors,
            )
            fig2.update_traces(marker=dict(size=6), line=dict(width=2))
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", size=12, color="#2a2a2a"),
                title_font=dict(size=20, color="#1a1a1a"),
                margin=dict(l=20, r=20, t=60, b=20),
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig2, use_container_width=True)

            # Top keywords trend
            st.markdown("### Keyword Trends")
            keywords = query_supabase("keywords", select="article_id,keyword,frequency", limit=5000)

            if not keywords.empty:
                # Join keywords with articles to get dates
                kw_df = keywords.merge(articles[["run_id"]], left_on="article_id", right_index=True, how="left")
                kw_df = kw_df.merge(runs[["id", "scan_date"]], left_on="run_id", right_on="id", how="left")

                # Get top 5 keywords overall
                top_kw = keywords.groupby("keyword")["frequency"].sum().nlargest(5).index.tolist()

                # Filter and aggregate
                kw_trend = kw_df[kw_df["keyword"].isin(top_kw)].groupby(["scan_date", "keyword"])["frequency"].sum().reset_index()
                kw_trend["scan_date"] = pd.to_datetime(kw_trend["scan_date"])

                fig3 = px.line(
                    kw_trend, x="scan_date", y="frequency", color="keyword",
                    title="Top 5 Keywords Over Time",
                    labels={"scan_date": "Date", "frequency": "Mentions"},
                    markers=True,
                )
                fig3.update_traces(marker=dict(size=6), line=dict(width=2))
                fig3.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, sans-serif", size=12, color="#2a2a2a"),
                    title_font=dict(size=20, color="#1a1a1a"),
                    margin=dict(l=20, r=20, t=60, b=20),
                    hovermode="x unified",
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig3, use_container_width=True)

# ── Page: By Section ──────────────────────────────────────────────────────────
elif page == "🗂️ By Section":
    st.title("🗂️ By Section")
    
    articles = query_supabase("articles", select="section,title,url,source_domain,snippet", limit=1000)
    
    if not articles.empty:
        section_counts = articles["section"].value_counts().reset_index()
        section_counts.columns = ["section", "total"]

        # Use grayscale for minimal look
        gray_shades = ["#1a1a1a", "#4a4a4a", "#6a6a6a", "#8a8a8a"]
        fig = go.Figure(go.Pie(
            labels=section_counts["section"],
            values=section_counts["total"],
            hole=0.5,
            marker=dict(colors=gray_shades, line=dict(color='white', width=2)),
            textinfo='label+percent',
            textfont=dict(size=13, family="Inter, sans-serif"),
        ))
        fig.update_layout(
            title="Total Articles by Section (All Time)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", size=12, color="#2a2a2a"),
            title_font=dict(size=20, color="#1a1a1a"),
            margin=dict(l=20, r=20, t=60, b=20),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        section = st.selectbox("Browse section", list(SECTION_COLORS.keys()))

        section_articles = articles[articles["section"] == section].head(20)

        st.markdown(f"#### Recent Articles in {section}")
        for _, row in section_articles.iterrows():
            snippet = str(row.snippet)[:180] if pd.notna(row.snippet) else ""
            st.markdown(f"""
            <div class="article-card">
              <a href="{row.url}" target="_blank">{row.title}</a>
              <div style="font-size:13px;color:#666;margin-top:10px;line-height:1.6">{snippet}…</div>
              <div class="source">{row.source_domain}</div>
            </div>""", unsafe_allow_html=True)

# ── Page: Search ──────────────────────────────────────────────────────────────
elif page == "🔍 Search":
    st.title("🔍 Search Articles")
    
    q = st.text_input("Search keyword or phrase", placeholder="e.g. OpenAI, regulation, funding…")
    if q:
        articles = query_supabase("articles", select="section,title,url,source_domain,snippet", limit=1000)
        
        if not articles.empty:
            results = articles[
                articles["title"].str.contains(q, case=False, na=False) |
                articles["snippet"].str.contains(q, case=False, na=False)
            ]
            
            st.markdown(f"**{len(results)} results** for *{q}*")
            for _, row in results.iterrows():
                color = SECTION_COLORS.get(row.section, "#6C63FF")
                snippet = str(row.snippet)[:220] if pd.notna(row.snippet) else ""
                st.markdown(f"""
                <div class="article-card" style="border-color:{color}">
                  <div style="font-size:11px;color:#aaa">
                    <span style="color:{color}">{row.section}</span></div>
                  <a href="{row.url}" target="_blank">{row.title}</a>
                  <div style="font-size:12px;color:#555;margin-top:4px">{snippet}…</div>
                  <div class="source" style="color:{color}">🔗 {row.source_domain}</div>
                </div>""", unsafe_allow_html=True)

# ── Page: Archive ─────────────────────────────────────────────────────────────
elif page == "📅 Archive":
    st.title("📅 Archive")

    runs = query_supabase("scan_runs", select="id,scan_date", order="scan_date.desc")

    if runs.empty:
        st.info("No archived scans yet.")
    else:
        st.markdown(f"**{len(runs)} scans** in archive")

        selected_date = st.selectbox("Select date", runs["scan_date"].tolist())

        if selected_date:
            run = runs[runs["scan_date"] == selected_date].iloc[0]
            run_id = run["id"]

            articles = query_supabase(
                "articles",
                select="section,title,url,source_domain,snippet",
                filters={"run_id": f"eq.{run_id}"},
                order="section"
            )

            if articles.empty:
                st.warning(f"No articles found for {selected_date}")
            else:
                st.markdown(f"### {selected_date} — {len(articles)} articles")

                for section in articles["section"].unique():
                    color = SECTION_COLORS.get(section, "#6C63FF")
                    section_articles = articles[articles["section"] == section]

                    with st.expander(f"{section} ({len(section_articles)} articles)", expanded=True):
                        for _, row in section_articles.iterrows():
                            snippet = str(row.snippet)[:200] if pd.notna(row.snippet) else ""
                            st.markdown(f"""
                            <div class="article-card" style="border-color:{color}">
                              <a href="{row.url}" target="_blank">{row.title}</a>
                              <div style="font-size:12px;color:#555;margin-top:4px">{snippet}…</div>
                              <div class="source" style="color:{color}">🔗 {row.source_domain}</div>
                            </div>""", unsafe_allow_html=True)
