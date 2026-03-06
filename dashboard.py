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
                    st.markdown(f"<h4 style='color:{color}'>{section}</h4>", unsafe_allow_html=True)
                    for _, row in latest[latest["section"] == section].iterrows():
                        snippet = str(row.snippet)[:200] if pd.notna(row.snippet) else ""
                        st.markdown(f"""
                        <div class="article-card" style="border-color:{color}">
                          <a href="{row.url}" target="_blank">{row.title}</a>
                          <div style="font-size:13px;color:#555;margin-top:6px">{snippet}…</div>
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
                color_continuous_scale="Purples",
                title="Top 20 Keywords",
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
    st.info("Trends view requires SQL joins — coming soon with enhanced API access.")

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
            hole=0.5,
            marker_colors=colors,
        ))
        fig.update_layout(title="Total Articles by Section (All Time)",
                          paper_bgcolor="#f8f9fc")
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        section = st.selectbox("Browse section", list(SECTION_COLORS.keys()))
        color = SECTION_COLORS[section]
        
        section_articles = articles[articles["section"] == section].head(20)
        
        st.markdown("#### Recent Articles")
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
    st.info("Archive view requires date filtering — coming soon with enhanced API access.")
