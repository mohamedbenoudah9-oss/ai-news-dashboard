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
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

  /* Global styles */
  * { font-family: 'Inter', sans-serif !important; }

  /* Main background gradient */
  .stApp {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  }

  /* Sidebar styling */
  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    box-shadow: 4px 0 20px rgba(0,0,0,0.3);
  }
  [data-testid="stSidebar"] * { color: #e0e6ed !important; }
  [data-testid="stSidebar"] .stRadio > label {
    font-size: 15px !important;
    font-weight: 500 !important;
    padding: 8px 0 !important;
  }
  [data-testid="stSidebar"] hr {
    border-color: rgba(255,255,255,0.1) !important;
    margin: 20px 0 !important;
  }

  /* Main content container */
  .main .block-container {
    padding: 2rem 3rem;
    max-width: 1400px;
    background: rgba(255,255,255,0.95);
    border-radius: 20px;
    margin: 2rem auto;
    box-shadow: 0 10px 40px rgba(0,0,0,0.2);
  }

  /* Headers */
  h1 {
    color: #1a1a2e !important;
    font-weight: 700 !important;
    font-size: 2.5rem !important;
    margin-bottom: 0.5rem !important;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  h2, h3, h4 {
    color: #2d3748 !important;
    font-weight: 600 !important;
  }

  /* Metric cards */
  .metric-card {
    background: linear-gradient(135deg, #ffffff 0%, #f7fafc 100%);
    border-radius: 16px;
    padding: 24px 28px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    border-left: 5px solid;
    transition: transform 0.2s, box-shadow 0.2s;
    height: 100%;
  }
  .metric-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.15);
  }

  /* Article cards */
  .article-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 14px;
    border-left: 5px solid #6C63FF;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    transition: all 0.2s;
  }
  .article-card:hover {
    transform: translateX(4px);
    box-shadow: 0 4px 20px rgba(108,99,255,0.15);
  }
  .article-card a {
    color: #1a1a2e;
    font-weight: 600;
    text-decoration: none;
    font-size: 15px;
    line-height: 1.5;
  }
  .article-card a:hover {
    color: #6C63FF;
  }
  .article-card .source {
    font-size: 12px;
    color: #6C63FF;
    margin-top: 8px;
    font-weight: 500;
  }

  /* Section headers */
  .section-header {
    display: inline-block;
    padding: 8px 20px;
    border-radius: 25px;
    font-weight: 600;
    font-size: 18px;
    margin: 20px 0 16px 0;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
  }

  /* Buttons and inputs */
  .stButton > button {
    border-radius: 10px;
    font-weight: 600;
    padding: 0.5rem 2rem;
    transition: all 0.2s;
  }
  .stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
  }

  /* Expander styling */
  .streamlit-expanderHeader {
    background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
    border-radius: 10px;
    font-weight: 600;
    padding: 12px 16px;
  }

  /* Info/warning boxes */
  .stAlert {
    border-radius: 12px;
    border-left: 5px solid;
  }

  /* Plotly charts */
  .js-plotly-plot {
    border-radius: 12px;
    overflow: hidden;
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
        (c1, "Total Articles", total_articles, "#6C63FF", "📰"),
        (c2, "Days Tracked",   total_scans,    "#00BFA5", "📅"),
        (c3, "Unique Sources", total_sources,  "#FF6B6B", "🌐"),
        (c4, "Top Keyword",    top_word,       "#FFA940", "🔥"),
    ]

    for col, label, value, color, icon in metrics:
        col.markdown(f"""
        <div class="metric-card" style="border-color:{color}">
          <div style="font-size:24px;margin-bottom:8px">{icon}</div>
          <div style="font-size:12px;color:#718096;margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;font-weight:600">{label}</div>
          <div style="font-size:32px;font-weight:700;color:{color}">{value}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📰 Today's Articles")

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
                    color = SECTION_COLORS.get(section, "#6C63FF")
                    section_emoji = {"Top AI News": "🗞️", "Model & Research": "🧠",
                                    "Regulation & Policy": "⚖️", "Investment & Funding": "💰"}.get(section, "📌")

                    st.markdown(f"""
                    <div class="section-header" style="background:{color};color:white;">
                      {section_emoji} {section}
                    </div>""", unsafe_allow_html=True)

                    for _, row in latest[latest["section"] == section].iterrows():
                        snippet = str(row.snippet)[:200] if pd.notna(row.snippet) else ""
                        st.markdown(f"""
                        <div class="article-card" style="border-color:{color}">
                          <a href="{row.url}" target="_blank">{row.title}</a>
                          <div style="font-size:13px;color:#718096;margin-top:8px;line-height:1.6">{snippet}…</div>
                          <div class="source" style="color:{color}">🔗 {row.source_domain}</div>
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
                orientation="h", color="total",
                color_continuous_scale=["#E0E7FF", "#6C63FF"],
                title="<b>Top 20 Keywords</b>",
                labels={"total": "Mentions", "keyword": ""},
            )
            fig.update_layout(
                yaxis=dict(autorange="reversed"),
                coloraxis_showscale=False,
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", size=12),
                title_font=dict(size=18, color="#1a1a2e"),
                margin=dict(l=20, r=20, t=60, b=20),
                hoverlabel=dict(bgcolor="white", font_size=13),
            )
            fig.update_traces(marker_line_width=0, hovertemplate="<b>%{y}</b><br>%{x} mentions<extra></extra>")
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.markdown("### 📊 Top 40 Keywords")
            max_v = kw_df["total"].max()
            for _, row in kw_df.iterrows():
                pct = int(row.total / max_v * 100)
                st.markdown(f"""
                <div style="margin-bottom:10px;padding:8px;background:white;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.05)">
                  <span style="font-size:13px;font-weight:600;color:#2d3748">{row.keyword}</span>
                  <span style="float:right;font-size:12px;color:#718096;font-weight:600">{int(row.total)}</span>
                  <div style="background:#E2E8F0;border-radius:6px;height:8px;margin-top:6px">
                    <div style="background:linear-gradient(90deg, #6C63FF 0%, #9F7AEA 100%);width:{pct}%;height:8px;border-radius:6px;transition:width 0.3s"></div>
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

            fig1 = px.area(
                daily_counts, x="scan_date", y="count",
                title="<b>Articles Per Day</b>",
                labels={"scan_date": "Date", "count": "Articles"},
            )
            fig1.update_traces(
                line_color="#6C63FF",
                fillcolor="rgba(108, 99, 255, 0.2)",
                hovertemplate="<b>%{x|%b %d}</b><br>%{y} articles<extra></extra>"
            )
            fig1.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", size=12),
                title_font=dict(size=18, color="#1a1a2e"),
                margin=dict(l=20, r=20, t=60, b=20),
                hovermode="x unified",
            )
            st.plotly_chart(fig1, use_container_width=True)

            # Articles by section over time
            section_daily = df.groupby(["scan_date", "section"]).size().reset_index(name="count")
            section_daily["scan_date"] = pd.to_datetime(section_daily["scan_date"])

            fig2 = px.line(
                section_daily, x="scan_date", y="count", color="section",
                title="<b>Articles by Section Over Time</b>",
                labels={"scan_date": "Date", "count": "Articles"},
                markers=True,
                color_discrete_map=SECTION_COLORS,
            )
            fig2.update_traces(marker=dict(size=8), line=dict(width=3))
            fig2.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font=dict(family="Inter, sans-serif", size=12),
                title_font=dict(size=18, color="#1a1a2e"),
                margin=dict(l=20, r=20, t=60, b=20),
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig2, use_container_width=True)

            # Top keywords trend
            st.markdown("### 🔥 Keyword Trends")
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
                    title="<b>Top 5 Keywords Over Time</b>",
                    labels={"scan_date": "Date", "frequency": "Mentions"},
                    markers=True,
                )
                fig3.update_traces(marker=dict(size=8), line=dict(width=3))
                fig3.update_layout(
                    plot_bgcolor="rgba(0,0,0,0)",
                    paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(family="Inter, sans-serif", size=12),
                    title_font=dict(size=18, color="#1a1a2e"),
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

        colors = [SECTION_COLORS.get(s, "#6C63FF") for s in section_counts["section"]]
        fig = go.Figure(go.Pie(
            labels=section_counts["section"],
            values=section_counts["total"],
            hole=0.6,
            marker=dict(colors=colors, line=dict(color='white', width=3)),
            textinfo='label+percent',
            textfont=dict(size=14, family="Inter, sans-serif"),
            hovertemplate="<b>%{label}</b><br>%{value} articles<br>%{percent}<extra></extra>"
        ))
        fig.update_layout(
            title="<b>Total Articles by Section (All Time)</b>",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Inter, sans-serif", size=12),
            title_font=dict(size=18, color="#1a1a2e"),
            margin=dict(l=20, r=20, t=60, b=20),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        section = st.selectbox("Browse section", list(SECTION_COLORS.keys()))
        color = SECTION_COLORS[section]

        section_articles = articles[articles["section"] == section].head(20)

        st.markdown(f"#### 📚 Recent Articles in {section}")
        for _, row in section_articles.iterrows():
            snippet = str(row.snippet)[:180] if pd.notna(row.snippet) else ""
            st.markdown(f"""
            <div class="article-card" style="border-color:{color}">
              <a href="{row.url}" target="_blank">{row.title}</a>
              <div style="font-size:12px;color:#555;margin-top:4px">{snippet}…</div>
              <div class="source" style="color:{color}">🔗 {row.source_domain}</div>
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
