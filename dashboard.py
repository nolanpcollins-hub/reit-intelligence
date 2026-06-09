"""
dashboard.py
US Multifamily REIT & Rent Control Intelligence Engine
Executive-grade platform for Fund Supervisor, PM, and CIO.
Tracks: AVB · EQR · ESS · MAA · CPT · UDR · INVH · AMH · CSR
Run: streamlit run dashboard.py
"""

import os
import sqlite3
import urllib.parse

import feedparser
import pandas as pd
import requests
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

# ─── Constants ────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "market_intelligence.db")

ALL_TICKERS = ["AVB", "EQR", "ESS", "MAA", "CPT", "UDR", "INVH", "AMH", "CSR"]

TICKER_NAMES = {
    "AVB":  "AvalonBay Communities",
    "EQR":  "Equity Residential",
    "ESS":  "Essex Property Trust",
    "MAA":  "Mid-America Apartment",
    "CPT":  "Camden Property Trust",
    "UDR":  "UDR Inc.",
    "INVH": "Invitation Homes",
    "AMH":  "American Homes 4 Rent",
    "CSR":  "Centerspace",
}

RISK_COLORS = {"Critical": "#FF4B4B", "Moderate": "#FFA500", "Low/Stable": "#21C55D"}

SOL_COLORS = {
    "Active Enforced":    "#FF4B4B",
    "Pending Vote":       "#FFA500",
    "Developing Ballot":  "#C9A84C",
    "Defeated/Preempted": "#21C55D",
}

# Baseline sentiment for ALL 50 states (used for choropleth when no DB row exists).
# Based on known preemption laws, active rent control, and legislative trajectory.
STATE_BASELINE = {
    "AK": 0.60, "AL": 0.65, "AR": 0.68, "AZ": -0.38, "CA": -0.82,
    "CO": -0.42, "CT": -0.18, "DE": 0.28, "FL": 0.80, "GA": -0.22,
    "HI": -0.30, "IA": 0.62, "ID": 0.68, "IL": -0.35, "IN": 0.65,
    "KS": 0.68, "KY": 0.62, "LA": 0.65, "MA": -0.55, "MD": -0.55,
    "ME": 0.18, "MI": 0.55, "MN": -0.58, "MO": 0.62, "MS": 0.68,
    "MT": 0.62, "NC": 0.68, "ND": 0.55, "NE": 0.58, "NH": 0.30,
    "NJ": -0.60, "NM": -0.22, "NV": 0.62, "NY": -0.62, "OH": 0.58,
    "OK": 0.68, "OR": -0.58, "PA": -0.15, "RI": -0.12, "SC": 0.65,
    "SD": 0.58, "TN": 0.68, "TX": 0.72, "UT": 0.48, "VA": 0.15,
    "VT": -0.18, "WA": -0.52, "WI": 0.58, "WV": 0.62, "WY": 0.72,
}

ALL_STATES = sorted(STATE_BASELINE.keys())

# Structured ballot supplement data (signature counts, litigation, candidate info)
BALLOT_SUPPLEMENTS = {
    "Cambridge": {
        "type": "ballot",
        "signatures_collected": 8400,
        "signatures_required": 5000,
        "deadline": "Filed — November 2026 ballot",
        "polling": "58% support (Suffolk University, March 2026)",
        "litigation": "Greater Boston Real Estate Board — Home Rule Amendment challenge filed",
        "litigation_risk": "High",
        "next_milestone": "Cambridge Election Commission title review, August 2026",
    },
    "Phoenix": {
        "type": "ballot",
        "signatures_collected": 142000,
        "signatures_required": 237645,
        "deadline": "July 3, 2026",
        "polling": "54% support (OH Predictive Insights, April 2026)",
        "litigation": "Arizona Multihousing Association — title & summary challenge, Maricopa Superior Court",
        "litigation_risk": "Medium",
        "next_milestone": "Signature drive close-out: July 3, 2026",
    },
    "Atlanta": {
        "type": "candidate",
        "candidate": "Councilwoman Keisha Dorsey",
        "office": "Atlanta Mayor",
        "election_date": "November 3, 2026",
        "polling": "38% (leading) — Atlanta Journal-Constitution, May 2026",
        "stance": "Pro-stabilization study commission; not a direct rent control advocate",
        "endorsements": "SEIU Local 32BJ, Atlanta Progressive Caucus, DSA ATL",
        "opposition": "Atlanta Apartment Association, NMHC, Georgia Chamber of Commerce",
        "tickers": "MAA, CPT, INVH",
        "risk_if_elected": "Study commission precursor to state preemption repeal attempt in 2027",
    },
}

# ─── Page config ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="REIT Regulatory Intelligence",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── CSS ─────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ─── Import ─── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ─── Global ─── */
html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', system-ui, sans-serif !important;
    font-size: 15px !important;
}
.stApp { background-color: #06101E; color: #E2EBF6; }
.block-container { padding: 1.6rem 2.2rem 5rem 2.2rem !important; max-width: 100% !important; }
p { font-size: 0.95rem !important; line-height: 1.72 !important; color: #D8E8F6 !important; }

/* ─── Sidebar ─── */
[data-testid="stSidebar"] {
    background-color: #050D18 !important;
    border-right: 1px solid #182D48;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.2rem; }
[data-testid="stSidebarContent"] { padding: 0 1.1rem; }
[data-testid="stSidebar"] label {
    color: #7A9BBE !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.07em !important;
}

/* ─── Metric cards ─── */
[data-testid="metric-container"] {
    background: linear-gradient(140deg, #0B1A2D 0%, #0F2035 100%);
    border: 1px solid #1D3450;
    border-radius: 12px;
    padding: 20px 24px !important;
}
[data-testid="stMetricValue"] {
    color: #C9A84C !important;
    font-size: 2.0rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
}
[data-testid="stMetricLabel"] {
    color: #6E90B2 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.09em !important;
    font-weight: 700 !important;
}
[data-testid="stMetricDelta"] svg { display: none; }
[data-testid="stMetricDelta"] { font-size: 0.78rem !important; color: #6E90B2 !important; }

/* ─── Tabs ─── */
.stTabs [data-baseweb="tab-list"] {
    background-color: #050D18;
    gap: 4px;
    border-bottom: 2px solid #182D48;
    padding-bottom: 0;
}
.stTabs [data-baseweb="tab"] {
    background-color: #0B1A2D;
    color: #6E90B2;
    border-radius: 8px 8px 0 0;
    padding: 11px 24px;
    font-size: 0.90rem;
    font-weight: 600;
    border: 1px solid #182D48;
    border-bottom: none;
    transition: all 0.18s;
    letter-spacing: 0.01em;
}
.stTabs [data-baseweb="tab"]:hover { color: #D0DDF0 !important; background-color: #0F2035 !important; }
.stTabs [aria-selected="true"] {
    background-color: #142438 !important;
    color: #C9A84C !important;
    border-color: #2E5070 !important;
    border-bottom: 2px solid #C9A84C !important;
}
.stTabs [data-baseweb="tab-panel"] { padding-top: 1.6rem !important; }

/* ─── Buttons ─── */
.stButton > button {
    background: #0B1A2D !important;
    color: #C9A84C !important;
    border: 1px solid #3A5A20 !important;
    border-color: rgba(201,168,76,0.5) !important;
    border-radius: 6px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    padding: 6px 14px !important;
    transition: all 0.15s !important;
    letter-spacing: 0.02em;
}
.stButton > button:hover {
    background: #C9A84C !important;
    color: #06101E !important;
    border-color: #C9A84C !important;
}

/* ─── Multiselect / Select ─── */
[data-baseweb="select"] { background-color: #0B1A2D !important; }
[data-baseweb="select"] div { color: #D8E8F6 !important; font-size: 0.88rem !important; }
[data-baseweb="tag"] { background-color: #1D3450 !important; color: #C9A84C !important; font-weight: 600 !important; }
[data-baseweb="menu"] { background-color: #0B1A2D !important; border: 1px solid #1D3450 !important; }
[data-baseweb="menu"] li { color: #D8E8F6 !important; font-size: 0.88rem !important; }
[data-baseweb="menu"] li:hover { background-color: #142438 !important; }

/* ─── Text inputs ─── */
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea {
    background-color: #0B1A2D !important;
    color: #E2EBF6 !important;
    border: 1px solid #1D3450 !important;
    border-radius: 8px !important;
    font-size: 0.92rem !important;
}
[data-testid="stTextInput"] input:focus, [data-testid="stTextArea"] textarea:focus {
    border-color: #C9A84C !important;
    box-shadow: 0 0 0 2px rgba(201,168,76,0.15) !important;
}
[data-testid="stTextInput"] label, [data-testid="stTextArea"] label {
    color: #6E90B2 !important; font-size: 0.78rem !important;
    font-weight: 700 !important; text-transform: uppercase !important; letter-spacing: 0.07em !important;
}

/* ─── Dataframe ─── */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
[data-testid="stDataFrame"] th {
    background: #0B1A2D !important;
    color: #C9A84C !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.06em !important;
}
[data-testid="stDataFrame"] td { color: #D8E8F6 !important; font-size: 0.88rem !important; }

/* ─── Expanders ─── */
details {
    background-color: #0B1A2D !important;
    border: 1px solid #1D3450 !important;
    border-radius: 10px !important;
    margin-bottom: 4px;
}
summary {
    color: #C8DAEA !important;
    font-weight: 600 !important;
    padding: 12px 16px !important;
    font-size: 0.91rem !important;
    letter-spacing: 0.01em;
}
summary:hover { color: #E8F0FA !important; }

/* ─── Progress ─── */
.stProgress > div > div { background: linear-gradient(90deg, #C9A84C, #E8C96A) !important; }
.stProgress > div { background-color: #1D3450 !important; border-radius: 99px !important; height: 8px !important; }

/* ─── Dividers ─── */
hr { border-color: #182D48 !important; margin: 1.4rem 0 !important; }

/* ─── Spinners / info ─── */
[data-testid="stSpinner"] p { color: #C9A84C !important; }

/* ─── Chat (inline inside column) ─── */
[data-testid="stChatMessage"] {
    background-color: #0B1A2D !important;
    border: 1px solid #1D3450 !important;
    border-radius: 10px !important;
    padding: 12px 16px !important;
    margin-bottom: 8px !important;
}
[data-testid="stChatMessage"] p { font-size: 0.92rem !important; line-height: 1.68 !important; color: #D8E8F6 !important; }
[data-testid="stChatInput"] {
    background: #06101E !important;
    border-top: 2px solid #1D3450 !important;
    padding: 10px 16px !important;
}
[data-testid="stChatInput"] textarea {
    background-color: #0B1A2D !important;
    color: #E2EBF6 !important;
    border: 1.5px solid #1D3450 !important;
    border-radius: 12px !important;
    font-size: 0.93rem !important;
    padding: 10px 16px !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: #00FF88 !important;
    box-shadow: 0 0 0 3px rgba(0,255,136,0.1) !important;
}
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #00DD77, #00AA55) !important;
    border-radius: 10px !important;
    border: none !important;
}

/* ─── Page header ─── */
.page-header { border-bottom: 2px solid #C9A84C; padding-bottom: 14px; margin-bottom: 24px; }
.page-header h1 {
    color: #EBF1FA;
    font-size: 1.6rem;
    font-weight: 800;
    margin: 0 0 5px 0;
    letter-spacing: -0.02em;
}
.page-header p { color: #6E90B2 !important; font-size: 0.85rem !important; margin: 0; }

/* ─── Section titles ─── */
.section-title {
    color: #C9A84C;
    font-weight: 700;
    font-size: 0.82rem;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    border-bottom: 1px solid #182D48;
    padding-bottom: 7px;
    margin-bottom: 16px;
}

/* ─── Cards ─── */
.intel-card {
    background: linear-gradient(160deg, #0B1A2D 0%, #0F2035 100%);
    border: 1px solid #1D3450;
    border-radius: 12px;
    padding: 20px 24px;
    margin-bottom: 14px;
    transition: border-color 0.18s, box-shadow 0.18s;
}
.intel-card:hover { border-color: #2E5070; box-shadow: 0 4px 24px rgba(0,0,0,0.3); }

.news-card {
    background: linear-gradient(160deg, #0B1A2D 0%, #0F2035 100%);
    border: 1px solid #1D3450;
    border-left: 4px solid #1D3450;
    border-radius: 10px;
    padding: 18px 22px;
    margin-bottom: 12px;
    transition: border-color 0.15s, box-shadow 0.15s;
}
.news-card:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.35); }
.news-card.critical { border-left-color: #FF4B4B; }
.news-card.moderate { border-left-color: #FFA500; }
.news-card.stable   { border-left-color: #21C55D; }

.market-card {
    background: linear-gradient(160deg, #0B1A2D 0%, #0F2035 100%);
    border: 1px solid #1D3450;
    border-radius: 14px;
    padding: 24px 28px;
    margin-bottom: 18px;
    transition: border-color 0.18s, box-shadow 0.18s;
}
.market-card:hover { border-color: #2E5070; box-shadow: 0 6px 30px rgba(0,0,0,0.35); }

/* ─── Audit quote ─── */
.audit-quote {
    background-color: #050D18;
    border-left: 4px solid #C9A84C;
    padding: 14px 18px;
    border-radius: 0 10px 10px 0;
    font-style: italic;
    color: #B8CEE8;
    font-size: 0.90rem;
    line-height: 1.75;
    margin: 12px 0;
}

/* ─── Table ─── */
.tbl-header {
    color: #C9A84C;
    font-size: 0.76rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    padding: 10px 8px;
    border-bottom: 2px solid #1D3450;
}
.tbl-cell {
    color: #D8E8F6;
    font-size: 0.90rem;
    padding: 12px 8px;
    border-bottom: 1px solid #111E2E;
    vertical-align: top;
    word-wrap: break-word;
    word-break: break-word;
    line-height: 1.55;
}

/* ─── Badges / chips ─── */
.sent-tag {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 0.79rem; font-weight: 700; white-space: nowrap;
}
.sent-bearish { background: #3D0E0E; color: #FF7B7B; border: 1px solid rgba(255,75,75,0.3); }
.sent-bullish { background: #0A2E18; color: #34D973; border: 1px solid rgba(52,217,115,0.3); }
.sent-neutral { background: #152030; color: #7A9BBE; border: 1px solid rgba(122,155,190,0.3); }

.risk-tag {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 0.79rem; font-weight: 700; white-space: nowrap;
}
.risk-critical { background: #2E0808; color: #FF5555; border: 1px solid rgba(255,75,75,0.3); }
.risk-moderate { background: #211400; color: #FFB020; border: 1px solid rgba(255,160,32,0.3); }
.risk-low      { background: #082214; color: #28D96A; border: 1px solid rgba(40,217,106,0.3); }

.ticker-chip {
    display: inline-block;
    background: #102030;
    color: #C9A84C;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.80rem;
    font-weight: 700;
    white-space: nowrap;
    margin: 2px;
    border: 1px solid rgba(201,168,76,0.3);
}

.sol-badge {
    display: inline-block; padding: 4px 12px; border-radius: 20px;
    font-size: 0.79rem; font-weight: 700; white-space: nowrap;
}
.sol-active   { background: #2E0808; color: #FF5555; border: 1px solid rgba(255,75,75,0.3); }
.sol-pending  { background: #211400; color: #FFB020; border: 1px solid rgba(255,160,32,0.3); }
.sol-ballot   { background: #1E1800; color: #C9A84C; border: 1px solid rgba(201,168,76,0.3); }
.sol-defeated { background: #082214; color: #28D96A; border: 1px solid rgba(40,217,106,0.3); }

/* ─── Stat boxes ─── */
.stat-box {
    background: #050D18;
    border: 1px solid #1D3450;
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
}
.stat-box .stat-val { color: #C9A84C; font-size: 1.45rem; font-weight: 700; }
.stat-box .stat-lbl {
    color: #6E90B2; font-size: 0.72rem;
    text-transform: uppercase; letter-spacing: 0.07em; margin-top: 3px;
}

/* ─── Floating AI robot button ─── */
@keyframes neon-pulse {
    0%   { box-shadow: 0 0 8px 2px rgba(0,255,136,0.7), 0 4px 20px rgba(0,0,0,0.6); }
    50%  { box-shadow: 0 0 22px 8px rgba(0,255,136,0.4), 0 4px 20px rgba(0,0,0,0.6); }
    100% { box-shadow: 0 0 8px 2px rgba(0,255,136,0.7), 0 4px 20px rgba(0,0,0,0.6); }
}
#ai-fab {
    position: fixed;
    bottom: 28px;
    right: 28px;
    z-index: 99999;
    width: 62px;
    height: 62px;
    border-radius: 50%;
    background: linear-gradient(135deg, #00FF88 0%, #00BB55 100%);
    border: 2px solid rgba(0,255,136,0.6);
    cursor: pointer;
    font-size: 26px;
    display: flex;
    align-items: center;
    justify-content: center;
    animation: neon-pulse 2.4s ease-in-out infinite;
    transition: transform 0.2s;
    text-decoration: none;
    line-height: 1;
}
#ai-fab:hover { transform: scale(1.14); }

/* ─── Chat panel ─── */
.chat-panel-wrap {
    background: linear-gradient(160deg, #070F1D 0%, #0B1A2D 100%);
    border: 1.5px solid #00CC66;
    border-radius: 18px;
    padding: 0;
    overflow: hidden;
    box-shadow: 0 8px 40px rgba(0,0,0,0.6), 0 0 40px rgba(0,204,102,0.08);
}
.chat-panel-header {
    background: linear-gradient(90deg, #071A0F 0%, #0A2318 100%);
    border-bottom: 1px solid #00CC66;
    padding: 14px 20px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.chat-panel-body { padding: 14px 16px 0 16px; max-height: 380px; overflow-y: auto; }

/* ─── Sig bar ─── */
.sig-bar-container { margin: 8px 0 14px 0; }
.sig-bar-label { font-size: 0.82rem; color: #6E90B2; margin-bottom: 4px; display: flex; justify-content: space-between; }
</style>
""", unsafe_allow_html=True)


# ─── Data loading ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def load_data() -> pd.DataFrame:
    if not os.path.exists(DB_PATH):
        # Auto-seed when deployed (e.g. Streamlit Community Cloud)
        try:
            import db_seeder
            db_seeder.main()
        except Exception:
            st.error(f"Database not found at `{DB_PATH}`. Run `python db_seeder.py` first.")
            st.stop()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM market_intelligence ORDER BY last_updated DESC", conn
    )
    conn.close()
    return df


df_all = load_data()


# ─── Live News Scraper ─────────────────────────────────────────────────────────

# Maps tickers to company names for better search results
_TICKER_SEARCH_TERMS = {
    "AVB":  "AvalonBay Communities REIT",
    "EQR":  "Equity Residential REIT",
    "ESS":  "Essex Property Trust REIT",
    "MAA":  "Mid-America Apartment REIT",
    "CPT":  "Camden Property Trust REIT",
    "UDR":  "UDR apartment REIT",
    "INVH": "Invitation Homes REIT",
    "AMH":  "American Homes 4 Rent REIT",
    "CSR":  "Centerspace REIT",
}

_TOPIC_QUERIES = [
    ("rent control legislation", []),
    ("apartment rent cap law", []),
    ("multifamily REIT regulation", ["AVB", "EQR", "ESS", "MAA", "CPT", "UDR"]),
    ("algorithmic pricing rent ban", ["AVB", "EQR", "ESS"]),
    ("single family rental regulation", ["INVH", "AMH"]),
]


@st.cache_data(ttl=300)
def fetch_live_news() -> pd.DataFrame:
    """Pull headlines from Google News RSS for tracked tickers and rent-control topics."""
    rows = []
    seen_titles = set()

    def _fetch(query: str, tickers: list):
        url = (
            "https://news.google.com/rss/search?"
            + urllib.parse.urlencode({"q": query, "hl": "en-US", "gl": "US", "ceid": "US:en"})
        )
        try:
            feed = feedparser.parse(url)
        except Exception:
            return
        for entry in feed.entries[:5]:
            title = entry.get("title", "").strip()
            if not title or title in seen_titles:
                continue
            seen_titles.add(title)
            source = entry.get("source", {}).get("title", "Google News")
            published = entry.get("published", "")[:16]
            link = entry.get("link", "")
            summary_raw = entry.get("summary", "")
            # Strip HTML tags from summary
            import re
            summary = re.sub(r"<[^>]+>", " ", summary_raw).strip()[:300]
            rows.append({
                "headline": title,
                "source_name": source,
                "published": published,
                "url": link,
                "tickers_exposed": ",".join(tickers) if tickers else "",
                "summary": summary,
            })

    # Per-ticker queries
    for ticker, term in _TICKER_SEARCH_TERMS.items():
        _fetch(term, [ticker])

    # Topic queries
    for query, tickers in _TOPIC_QUERIES:
        _fetch(query, tickers)

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows)


# ─── Prediction Market Feeds ──────────────────────────────────────────────────

_POLY_KEYWORDS = [
    # Housing / rent control
    "rent control", "rent cap", "rent stabilization", "housing ballot",
    "eviction", "tenant", "landlord", "multifamily", "housing", "real estate",
    "california ballot", "new york rent", "oregon rent", "zoning",
    # Macro / REIT drivers
    "federal reserve", "rate cut", "rate hike", "interest rate", "fed funds",
    "recession", "unemployment", "jobs report", "cpi", "inflation", "gdp",
    "treasury yield", "mortgage rate", "10-year", "10 year",
    # Elections affecting housing legislation
    "senate", "congress", "governor", "california governor",
]

_MANIFOLD_QUERIES = [
    ("rent control", "Housing Policy"),
    ("rent freeze NYC", "Housing Policy"),
    ("housing ballot", "Housing Policy"),
    ("zoning reform", "Housing Policy"),
    ("federal reserve rate cut 2026", "Fed / Rates"),
    ("federal reserve hike 2026", "Fed / Rates"),
    ("recession 2026", "Macro"),
    ("us inflation 2026", "Macro"),
    ("unemployment 2026", "Macro"),
    ("real estate crash", "Real Estate"),
    ("housing market 2026", "Real Estate"),
]

_PREDICTIT_KEYWORDS = [
    # Congressional control — directly affects national housing legislation
    "control the senate", "control the house", "house seats", "senate seats",
    # State governor races in highest rent-control-risk states
    "governor of california", "governor of new york", "governor of oregon",
    "governor of washington", "governor of colorado", "governor of minnesota",
    "governor of illinois", "governor of massachusetts", "governor of new jersey",
    # Key Senate races in those states
    "senate election in california", "senate election in new york",
    "senate election in oregon", "senate election in washington",
    "senate election in colorado", "senate election in minnesota",
    "senate election in illinois", "senate election in massachusetts",
    # Economy / Fed (PredictIt occasionally has these)
    "federal reserve", "interest rate", "inflation", "recession",
]


@st.cache_data(ttl=300)
def fetch_polymarket_odds() -> list[dict]:
    """Fetch active Polymarket markets relevant to housing/macro/elections."""
    results = []
    seen_ids = set()
    try:
        resp = requests.get(
            "https://gamma-api.polymarket.com/markets",
            params={"active": "true", "closed": "false", "limit": 500},
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        markets = resp.json() if isinstance(resp.json(), list) else resp.json().get("data", [])
    except Exception:
        return []

    for m in markets:
        question = m.get("question", "")
        if not question:
            continue
        q_lower = question.lower()
        if not any(kw in q_lower for kw in _POLY_KEYWORDS):
            continue
        mid = m.get("id", question)
        if mid in seen_ids:
            continue
        seen_ids.add(mid)

        outcomes = m.get("outcomes", "[]")
        prices   = m.get("outcomePrices", "[]")
        try:
            outcomes = outcomes if isinstance(outcomes, list) else __import__("json").loads(outcomes)
            prices   = prices   if isinstance(prices,   list) else __import__("json").loads(prices)
        except Exception:
            outcomes, prices = [], []

        prob = None
        for oc, pr in zip(outcomes, prices):
            if str(oc).lower() == "yes":
                try:
                    prob = round(float(pr) * 100, 1)
                except (TypeError, ValueError):
                    pass
                break
        if prob is None and prices:
            try:
                prob = round(float(prices[0]) * 100, 1)
            except (TypeError, ValueError):
                pass

        end_date = (m.get("endDate") or "")[:10]
        volume = m.get("volume", 0)
        try:
            volume = int(float(volume))
        except (TypeError, ValueError):
            volume = 0

        slug = m.get("slug", "")
        url = f"https://polymarket.com/event/{slug}" if slug else "https://polymarket.com"

        results.append({"question": question, "prob": prob, "end_date": end_date,
                        "volume": volume, "url": url})

    results.sort(key=lambda x: x["volume"], reverse=True)
    return results[:20]


@st.cache_data(ttl=300)
def fetch_manifold_odds() -> list[dict]:
    """Fetch Manifold Markets binary questions relevant to housing/macro."""
    results = []
    seen_ids = set()
    for term, category in _MANIFOLD_QUERIES:
        try:
            resp = requests.get(
                "https://api.manifold.markets/v0/search-markets",
                params={"term": term, "limit": 4, "filter": "open",
                        "sort": "liquidity", "contractType": "BINARY"},
                timeout=8,
            )
            markets = resp.json() if resp.ok else []
        except Exception:
            continue
        for m in markets:
            if m.get("probability") is None:
                continue
            mid = m.get("id", m.get("url", ""))
            if mid in seen_ids:
                continue
            seen_ids.add(mid)
            try:
                prob = round(float(m["probability"]) * 100, 1)
            except (TypeError, ValueError):
                continue
            close_ms = m.get("closeTime", 0)
            try:
                import datetime
                end_date = datetime.datetime.fromtimestamp(close_ms / 1000).strftime("%Y-%m-%d")
            except Exception:
                end_date = ""
            results.append({
                "question": m.get("question", ""),
                "prob": prob,
                "end_date": end_date,
                "volume": int(m.get("volume", 0)),
                "traders": m.get("uniqueBettorCount", 0),
                "url": m.get("url", "https://manifold.markets"),
                "category": category,
            })
    results.sort(key=lambda x: x["volume"], reverse=True)
    seen_q: set = set()
    deduped = []
    for r in results:
        key = r["question"][:60].lower()
        if key not in seen_q:
            seen_q.add(key)
            deduped.append(r)
    return deduped[:20]


@st.cache_data(ttl=300)
def fetch_predictit_odds() -> list[dict]:
    """Fetch PredictIt markets relevant to elections in REIT-exposed states + congressional control."""
    try:
        resp = requests.get(
            "https://www.predictit.org/api/marketdata/all/",
            timeout=8,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp.raise_for_status()
        all_markets = resp.json().get("markets", [])
    except Exception:
        return []

    results = []
    for m in all_markets:
        name = m.get("name", "")
        if not any(kw in name.lower() for kw in _PREDICTIT_KEYWORDS):
            continue
        contracts = m.get("contracts", [])
        contract_rows = []
        for c in contracts:
            price = c.get("lastTradePrice") or c.get("bestYesPrice")
            try:
                prob = round(float(price) * 100, 1) if price is not None else None
            except (TypeError, ValueError):
                prob = None
            contract_rows.append({"name": c.get("name", ""), "prob": prob})
        contract_rows = [r for r in contract_rows if r["prob"] is not None]
        if not contract_rows:
            continue
        results.append({
            "question": name,
            "contracts": contract_rows[:4],
            "url": m.get("url", "https://www.predictit.org"),
        })
    return results[:20]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def filter_by_tickers(df: pd.DataFrame, tickers: list) -> pd.DataFrame:
    if not tickers or set(tickers) == set(ALL_TICKERS):
        return df
    ticker_set = set(tickers)
    return df[df["tickers_exposed"].apply(
        lambda c: bool(ticker_set & set(str(c).split(",")))
    )]


def sol_badge(sol: str) -> str:
    css = {
        "Active Enforced":    "sol-active",
        "Pending Vote":       "sol-pending",
        "Developing Ballot":  "sol-ballot",
        "Defeated/Preempted": "sol-defeated",
    }
    klass = css.get(sol, "sol-pending")
    return f"<span class='sol-badge {klass}'>{sol}</span>"


def risk_badge(risk: str) -> str:
    css = {"Critical": "risk-critical", "Moderate": "risk-moderate", "Low/Stable": "risk-low"}
    klass = css.get(risk, "risk-low")
    return f"<span class='risk-tag {klass}'>{risk}</span>"


def sent_badge(score: float) -> str:
    if score < -0.2:
        return f"<span class='sent-tag sent-bearish'>▼ BEARISH {score:+.2f}</span>"
    elif score > 0.2:
        return f"<span class='sent-tag sent-bullish'>▲ BULLISH {score:+.2f}</span>"
    return f"<span class='sent-tag sent-neutral'>● NEUTRAL {score:+.2f}</span>"


def ticker_chips(tickers_str: str) -> str:
    return " ".join(
        f"<span class='ticker-chip'>{t.strip()}</span>"
        for t in str(tickers_str).split(",") if t.strip()
    )


def sentiment_color(score: float) -> str:
    if score < -0.2:
        return "#FF7070"
    elif score > 0.2:
        return "#2ECC71"
    return "#7A9BBE"


# ─── AI assistant ─────────────────────────────────────────────────────────────

def build_ai_context(df: pd.DataFrame) -> str:
    lines = [
        "You are an expert REIT legislative risk analyst for an institutional investment fund.",
        "Tracked tickers: AVB (AvalonBay), EQR (Equity Residential), ESS (Essex Property Trust), "
        "MAA (Mid-America Apartment), CPT (Camden Property Trust), UDR, INVH (Invitation Homes), "
        "AMH (American Homes 4 Rent), CSR (Centerspace — upper Midwest: MN, CO, MT, ND, SD, NE, UT).",
        "CenterSquare Investment Management 13F (03/31/2026) holds: CPT $258M, UDR $282M, INVH $185M, "
        "AMH $166M, MAA $75M, EQR $68M, ESS $52M.",
        "",
        "Current market intelligence database:",
    ]
    for _, row in df.iterrows():
        lines.append(
            f"[{row['state_code']}] {row['metro_market']} | Tickers: {row['tickers_exposed']} | "
            f"{row['category']} | {row['state_of_law']} | Risk: {row['portfolio_risk_impact']} | "
            f"Sentiment: {row['sentiment_score']:.2f}\n"
            f"  Summary: {str(row['summary_insight'])[:350]}"
        )
    lines += [
        "",
        "Answer questions concisely. Quantify NOI impacts when data is available.",
        "Format with bullet points for multi-part answers. Keep responses under 350 words unless asked for detail.",
    ]
    return "\n".join(lines)


def get_ai_response(question: str, df: pd.DataFrame) -> str:
    api_key = st.session_state.get("api_key_input", "") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return (
            "**API key required.** Enter your Anthropic API key in the field above the chat, "
            "or set the `ANTHROPIC_API_KEY` environment variable before launching Streamlit."
        )
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=900,
            system=build_ai_context(df),
            messages=[
                *[
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.get("chat_history", [])[-6:]
                ],
                {"role": "user", "content": question},
            ],
        )
        return response.content[0].text
    except ImportError:
        return "Anthropic library missing. Run: `pip install anthropic`"
    except Exception as e:
        err = str(e)
        if "authentication" in err.lower() or "api_key" in err.lower() or "401" in err:
            return "**Authentication error.** Check that your API key is valid."
        return f"**Error:** {err}"


# ─── Sidebar ─────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        "<div style='color:#C9A84C;font-size:1.05rem;font-weight:700;"
        "border-bottom:1px solid #1B3150;padding-bottom:10px;margin-bottom:14px;'>"
        "🏢 REIT Intelligence Engine</div>",
        unsafe_allow_html=True,
    )

    selected_tickers = st.multiselect(
        "REIT Tickers", ALL_TICKERS, default=ALL_TICKERS,
        help="Filter all views by REIT ticker",
    )
    st.session_state["_sidebar_tickers"] = selected_tickers or ALL_TICKERS
    all_metros = sorted(df_all["metro_market"].unique().tolist())
    selected_metros = st.multiselect(
        "Metro Market", all_metros, default=all_metros,
    )
    risk_filter = st.multiselect(
        "Risk Level", ["Critical", "Moderate", "Low/Stable"],
        default=["Critical", "Moderate", "Low/Stable"],
    )

    st.markdown("---")
    st.markdown(
        "<div style='color:#7A9BBE;font-size:0.72rem;'>"
        "CenterSquare 13F · 03/31/2026<br>"
        "9 tickers · 26 markets · 22 states</div>",
        unsafe_allow_html=True,
    )

# ─── Apply filters ────────────────────────────────────────────────────────────

filtered_df = df_all.copy()
filtered_df = filter_by_tickers(filtered_df, selected_tickers)
if selected_metros:
    filtered_df = filtered_df[filtered_df["metro_market"].isin(selected_metros)]
if risk_filter:
    filtered_df = filtered_df[filtered_df["portfolio_risk_impact"].isin(risk_filter)]

# ─── Page header ─────────────────────────────────────────────────────────────

st.markdown("""
<div class="page-header">
  <h1>US Multifamily REIT &amp; Rent Control Intelligence Engine</h1>
  <p>Institutional Legislative Risk Platform &nbsp;·&nbsp;
     AVB &nbsp;·&nbsp; EQR &nbsp;·&nbsp; ESS &nbsp;·&nbsp; MAA &nbsp;·&nbsp;
     CPT &nbsp;·&nbsp; UDR &nbsp;·&nbsp; INVH &nbsp;·&nbsp; AMH &nbsp;·&nbsp; CSR
     &nbsp;·&nbsp; Powered by CenterSquare 13F &amp; Primary Legislative Sources</p>
</div>
""", unsafe_allow_html=True)

# ─── Metrics ribbon ───────────────────────────────────────────────────────────

active_states = filtered_df[
    filtered_df["state_of_law"].isin(["Active Enforced", "Pending Vote"])
]["state_code"].nunique()
total_states = max(filtered_df["state_code"].nunique(), 1)
exposure_pct = active_states / total_states * 100

critical_count = int((filtered_df["portfolio_risk_impact"] == "Critical").sum())
volatility_label = "HIGH VOLATILITY" if critical_count >= 4 else ("ELEVATED" if critical_count >= 2 else "CONTAINED")

ballot_active = int(
    ((filtered_df["category"] == "Ballot Initiative") &
     (filtered_df["state_of_law"] != "Defeated/Preempted")).sum()
)

avg_sentiment = filtered_df["sentiment_score"].mean() if not filtered_df.empty else 0.0
sentiment_label = "BEARISH" if avg_sentiment < -0.2 else ("BULLISH" if avg_sentiment > 0.2 else "NEUTRAL")

mc1, mc2, mc3, mc4, mc5 = st.columns(5)
mc1.metric("Fund Exposure Index", f"{exposure_pct:.1f}%",
           delta=f"{active_states}/{total_states} states at risk", delta_color="inverse")
mc2.metric("NOI Volatility Vector", volatility_label,
           delta=f"{critical_count} critical markets", delta_color="inverse")
mc3.metric("Active Ballot Measures", ballot_active,
           delta="Unresolved items", delta_color="off")
mc4.metric("Portfolio Sentiment", f"{avg_sentiment:+.2f}",
           delta=sentiment_label, delta_color="off")
mc5.metric("Markets Tracked", len(filtered_df),
           delta=f"of {len(df_all)} total records", delta_color="off")

st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

# ─── Tabs ─────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🗺️ Regulatory Heatmap",
    "📋 Portfolio Intelligence",
    "🗳️ Election & Ballot Pulse",
    "📰 News Terminal",
    "📊 Market Analysis",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — ALL-50-STATE CHOROPLETH
# ══════════════════════════════════════════════════════════════════════════════

with tab1:
    st.markdown("<div class='section-title'>Legislative Sentiment — All 50 US States</div>", unsafe_allow_html=True)

    # Build a DataFrame with ALL states, merging DB data over baseline
    db_state_agg = (
        df_all.groupby("state_code")
        .agg(
            db_sentiment=("sentiment_score", "mean"),
            market_count=("metro_market", "count"),
            critical_count=("portfolio_risk_impact", lambda x: (x == "Critical").sum()),
            active_laws=("state_of_law", lambda x: (x == "Active Enforced").sum()),
            tickers_all=("tickers_exposed", lambda x: ",".join(x)),
        )
        .reset_index()
    )

    state_frame = pd.DataFrame({"state_code": ALL_STATES})
    state_frame = state_frame.merge(db_state_agg, on="state_code", how="left")
    state_frame["sentiment_score"] = state_frame.apply(
        lambda r: r["db_sentiment"] if pd.notna(r["db_sentiment"])
        else STATE_BASELINE.get(r["state_code"], 0.0),
        axis=1,
    )
    state_frame["data_source"] = state_frame["market_count"].apply(
        lambda x: "Active Coverage" if pd.notna(x) and x > 0 else "Baseline Estimate"
    )
    state_frame["market_count"]   = state_frame["market_count"].fillna(0).astype(int)
    state_frame["critical_count"] = state_frame["critical_count"].fillna(0).astype(int)
    state_frame["active_laws"]    = state_frame["active_laws"].fillna(0).astype(int)
    state_frame["sentiment_disp"] = state_frame["sentiment_score"].round(3)

    # Highlight filtered states
    filtered_states = set(filtered_df["state_code"].unique())
    state_frame["in_filter"] = state_frame["state_code"].isin(filtered_states)

    fig_map = px.choropleth(
        state_frame,
        locations="state_code",
        locationmode="USA-states",
        color="sentiment_score",
        scope="usa",
        color_continuous_scale=[
            [0.00, "#7B0000"],
            [0.20, "#CC2200"],
            [0.35, "#8B3A00"],
            [0.50, "#1B3150"],
            [0.65, "#1E6080"],
            [0.80, "#1A7A4A"],
            [1.00, "#C9A84C"],
        ],
        range_color=[-1.0, 1.0],
        hover_name="state_code",
        hover_data={
            "sentiment_disp": True,
            "market_count": True,
            "critical_count": True,
            "active_laws": True,
            "data_source": True,
            "sentiment_score": False,
        },
        labels={
            "sentiment_disp":  "Sentiment Score",
            "market_count":    "Markets in DB",
            "critical_count":  "Critical Risk Items",
            "active_laws":     "Active Enforced Laws",
            "data_source":     "Coverage Type",
        },
    )
    fig_map.update_layout(
        template="plotly_dark",
        paper_bgcolor="#070F1D",
        plot_bgcolor="#070F1D",
        geo=dict(
            bgcolor="#070F1D", lakecolor="#070F1D",
            landcolor="#0C1929", subunitcolor="#1B3150",
            showlakes=True, showframe=False,
            coastlinecolor="#1B3150",
            showsubunits=True,
        ),
        font=dict(color="#D4DCE8", family="Inter, Segoe UI, sans-serif", size=12),
        coloraxis_colorbar=dict(
            title=dict(text="Sentiment", font=dict(color="#C9A84C", size=12)),
            tickfont=dict(color="#D4DCE8", size=11),
            bgcolor="#0C1929", bordercolor="#1B3150",
            thickness=16, len=0.75,
            tickvals=[-1.0, -0.5, 0, 0.5, 1.0],
            ticktext=["−1.0 Tenant-Favorable", "−0.5", "Neutral", "+0.5", "+1.0 Landlord-Favorable"],
        ),
        margin=dict(l=0, r=0, t=10, b=10),
        height=480,
    )
    st.plotly_chart(fig_map, use_container_width=True)

    st.markdown(
        "<div style='color:#7A9BBE;font-size:0.78rem;margin:-8px 0 16px 0;'>"
        "🔵 Dark red = tenant-favorable / high regulatory risk &nbsp;|&nbsp; "
        "Navy = neutral &nbsp;|&nbsp; Gold/Green = landlord-favorable / preempted &nbsp;|&nbsp; "
        "Hatched = active database coverage</div>",
        unsafe_allow_html=True,
    )

    col_tbl, col_chart = st.columns([3, 2])

    with col_tbl:
        st.markdown("<div class='section-title'>State Summary</div>", unsafe_allow_html=True)
        display_tbl = (
            state_frame[["state_code", "sentiment_score", "market_count", "critical_count", "data_source"]]
            .rename(columns={
                "state_code":     "State",
                "sentiment_score": "Sentiment",
                "market_count":   "Markets",
                "critical_count": "Critical",
                "data_source":    "Coverage",
            })
            .sort_values("Sentiment")
            .reset_index(drop=True)
        )
        display_tbl["Sentiment"] = display_tbl["Sentiment"].round(3)
        st.dataframe(display_tbl, use_container_width=True, hide_index=True, height=380)

    with col_chart:
        st.markdown("<div class='section-title'>Risk Distribution</div>", unsafe_allow_html=True)
        risk_counts = df_all["portfolio_risk_impact"].value_counts().reset_index()
        risk_counts.columns = ["Risk", "Count"]
        fig_donut = px.pie(
            risk_counts, names="Risk", values="Count",
            color="Risk", color_discrete_map=RISK_COLORS,
            hole=0.5, template="plotly_dark",
        )
        fig_donut.update_layout(
            paper_bgcolor="#0C1929", font=dict(color="#D4DCE8"),
            margin=dict(l=10, r=10, t=10, b=10), height=200,
            legend=dict(font=dict(color="#D4DCE8", size=12), bgcolor="#0C1929"),
            showlegend=True,
        )
        fig_donut.update_traces(textfont_color="#D4DCE8", textfont_size=13)
        st.plotly_chart(fig_donut, use_container_width=True)

        st.markdown("<div class='section-title' style='margin-top:10px;'>By Category</div>", unsafe_allow_html=True)
        cat_counts = df_all["category"].value_counts().reset_index()
        cat_counts.columns = ["Category", "Count"]
        fig_cat = px.bar(
            cat_counts, x="Count", y="Category", orientation="h",
            color="Count", color_continuous_scale=["#1B3150", "#C9A84C"],
            template="plotly_dark",
        )
        fig_cat.update_layout(
            paper_bgcolor="#0C1929", plot_bgcolor="#0C1929",
            font=dict(color="#D4DCE8", size=11),
            margin=dict(l=10, r=10, t=10, b=10), height=160,
            showlegend=False, coloraxis_showscale=False,
            xaxis=dict(gridcolor="#1B3150"),
            yaxis=dict(gridcolor="#0C1929"),
        )
        st.plotly_chart(fig_cat, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PORTFOLIO INTELLIGENCE
# ══════════════════════════════════════════════════════════════════════════════

with tab2:
    st.markdown("<div class='section-title'>Portfolio Legislative Exposure Matrix</div>", unsafe_allow_html=True)

    if filtered_df.empty:
        st.warning("No data matches current filters.")
    else:
        # ── Top-line charts ────────────────────────────────────────────────
        ch1, ch2, ch3 = st.columns(3)

        with ch1:
            # Count exposure per ticker
            ticker_exposure = {}
            for t in ALL_TICKERS:
                cnt = filtered_df["tickers_exposed"].apply(
                    lambda c: t in str(c).split(",")
                ).sum()
                ticker_exposure[t] = int(cnt)
            ticker_df = pd.DataFrame(list(ticker_exposure.items()), columns=["Ticker", "Exposure"])
            ticker_df = ticker_df.sort_values("Exposure", ascending=True)
            fig_t = px.bar(
                ticker_df, x="Exposure", y="Ticker", orientation="h",
                color="Exposure", color_continuous_scale=["#1B3150", "#C9A84C"],
                title="Legislative Items per Ticker",
                template="plotly_dark",
            )
            fig_t.update_layout(
                paper_bgcolor="#0C1929", plot_bgcolor="#0C1929",
                font=dict(color="#D4DCE8", size=11),
                margin=dict(l=0, r=10, t=36, b=10), height=260,
                title_font=dict(color="#C9A84C", size=12),
                showlegend=False, coloraxis_showscale=False,
                xaxis=dict(gridcolor="#1B3150"),
                yaxis=dict(gridcolor="#0C1929"),
            )
            st.plotly_chart(fig_t, use_container_width=True)

        with ch2:
            # Critical NOI items per ticker
            crit_df = filtered_df[filtered_df["portfolio_risk_impact"] == "Critical"]
            crit_exposure = {}
            for t in ALL_TICKERS:
                cnt = crit_df["tickers_exposed"].apply(
                    lambda c: t in str(c).split(",")
                ).sum()
                crit_exposure[t] = int(cnt)
            crit_frame = pd.DataFrame(
                [(k, v) for k, v in crit_exposure.items() if v > 0],
                columns=["Ticker", "Critical Items"],
            ).sort_values("Critical Items", ascending=True)
            if crit_frame.empty:
                st.info("No critical items in current filter.")
            else:
                fig_c = px.bar(
                    crit_frame, x="Critical Items", y="Ticker", orientation="h",
                    color="Critical Items", color_continuous_scale=["#FFA500", "#FF4B4B"],
                    title="Critical Risk Exposure by Ticker",
                    template="plotly_dark",
                )
                fig_c.update_layout(
                    paper_bgcolor="#0C1929", plot_bgcolor="#0C1929",
                    font=dict(color="#D4DCE8", size=11),
                    margin=dict(l=0, r=10, t=36, b=10), height=260,
                    title_font=dict(color="#C9A84C", size=12),
                    showlegend=False, coloraxis_showscale=False,
                    xaxis=dict(gridcolor="#1B3150"),
                    yaxis=dict(gridcolor="#0C1929"),
                )
                st.plotly_chart(fig_c, use_container_width=True)

        with ch3:
            fig_sent = px.bar(
                filtered_df.sort_values("sentiment_score"),
                x="sentiment_score",
                y="metro_market",
                orientation="h",
                color="sentiment_score",
                color_continuous_scale=[
                    [0.0, "#CC2200"], [0.5, "#1B3150"], [1.0, "#C9A84C"]
                ],
                range_color=[-1.0, 1.0],
                title="Market Sentiment Scores",
                template="plotly_dark",
            )
            fig_sent.update_layout(
                paper_bgcolor="#0C1929", plot_bgcolor="#0C1929",
                font=dict(color="#D4DCE8", size=10),
                margin=dict(l=0, r=10, t=36, b=10), height=260,
                title_font=dict(color="#C9A84C", size=12),
                showlegend=False, coloraxis_showscale=False,
                xaxis=dict(gridcolor="#1B3150", range=[-1.1, 1.1]),
                yaxis=dict(gridcolor="#0C1929"),
            )
            fig_sent.add_vline(x=0, line_color="#7A9BBE", line_dash="dash", line_width=1)
            st.plotly_chart(fig_sent, use_container_width=True)

        st.markdown("<div style='margin-top:10px;'></div>", unsafe_allow_html=True)
        st.markdown("<div class='section-title'>Legislative Exposure Detail</div>", unsafe_allow_html=True)

        # ── Matrix table ───────────────────────────────────────────────────
        col_w = [2.0, 0.6, 1.8, 1.8, 1.9, 1.3, 0.9, 0.8]
        headers = ["Metro Market", "St.", "Tickers", "Category", "Status", "Risk", "Sent.", "Audit"]

        hdr = st.columns(col_w)
        for c, h in zip(hdr, headers):
            c.markdown(f"<div class='tbl-header'>{h}</div>", unsafe_allow_html=True)

        for _, row in filtered_df.iterrows():
            rc = st.columns(col_w)
            rc[0].markdown(
                f"<div class='tbl-cell'><strong style='color:#E8EDF5;'>{row['metro_market']}</strong>"
                f"<br><span style='color:#7A9BBE;font-size:0.75rem;'>{row['source_name'][:40] if row['source_name'] else ''}</span></div>",
                unsafe_allow_html=True,
            )
            rc[1].markdown(f"<div class='tbl-cell'><strong style='color:#C9A84C;'>{row['state_code']}</strong></div>", unsafe_allow_html=True)
            rc[2].markdown(f"<div class='tbl-cell'>{ticker_chips(row['tickers_exposed'])}</div>", unsafe_allow_html=True)
            rc[3].markdown(f"<div class='tbl-cell'><span style='color:#C8D8EE;'>{row['category']}</span></div>", unsafe_allow_html=True)
            rc[4].markdown(f"<div class='tbl-cell'>{sol_badge(row['state_of_law'])}</div>", unsafe_allow_html=True)
            rc[5].markdown(f"<div class='tbl-cell'>{risk_badge(row['portfolio_risk_impact'])}</div>", unsafe_allow_html=True)
            rc[6].markdown(
                f"<div class='tbl-cell'><span style='color:{sentiment_color(row['sentiment_score'])};font-weight:700;'>"
                f"{row['sentiment_score']:+.2f}</span></div>",
                unsafe_allow_html=True,
            )
            with rc[7]:
                st.markdown("<div style='padding-top:6px;'></div>", unsafe_allow_html=True)
                if st.button("Audit", key=f"a2_{row['id']}"):
                    st.session_state["audit_row_id"] = int(row["id"])

            with st.expander(f"▸ Summary: {row['metro_market']}", expanded=False):
                ec1, ec2 = st.columns([4, 1])
                ec1.markdown(
                    f"<div style='color:#C8D8EE;font-size:0.87rem;line-height:1.7;'>{row['summary_insight']}</div>",
                    unsafe_allow_html=True,
                )
                with ec2:
                    st.markdown(
                        f"<div style='color:#7A9BBE;font-size:0.75rem;'>"
                        f"Updated:<br><span style='color:#C9A84C;'>{row['last_updated']}</span></div>",
                        unsafe_allow_html=True,
                    )
                    if row["source_url"]:
                        st.markdown(f"[🔗 Source]({row['source_url']})")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — ELECTION & BALLOT PULSE
# ══════════════════════════════════════════════════════════════════════════════

with tab3:
    st.markdown("<div class='section-title'>Election & Ballot Initiative Tracker</div>", unsafe_allow_html=True)

    ballot_df = filtered_df[
        filtered_df["category"].isin(["Ballot Initiative", "Candidate Profiling"])
    ].copy()

    all_ballot = df_all[df_all["category"].isin(["Ballot Initiative", "Candidate Profiling"])].copy()

    # ── Top KPI strip ──────────────────────────────────────────────────────
    bk1, bk2, bk3, bk4 = st.columns(4)
    bk1.metric("Ballot Items Tracked", len(all_ballot))
    bk2.metric("Active / Developing",
               int(all_ballot["state_of_law"].isin(["Developing Ballot", "Pending Vote"]).sum()))
    bk3.metric("Defeated / Preempted",
               int((all_ballot["state_of_law"] == "Defeated/Preempted").sum()))
    bk4.metric("Candidate Profiles",
               int((all_ballot["category"] == "Candidate Profiling").sum()))

    st.markdown("<div style='margin-top:18px;'></div>", unsafe_allow_html=True)

    # ── Status pipeline chart ─────────────────────────────────────────────
    col_pipe, col_map = st.columns([3, 2])

    with col_pipe:
        st.markdown("<div class='section-title'>Initiative Pipeline</div>", unsafe_allow_html=True)
        if all_ballot.empty:
            st.info("No ballot data.")
        else:
            status_counts = all_ballot["state_of_law"].value_counts().reset_index()
            status_counts.columns = ["Status", "Count"]
            ordered = ["Developing Ballot", "Pending Vote", "Active Enforced", "Defeated/Preempted"]
            status_counts["Status"] = pd.Categorical(status_counts["Status"], categories=ordered, ordered=True)
            status_counts = status_counts.sort_values("Status")

            fig_pipe = px.bar(
                status_counts, x="Status", y="Count",
                color="Status", color_discrete_map=SOL_COLORS,
                template="plotly_dark",
                text="Count",
            )
            fig_pipe.update_layout(
                paper_bgcolor="#0C1929", plot_bgcolor="#0C1929",
                font=dict(color="#D4DCE8", size=12),
                margin=dict(l=10, r=10, t=20, b=10), height=240,
                showlegend=False,
                xaxis=dict(tickfont=dict(color="#D4DCE8", size=11), gridcolor="#1B3150"),
                yaxis=dict(tickfont=dict(color="#D4DCE8"), gridcolor="#1B3150"),
            )
            fig_pipe.update_traces(textfont=dict(color="#D4DCE8"), textposition="outside")
            st.plotly_chart(fig_pipe, use_container_width=True)

    with col_map:
        st.markdown("<div class='section-title'>Tickers at Risk</div>", unsafe_allow_html=True)
        if not all_ballot.empty:
            bt_exposure = {}
            for t in ALL_TICKERS:
                active_rows = all_ballot[all_ballot["state_of_law"].isin(["Developing Ballot", "Pending Vote"])]
                cnt = active_rows["tickers_exposed"].apply(
                    lambda c: t in str(c).split(",")
                ).sum()
                if cnt > 0:
                    bt_exposure[t] = int(cnt)
            if bt_exposure:
                bt_df = pd.DataFrame(list(bt_exposure.items()), columns=["Ticker", "Active Initiatives"])
                fig_bt = px.bar(
                    bt_df.sort_values("Active Initiatives", ascending=True),
                    x="Active Initiatives", y="Ticker", orientation="h",
                    color="Active Initiatives",
                    color_continuous_scale=["#FFA500", "#FF4B4B"],
                    template="plotly_dark",
                )
                fig_bt.update_layout(
                    paper_bgcolor="#0C1929", plot_bgcolor="#0C1929",
                    font=dict(color="#D4DCE8", size=11),
                    margin=dict(l=0, r=10, t=10, b=10), height=240,
                    showlegend=False, coloraxis_showscale=False,
                    xaxis=dict(gridcolor="#1B3150"),
                    yaxis=dict(gridcolor="#0C1929"),
                )
                st.plotly_chart(fig_bt, use_container_width=True)

    st.markdown("<div style='margin-top:6px;'></div>", unsafe_allow_html=True)

    # ── Active signature campaigns ──────────────────────────────────────────
    active_ballot = all_ballot[all_ballot["state_of_law"] == "Developing Ballot"]
    if not active_ballot.empty:
        st.markdown("<div class='section-title'>Signature Collection Progress</div>", unsafe_allow_html=True)
        for _, row in active_ballot.iterrows():
            sup = BALLOT_SUPPLEMENTS.get(row["metro_market"], {})
            with st.container():
                col_info, col_progress = st.columns([2, 3])
                with col_info:
                    st.markdown(
                        f"<div class='intel-card' style='margin-bottom:0;'>"
                        f"<div style='color:#E8EDF5;font-weight:700;font-size:0.92rem;margin-bottom:6px;'>"
                        f"{row['metro_market']} ({row['state_code']})</div>"
                        f"<div style='margin-bottom:4px;'>{ticker_chips(row['tickers_exposed'])}</div>"
                        f"<div style='color:#7A9BBE;font-size:0.80rem;margin-top:6px;'>{row['category']}</div>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with col_progress:
                    if "signatures_collected" in sup:
                        collected = sup["signatures_collected"]
                        required  = sup["signatures_required"]
                        pct = min(collected / required, 1.0)
                        st.markdown(
                            f"<div style='margin-top:8px;'>"
                            f"<div style='display:flex;justify-content:space-between;color:#C8D8EE;"
                            f"font-size:0.82rem;margin-bottom:6px;'>"
                            f"<span>Signatures Collected</span>"
                            f"<span><strong style='color:#C9A84C;'>{collected:,}</strong>"
                            f" / {required:,} required</span></div>",
                            unsafe_allow_html=True,
                        )
                        st.progress(pct)
                        polling  = sup.get("polling", "N/A")
                        deadline = sup.get("deadline", "N/A")
                        lit      = sup.get("litigation", "None")
                        lit_risk = sup.get("litigation_risk", "Low")
                        lit_color = {"High": "#FF4B4B", "Medium": "#FFA500", "Low": "#21C55D"}.get(lit_risk, "#7A9BBE")
                        next_ms  = sup.get("next_milestone", "")
                        st.markdown(
                            f"<div style='font-size:0.80rem;color:#C8D8EE;margin-top:4px;'>"
                            f"<span style='color:#7A9BBE;'>Polling: </span>{polling} &nbsp;·&nbsp;"
                            f"<span style='color:#7A9BBE;'>Deadline: </span>{deadline}</div>"
                            f"<div style='font-size:0.80rem;margin-top:4px;'>"
                            f"<span style='color:#7A9BBE;'>Litigation: </span>"
                            f"<span style='color:{lit_color};font-weight:600;'>[{lit_risk}] </span>"
                            f"<span style='color:#C8D8EE;'>{lit}</span></div>"
                            f"{'<div style=\"font-size:0.78rem;color:#7A9BBE;margin-top:2px;\">Next: '+next_ms+'</div>' if next_ms else ''}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            f"<div style='padding-top:12px;color:#C8D8EE;font-size:0.87rem;'>{row['summary_insight'][:280]}…</div>",
                            unsafe_allow_html=True,
                        )
                st.markdown("<hr>", unsafe_allow_html=True)

    # ── Candidate profiles ─────────────────────────────────────────────────
    cand_df = all_ballot[all_ballot["category"] == "Candidate Profiling"]
    if not cand_df.empty:
        st.markdown("<div class='section-title'>Candidate Profiles & Stance Rankings</div>", unsafe_allow_html=True)
        for _, row in cand_df.iterrows():
            sup = BALLOT_SUPPLEMENTS.get(row["metro_market"], {})
            r_color = RISK_COLORS.get(row["portfolio_risk_impact"], "#7A9BBE")
            with st.expander(
                f"🗳️  {sup.get('candidate', row['metro_market'])} — {row['state_code']} — {row['state_of_law']}",
                expanded=True,
            ):
                ca, cb, cc = st.columns(3)
                ca.markdown(
                    f"<div class='stat-box'>"
                    f"<div class='stat-val'>{sup.get('polling', 'N/A')}</div>"
                    f"<div class='stat-lbl'>Polling Position</div></div>",
                    unsafe_allow_html=True,
                )
                cb.markdown(
                    f"<div class='stat-box'>"
                    f"<div class='stat-val'>{sup.get('election_date', row['last_updated'][:10])}</div>"
                    f"<div class='stat-lbl'>Election Date</div></div>",
                    unsafe_allow_html=True,
                )
                cc.markdown(
                    f"<div class='stat-box'>"
                    f"<div class='stat-val' style='color:{r_color};'>{row['portfolio_risk_impact']}</div>"
                    f"<div class='stat-lbl'>Portfolio Risk</div></div>",
                    unsafe_allow_html=True,
                )
                st.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
                pa, pb = st.columns(2)
                with pa:
                    st.markdown(
                        f"<div style='color:#7A9BBE;font-size:0.78rem;font-weight:700;text-transform:uppercase;"
                        f"letter-spacing:0.05em;margin-bottom:4px;'>Candidate Stance</div>"
                        f"<div style='color:#C8D8EE;font-size:0.87rem;line-height:1.6;'>"
                        f"{sup.get('stance', row['summary_insight'][:300])}</div>"
                        f"<div style='margin-top:10px;color:#7A9BBE;font-size:0.78rem;font-weight:700;"
                        f"text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;'>Endorsements</div>"
                        f"<div style='color:#2ECC71;font-size:0.85rem;'>{sup.get('endorsements', 'N/A')}</div>",
                        unsafe_allow_html=True,
                    )
                with pb:
                    st.markdown(
                        f"<div style='color:#7A9BBE;font-size:0.78rem;font-weight:700;text-transform:uppercase;"
                        f"letter-spacing:0.05em;margin-bottom:4px;'>Tickers at Risk</div>"
                        f"<div style='margin-bottom:10px;'>{ticker_chips(row['tickers_exposed'])}</div>"
                        f"<div style='color:#7A9BBE;font-size:0.78rem;font-weight:700;text-transform:uppercase;"
                        f"letter-spacing:0.05em;margin-bottom:4px;'>Industry Opposition</div>"
                        f"<div style='color:#FF7070;font-size:0.85rem;'>{sup.get('opposition', 'N/A')}</div>"
                        f"<div style='margin-top:10px;color:#7A9BBE;font-size:0.78rem;font-weight:700;"
                        f"text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;'>"
                        f"Risk If Elected</div>"
                        f"<div style='color:#FFA500;font-size:0.85rem;'>{sup.get('risk_if_elected', 'N/A')}</div>",
                        unsafe_allow_html=True,
                    )

    # ── Pending vote items ─────────────────────────────────────────────────
    pending_df = all_ballot[all_ballot["state_of_law"] == "Pending Vote"]
    if not pending_df.empty:
        st.markdown("<div class='section-title' style='margin-top:18px;'>Pending Legislative Votes</div>", unsafe_allow_html=True)
        for _, row in pending_df.iterrows():
            st.html(
                f"<div class='intel-card'>"
                f"<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
                f"<div style='flex:1;'>"
                f"<div style='color:#E8EDF5;font-weight:700;font-size:0.92rem;margin-bottom:6px;'>{row['headline']}</div>"
                f"<div style='color:#C8D8EE;font-size:0.85rem;line-height:1.65;'>{row['summary_insight'][:400]}&#8230;</div>"
                f"</div><div style='margin-left:20px;text-align:right;white-space:nowrap;'>"
                f"{risk_badge(row['portfolio_risk_impact'])}<br>"
                f"<span style='color:#7A9BBE;font-size:0.75rem;'>{row['state_code']} &middot; {row['last_updated'][:10]}</span><br>"
                f"<div style='margin-top:6px;'>{ticker_chips(row['tickers_exposed'])}</div>"
                f"</div></div></div>"
            )


    # ── Prediction Markets ─────────────────────────────────────────────────────
    st.markdown(
        "<div class='section-title' style='margin-top:28px;'>Prediction Market Intelligence</div>"
        "<div style='color:#7A9BBE;font-size:0.80rem;margin-bottom:18px;'>"
        "Live crowd-sourced probability estimates across housing policy, macro, and elections · "
        "Refreshes every 5 min</div>",
        unsafe_allow_html=True,
    )

    def _prob_color(p):
        if p is None: return "#7A9BBE"
        return "#FF4B4B" if p >= 60 else ("#FFA500" if p >= 35 else "#21C55D")

    def _prob_bar(p, color):
        pct = int(p) if p is not None else 0
        return (
            f"<div style='background:#1B3150;border-radius:3px;height:5px;margin-top:5px;'>"
            f"<div style='background:{color};width:{pct}%;height:5px;border-radius:3px;'></div></div>"
        )

    def _source_header(label, url, note=""):
        return (
            f"<div style='display:flex;align-items:center;gap:10px;margin:22px 0 10px;'>"
            f"<span style='color:#E8EDF5;font-weight:700;font-size:0.95rem;'>{label}</span>"
            f"<a href='{url}' target='_blank' style='color:#4A90D9;font-size:0.78rem;'>↗ {url.split('//')[1].split('/')[0]}</a>"
            f"{'<span style=\"color:#7A9BBE;font-size:0.76rem;\">· ' + note + '</span>' if note else ''}"
            f"</div>"
        )

    def _market_card(question, prob, end_date, vol_label, url, sub_label="YES implied prob"):
        color = _prob_color(prob)
        bar   = _prob_bar(prob, color)
        prob_display = f"{prob:.1f}%" if prob is not None else "N/A"
        vol_str = vol_label or "—"
        end_str = end_date or "—"
        return (
            f"<div class='intel-card' style='padding:11px 15px;margin-bottom:7px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:flex-start;gap:14px;'>"
            f"<div style='flex:1;'>"
            f"<a href='{url}' target='_blank' style='color:#C8D8EE;font-size:0.87rem;"
            f"font-weight:600;text-decoration:none;line-height:1.4;'>{question}</a>"
            f"{bar}"
            f"<div style='color:#7A9BBE;font-size:0.74rem;margin-top:4px;'>"
            f"Closes: {end_str} &nbsp;·&nbsp; {vol_str}</div>"
            f"</div>"
            f"<div style='text-align:right;white-space:nowrap;'>"
            f"<div style='font-size:1.35rem;font-weight:800;color:{color};'>{prob_display}</div>"
            f"<div style='color:#7A9BBE;font-size:0.70rem;margin-top:1px;'>{sub_label}</div>"
            f"</div></div></div>"
        )

    # ── Manifold Markets ───────────────────────────────────────────────────────
    st.markdown(
        _source_header("Manifold Markets", "https://manifold.markets",
                       "community prediction · housing / macro / Fed"),
        unsafe_allow_html=True,
    )
    manifold_data = fetch_manifold_odds()
    if not manifold_data:
        st.info("Manifold Markets unreachable or no relevant open markets found.")
    else:
        for mkt in manifold_data:
            traders = mkt.get("traders", 0)
            vol_label = f"Vol: M${mkt['volume']:,} · {traders} traders"
            cat_chip = (
                f"<span style='background:#0F2035;color:#7A9BBE;font-size:0.70rem;"
                f"padding:1px 6px;border-radius:3px;margin-right:6px;'>{mkt['category']}</span>"
            )
            card = _market_card(
                cat_chip + mkt["question"], mkt["prob"],
                mkt["end_date"], vol_label, mkt["url"],
            )
            st.markdown(card, unsafe_allow_html=True)

    # ── PredictIt ─────────────────────────────────────────────────────────────
    st.markdown(
        _source_header("PredictIt", "https://www.predictit.org",
                       "elections · congressional control · governor races"),
        unsafe_allow_html=True,
    )
    predictit_data = fetch_predictit_odds()
    if not predictit_data:
        st.info("PredictIt unreachable or no matching markets found.")
    else:
        for mkt in predictit_data:
            st.markdown(
                f"<div class='intel-card' style='padding:11px 15px;margin-bottom:7px;'>"
                f"<a href='{mkt['url']}' target='_blank' style='color:#C8D8EE;font-size:0.87rem;"
                f"font-weight:600;text-decoration:none;'>{mkt['question']}</a>",
                unsafe_allow_html=True,
            )
            cols = st.columns(min(len(mkt["contracts"]), 4))
            for col, c in zip(cols, mkt["contracts"]):
                color = _prob_color(c["prob"])
                prob_str = f"{c['prob']:.0f}%" if c["prob"] is not None else "—"
                col.markdown(
                    f"<div style='background:#0A1929;border:1px solid #1B3150;border-radius:6px;"
                    f"padding:8px 10px;text-align:center;'>"
                    f"<div style='font-size:1.15rem;font-weight:800;color:{color};'>{prob_str}</div>"
                    f"<div style='color:#7A9BBE;font-size:0.72rem;margin-top:2px;'>{c['name'][:22]}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
            st.markdown("</div>", unsafe_allow_html=True)

    # ── Polymarket ────────────────────────────────────────────────────────────
    st.markdown(
        _source_header("Polymarket", "https://polymarket.com",
                       "high-liquidity · housing markets appear when ballot measures gain traction"),
        unsafe_allow_html=True,
    )
    poly_markets = fetch_polymarket_odds()
    if not poly_markets:
        st.markdown(
            "<div style='color:#7A9BBE;font-size:0.83rem;padding:10px 0;'>"
            "No active Polymarket markets matched housing/macro keywords right now. "
            "Polymarket covers these when ballot measures gain national traction — "
            "check back closer to November 2026.</div>",
            unsafe_allow_html=True,
        )
    else:
        for mkt in poly_markets:
            vol_label = f"Vol: ${mkt['volume']:,}" if mkt["volume"] else "—"
            st.markdown(
                _market_card(mkt["question"], mkt["prob"], mkt["end_date"],
                             vol_label, mkt["url"]),
                unsafe_allow_html=True,
            )

    # ── Metaculus link card ────────────────────────────────────────────────────
    st.markdown(
        "<div style='margin-top:18px;'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='intel-card' style='padding:12px 16px;'>"
        "<div style='display:flex;justify-content:space-between;align-items:center;'>"
        "<div>"
        "<div style='color:#E8EDF5;font-weight:700;font-size:0.90rem;margin-bottom:4px;'>Metaculus</div>"
        "<div style='color:#7A9BBE;font-size:0.80rem;'>"
        "Researcher-grade forecasting with structured resolution criteria · "
        "Covers housing policy, Fed decisions, and macroeconomic questions · "
        "Requires free account for API access.</div>"
        "</div>"
        "<a href='https://www.metaculus.com/questions/?search=housing' target='_blank' "
        "style='color:#4A90D9;font-size:0.82rem;white-space:nowrap;margin-left:16px;'>Browse ↗</a>"
        "</div></div>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — LIVE NEWS TERMINAL
# ══════════════════════════════════════════════════════════════════════════════

with tab4:
    st.markdown(
        "<div class='section-title'>Live Regulatory News Terminal</div>"
        "<div style='color:#7A9BBE;font-size:0.80rem;margin-bottom:18px;'>"
        "Real-time headlines from Google News · Sorted by most recent · Click 🔍 to open Audit Panel</div>",
        unsafe_allow_html=True,
    )

    # ── Live scraped news ──────────────────────────────────────────────────────
    col_live_hdr, col_live_refresh = st.columns([6, 1])
    with col_live_hdr:
        st.markdown(
            "<div style='display:flex;align-items:center;gap:10px;margin-bottom:12px;'>"
            "<span style='background:#FF4B4B;color:#fff;font-size:0.68rem;font-weight:800;"
            "padding:3px 8px;border-radius:4px;letter-spacing:0.08em;'>● LIVE</span>"
            "<span style='color:#7A9BBE;font-size:0.80rem;'>Google News · refreshes every 5 min</span>"
            "</div>",
            unsafe_allow_html=True,
        )
    with col_live_refresh:
        if st.button("↻ Refresh", key="refresh_live_news"):
            st.cache_data.clear()
            st.rerun()

    live_df = fetch_live_news()

    # Filter live news by selected tickers if a specific filter is active
    selected_tickers = st.session_state.get("_sidebar_tickers", ALL_TICKERS)
    if live_df.empty:
        st.markdown(
            "<div style='color:#7A9BBE;font-size:0.84rem;padding:12px 0 20px 0;'>"
            "⚠ Could not fetch live news (check your internet connection).</div>",
            unsafe_allow_html=True,
        )
    else:
        # Filter to selected tickers when user has narrowed the filter
        active_tickers = st.session_state.get("_sidebar_tickers", ALL_TICKERS)
        if set(active_tickers) != set(ALL_TICKERS):
            ticker_set = set(active_tickers)
            live_df = live_df[
                live_df["tickers_exposed"].apply(
                    lambda c: bool(ticker_set & set(str(c).split(","))) if c else True
                )
            ]

        for _, lrow in live_df.iterrows():
            ticker_str = str(lrow["tickers_exposed"])
            chips_html = ticker_chips(ticker_str) if ticker_str else ""
            source_url = lrow.get("url", "")
            link_html = (
                f"<a href='{source_url}' target='_blank' "
                f"style='color:#C9A84C;font-size:0.75rem;text-decoration:none;margin-left:8px;'>↗ Source</a>"
                if source_url else ""
            )
            st.html(
                f"<div class='news-card' style='border-left:3px solid #1E90FF;'>"
                f"<div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;'>"
                f"<span style='color:#C9A84C;font-size:0.72rem;text-transform:uppercase;"
                f"font-weight:700;letter-spacing:0.07em;'>{lrow['source_name']}</span>"
                f"<span style='color:#7A9BBE;font-size:0.72rem;'>{lrow['published']}</span>"
                f"</div>"
                f"<div style='font-size:0.98rem;font-weight:700;color:#E8EDF5;"
                f"line-height:1.45;margin-bottom:8px;'>{lrow['headline']}{link_html}</div>"
                f"<div style='font-size:0.84rem;color:#A8BDD4;line-height:1.6;margin-bottom:10px;'>"
                f"{lrow['summary']}</div>"
                f"<div style='display:flex;gap:8px;flex-wrap:wrap;align-items:center;'>"
                f"<span style='background:#0B1E33;color:#1E90FF;padding:3px 9px;border-radius:20px;"
                f"font-size:0.72rem;font-weight:700;border:1px solid #1E3A5F;'>LIVE</span>"
                f"{chips_html}"
                f"</div>"
                f"</div>"
            )

    st.markdown(
        "<hr style='border-color:#1B3150;margin:24px 0 18px 0;'>"
        "<div style='color:#7A9BBE;font-size:0.78rem;margin-bottom:14px;'>"
        "▼ &nbsp;INTELLIGENCE DATABASE — verified entries with audit trails</div>",
        unsafe_allow_html=True,
    )

    # ── DB intelligence entries ────────────────────────────────────────────────
    if filtered_df.empty:
        st.info("No news items match the current filter.")
    else:
        for _, row in filtered_df.sort_values("last_updated", ascending=False).iterrows():
            card_class = {
                "Critical":   "news-card critical",
                "Moderate":   "news-card moderate",
                "Low/Stable": "news-card stable",
            }.get(row["portfolio_risk_impact"], "news-card")

            col_card, col_btn = st.columns([16, 1])
            with col_card:
                summary_trunc = str(row["summary_insight"])[:320]
                if len(str(row["summary_insight"])) > 320:
                    summary_trunc += "&#8230;"
                st.html(
                    f'<div class="{card_class}">'
                    f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;">'
                    f'<span style="color:#C9A84C;font-size:0.72rem;text-transform:uppercase;font-weight:700;letter-spacing:0.07em;">{row["source_name"]}</span>'
                    f'<span style="color:#7A9BBE;font-size:0.72rem;">{row["last_updated"]}</span>'
                    f'</div>'
                    f'<div style="font-size:1.0rem;font-weight:700;color:#E8EDF5;line-height:1.45;margin-bottom:10px;">{row["headline"]}</div>'
                    f'<div style="font-size:0.86rem;color:#A8BDD4;line-height:1.65;margin-bottom:12px;">{summary_trunc}</div>'
                    f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">'
                    f'{sent_badge(row["sentiment_score"])}'
                    f'{risk_badge(row["portfolio_risk_impact"])}'
                    f'{ticker_chips(row["tickers_exposed"])}'
                    f'<span style="background:#0C1929;color:#7A9BBE;padding:3px 10px;border-radius:20px;font-size:0.75rem;">'
                    f'{row["state_code"]} &middot; {row["metro_market"]}'
                    f'</span>'
                    f'</div>'
                    f'</div>'
                )
            with col_btn:
                st.markdown("<div style='height:52px;'></div>", unsafe_allow_html=True)
                if st.button("🔍", key=f"a4_{row['id']}", help="Open audit trail"):
                    st.session_state["audit_row_id"] = int(row["id"])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — MARKET-BY-MARKET ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

with tab5:
    st.markdown("<div class='section-title'>Market-by-Market Legislative Analysis</div>", unsafe_allow_html=True)
    st.markdown(
        "<div style='color:#7A9BBE;font-size:0.82rem;margin-bottom:18px;'>"
        "Comprehensive analysis per market with sentiment assessment, legislative context, "
        "portfolio impact, and primary source citations.</div>",
        unsafe_allow_html=True,
    )

    # Group by state for organized display
    if df_all.empty:
        st.warning("No data loaded.")
    else:
        ma_search = st.text_input(
            "Search markets...",
            placeholder="e.g. California, CSR, Algorithmic, Critical",
            label_visibility="collapsed",
        )

        ma_df = df_all.copy()
        if ma_search.strip():
            q = ma_search.strip().lower()
            mask = (
                ma_df["metro_market"].str.lower().str.contains(q, na=False) |
                ma_df["state_code"].str.lower().str.contains(q, na=False) |
                ma_df["tickers_exposed"].str.lower().str.contains(q, na=False) |
                ma_df["category"].str.lower().str.contains(q, na=False) |
                ma_df["portfolio_risk_impact"].str.lower().str.contains(q, na=False) |
                ma_df["summary_insight"].str.lower().str.contains(q, na=False)
            )
            ma_df = ma_df[mask]

        if ma_df.empty:
            st.info(f"No results for '{ma_search}'")
        else:
            # Sort: Critical first, then by state
            risk_order = {"Critical": 0, "Moderate": 1, "Low/Stable": 2}
            ma_df["_risk_ord"] = ma_df["portfolio_risk_impact"].map(risk_order).fillna(3)
            ma_df = ma_df.sort_values(["_risk_ord", "state_code", "metro_market"])

            states_in_df = ma_df["state_code"].unique()

            for state in states_in_df:
                state_rows = ma_df[ma_df["state_code"] == state]
                avg_sent = state_rows["sentiment_score"].mean()
                risk_summary = state_rows["portfolio_risk_impact"].value_counts().to_dict()
                risk_display = " · ".join(
                    f"<span style='color:{RISK_COLORS.get(k, '#7A9BBE')};font-weight:700;'>{v} {k}</span>"
                    for k, v in risk_summary.items()
                )
                sent_clr = sentiment_color(avg_sent)

                st.markdown(
                    f"<div style='display:flex;align-items:center;gap:12px;margin:20px 0 10px 0;"
                    f"border-top:1px solid #1B3150;padding-top:16px;'>"
                    f"<span style='color:#C9A84C;font-size:1.3rem;font-weight:800;'>{state}</span>"
                    f"<span style='color:#D4DCE8;font-size:0.85rem;'>{len(state_rows)} market{'s' if len(state_rows)>1 else ''}</span>"
                    f"<span style='color:{sent_clr};font-size:0.85rem;font-weight:700;'>Avg Sentiment: {avg_sent:+.2f}</span>"
                    f"<span style='font-size:0.82rem;'>{risk_display}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                for _, row in state_rows.iterrows():
                    r_color = RISK_COLORS.get(row["portfolio_risk_impact"], "#7A9BBE")
                    s_color = sentiment_color(row["sentiment_score"])

                    # Sentiment gauge (simple visual bar)
                    gauge_pct = int((row["sentiment_score"] + 1.0) / 2.0 * 100)
                    gauge_color = s_color

                    source_link = (
                        f'<a href="{row["source_url"]}" target="_blank" '
                        f'style="color:#C9A84C;font-size:0.78rem;font-weight:600;text-decoration:none;">'
                        f'&#128279; View Primary Source</a>'
                        if row["source_url"] else ""
                    )
                    card_html = (
                        f'<div class="market-card">'
                        f'<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;">'
                        f'<div>'
                        f'<div style="color:#E8EDF5;font-size:1.0rem;font-weight:700;margin-bottom:4px;">{row["metro_market"]}</div>'
                        f'<div style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:8px;">'
                        f'{sol_badge(row["state_of_law"])}'
                        f'{risk_badge(row["portfolio_risk_impact"])}'
                        f'<span style="color:#7A9BBE;font-size:0.78rem;">{row["category"]}</span>'
                        f'</div>'
                        f'<div>{ticker_chips(row["tickers_exposed"])}</div>'
                        f'</div>'
                        f'<div style="text-align:right;min-width:140px;">'
                        f'<div style="color:#7A9BBE;font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Sentiment Score</div>'
                        f'<div style="font-size:1.6rem;font-weight:700;color:{s_color};">{row["sentiment_score"]:+.2f}</div>'
                        f'<div style="background:#1B3150;border-radius:99px;height:6px;margin-top:6px;width:130px;">'
                        f'<div style="background:{gauge_color};border-radius:99px;height:6px;width:{gauge_pct}%;"></div>'
                        f'</div>'
                        f'<div style="display:flex;justify-content:space-between;color:#7A9BBE;font-size:0.68rem;margin-top:2px;">'
                        f'<span>&#8722;1.0</span><span>+1.0</span>'
                        f'</div>'
                        f'</div>'
                        f'</div>'
                        f'<div style="color:#C8D8EE;font-size:0.87rem;line-height:1.70;margin-bottom:14px;">{row["summary_insight"]}</div>'
                        f'<div style="background:#060D1A;border-left:3px solid #C9A84C;border-radius:0 6px 6px 0;padding:12px 16px;margin-bottom:14px;">'
                        f'<div style="color:#7A9BBE;font-size:0.72rem;text-transform:uppercase;font-weight:700;letter-spacing:0.06em;margin-bottom:6px;">Verbatim Legislative Text</div>'
                        f'<div style="color:#B8CCE4;font-size:0.84rem;font-style:italic;line-height:1.7;">'
                        f'&#8220;{row["exact_text_quote"]}&#8221;'
                        f'</div>'
                        f'</div>'
                        f'<div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;">'
                        f'<div style="font-size:0.78rem;">'
                        f'<span style="color:#7A9BBE;">Source: </span>'
                        f'<span style="color:#C9A84C;font-weight:600;">{row["source_name"]}</span>'
                        f'</div>'
                        f'<div style="display:flex;gap:12px;align-items:center;">'
                        f'<span style="color:#7A9BBE;font-size:0.75rem;">Updated: {row["last_updated"][:10]}</span>'
                        f'{source_link}'
                        f'</div>'
                        f'</div>'
                        f'</div>'
                    )
                    st.html(card_html)

                    mc1c, mc2c = st.columns([12, 1])
                    with mc2c:
                        if st.button("Audit", key=f"a5_{row['id']}"):
                            st.session_state["audit_row_id"] = int(row["id"])


# ══════════════════════════════════════════════════════════════════════════════
# AUDIT ENGINE — Sidebar
# ══════════════════════════════════════════════════════════════════════════════

def render_audit_panel(df: pd.DataFrame) -> None:
    audit_id = st.session_state.get("audit_row_id")
    if audit_id is None:
        return
    row_matches = df[df["id"] == audit_id]
    if row_matches.empty:
        st.sidebar.warning("Audit target not found.")
        return
    row = row_matches.iloc[0]
    r_color = RISK_COLORS.get(row["portfolio_risk_impact"], "#7A9BBE")
    s_color = sentiment_color(row["sentiment_score"])

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "<div style='color:#C9A84C;font-weight:700;font-size:0.9rem;"
        "border-bottom:1px solid #1B3150;padding-bottom:8px;margin-bottom:12px;'>"
        "🔍 Audit Verification Panel</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<div style='color:#7A9BBE;font-size:0.72rem;text-transform:uppercase;"
        "font-weight:700;letter-spacing:0.06em;margin-bottom:2px;'>Verified Source</div>"
        f"<div style='color:#E8EDF5;font-weight:600;font-size:0.88rem;margin-bottom:10px;'>"
        f"{row['source_name']}</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<div style='color:#7A9BBE;font-size:0.72rem;text-transform:uppercase;"
        "font-weight:700;letter-spacing:0.06em;margin-bottom:4px;'>Live Source Link</div>",
        unsafe_allow_html=True,
    )
    if row["source_url"]:
        st.sidebar.markdown(f"[🔗 Open Primary Source →]({row['source_url']})")
    else:
        st.sidebar.markdown("_No URL recorded_")

    st.sidebar.markdown(
        "<div style='color:#7A9BBE;font-size:0.72rem;text-transform:uppercase;"
        "font-weight:700;letter-spacing:0.06em;margin-top:10px;margin-bottom:2px;'>"
        "Verification Timestamp</div>"
        f"<code style='color:#C9A84C;font-size:0.82rem;'>{row['last_updated']}</code>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"<div style='background:#060D1A;border:1px solid #1B3150;border-radius:8px;"
        f"padding:12px;font-size:0.82rem;margin:10px 0;'>"
        f"<div style='margin-bottom:4px;'><span style='color:#7A9BBE;'>Market: </span>"
        f"<span style='color:#E8EDF5;font-weight:600;'>{row['metro_market']} ({row['state_code']})</span></div>"
        f"<div style='margin-bottom:4px;'><span style='color:#7A9BBE;'>Tickers: </span>"
        f"<span style='color:#C9A84C;font-weight:700;'>{row['tickers_exposed']}</span></div>"
        f"<div style='margin-bottom:4px;'><span style='color:#7A9BBE;'>Category: </span>"
        f"<span style='color:#C8D8EE;'>{row['category']}</span></div>"
        f"<div style='margin-bottom:4px;'><span style='color:#7A9BBE;'>Status: </span>"
        f"<span style='color:{SOL_COLORS.get(row['state_of_law'], '#7A9BBE')};font-weight:600;'>"
        f"{row['state_of_law']}</span></div>"
        f"<div style='margin-bottom:4px;'><span style='color:#7A9BBE;'>Risk: </span>"
        f"<span style='color:{r_color};font-weight:700;'>{row['portfolio_risk_impact']}</span></div>"
        f"<div><span style='color:#7A9BBE;'>Sentiment: </span>"
        f"<span style='color:{s_color};font-weight:700;'>{row['sentiment_score']:+.3f}</span></div>"
        f"</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<div style='color:#7A9BBE;font-size:0.72rem;text-transform:uppercase;"
        "font-weight:700;letter-spacing:0.06em;margin-bottom:4px;'>"
        "Verbatim Source Text Used by AI</div>",
        unsafe_allow_html=True,
    )
    quote = row["exact_text_quote"] if row["exact_text_quote"] else "_No verbatim extract recorded._"
    st.sidebar.markdown(
        f"<div class='audit-quote'>&ldquo;{quote}&rdquo;</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<div style='color:#7A9BBE;font-size:0.72rem;text-transform:uppercase;"
        "font-weight:700;letter-spacing:0.06em;margin:8px 0 2px 0;'>Processed Headline</div>"
        f"<div style='color:#C8D8EE;font-size:0.84rem;font-style:italic;line-height:1.6;'>"
        f"{row['headline']}</div>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown("<div style='margin-top:14px;'></div>", unsafe_allow_html=True)
    if st.sidebar.button("✕ Close Audit Panel", key="clear_audit"):
        del st.session_state["audit_row_id"]
        st.rerun()


render_audit_panel(df_all)


# ══════════════════════════════════════════════════════════════════════════════
# AI CHAT OVERLAY — floating widget injected into parent DOM
# Calls Anthropic API directly from the browser using the
# anthropic-dangerous-direct-browser-access header (CORS-enabled by Anthropic).
# API key is stored only in the user's browser localStorage — never sent to
# the Python/Streamlit server.
# ══════════════════════════════════════════════════════════════════════════════

components.html("""
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script>
(function() {
    var pd = window.parent.document;
    if (pd.getElementById('reit-ai-fab')) return; // already injected

    /* ── Styles ── */
    var style = pd.createElement('style');
    style.textContent = [
        "@keyframes reit-glow{0%,100%{box-shadow:0 0 8px 3px rgba(0,255,136,.75),0 4px 24px rgba(0,0,0,.5)}50%{box-shadow:0 0 26px 10px rgba(0,255,136,.35),0 4px 24px rgba(0,0,0,.5)}}",
        "#reit-ai-fab{position:fixed;bottom:28px;right:28px;z-index:100000;width:62px;height:62px;border-radius:50%;border:2.5px solid rgba(0,255,136,.65);background:linear-gradient(135deg,#00FF88 0%,#00BB55 100%);cursor:pointer;font-size:27px;display:flex;align-items:center;justify-content:center;animation:reit-glow 2.6s ease-in-out infinite;transition:transform .2s;font-family:sans-serif;line-height:1;outline:none;}",
        "#reit-ai-fab:hover{transform:scale(1.13);}",
        "#reit-chat-panel{position:fixed;bottom:104px;right:28px;z-index:99999;width:400px;max-height:570px;background:#F2F5F9;border-radius:20px;box-shadow:0 14px 55px rgba(0,0,0,.45),0 0 0 1px rgba(0,0,0,.08);display:none;flex-direction:column;overflow:hidden;font-family:'Inter','Segoe UI',sans-serif;}",
        "#reit-chat-panel.reit-open{display:flex;}",
        ".reit-hdr{background:#0F1E35;padding:14px 18px;display:flex;align-items:center;gap:11px;flex-shrink:0;}",
        ".reit-hdr-icon{font-size:1.5rem;line-height:1;}",
        ".reit-hdr-title{color:#fff;font-size:.95rem;font-weight:700;}",
        ".reit-hdr-sub{color:#7A9BBE;font-size:.73rem;margin-top:1px;}",
        ".reit-live{margin-left:auto;background:#001A0D;color:#00FF88;border:1px solid rgba(0,255,136,.35);border-radius:20px;padding:3px 9px;font-size:.68rem;font-weight:700;letter-spacing:.07em;}",
        ".reit-close{background:none;border:none;color:#7A9BBE;font-size:18px;cursor:pointer;padding:2px 4px;line-height:1;margin-left:8px;}",
        ".reit-close:hover{color:#fff;}",
        ".reit-msgs{flex:1;overflow-y:auto;padding:14px 14px 6px 14px;display:flex;flex-direction:column;gap:10px;background:#F2F5F9;}",
        ".reit-bubble{max-width:86%;border-radius:14px;padding:10px 14px;font-size:.87rem;line-height:1.57;word-break:break-word;}",
        ".reit-bubble.user{background:#0F1E35;color:#E8F0FA;margin-left:auto;border-bottom-right-radius:4px;}",
        ".reit-bubble.ai{background:#fff;color:#1A202C;border:1px solid #E2E8F0;margin-right:auto;border-bottom-left-radius:4px;box-shadow:0 1px 4px rgba(0,0,0,.06);}",
        ".reit-bubble.typing{background:#fff;color:#9AABB8;border:1px solid #E2E8F0;margin-right:auto;font-style:italic;font-size:.82rem;}",
        ".reit-welcome{text-align:center;color:#718096;font-size:.82rem;padding:20px 16px 8px;line-height:1.6;}",
        ".reit-form{padding:12px 14px 14px;background:#fff;border-top:1px solid #E8ECF0;flex-shrink:0;}",
        ".reit-api-wrap{position:relative;margin-bottom:9px;}",
        ".reit-api-in{width:100%;padding:8px 12px;border:1.5px solid #D1D9E2;border-radius:10px;font-size:.80rem;color:#1A202C;background:#F8FAFB;box-sizing:border-box;outline:none;}",
        ".reit-api-in:focus{border-color:#00BB55;}",
        ".reit-row{display:flex;gap:8px;}",
        ".reit-msg-in{flex:1;padding:9px 14px;border:1.5px solid #D1D9E2;border-radius:10px;font-size:.88rem;color:#1A202C;background:#fff;outline:none;}",
        ".reit-msg-in:focus{border-color:#00BB55;box-shadow:0 0 0 2px rgba(0,187,85,.12);}",
        ".reit-send{padding:9px 18px;background:#00BB55;color:#fff;border:none;border-radius:10px;cursor:pointer;font-size:.88rem;font-weight:600;flex-shrink:0;transition:background .15s;}",
        ".reit-send:hover{background:#009944;}",
        ".reit-send:disabled{background:#A8D8B8;cursor:not-allowed;}",
        ".reit-clear{display:block;width:100%;margin-top:8px;padding:5px;background:none;border:none;color:#A0AEC0;font-size:.75rem;cursor:pointer;text-align:center;}",
        ".reit-clear:hover{color:#718096;}",
        ".reit-bubble.ai h1,.reit-bubble.ai h2,.reit-bubble.ai h3{color:#0F1E35;font-size:.93rem;font-weight:700;margin:.7em 0 .3em;border-bottom:1px solid #E2E8F0;padding-bottom:3px;}",
        ".reit-bubble.ai h3{border-bottom:none;font-size:.88rem;color:#2D3748;}",
        ".reit-bubble.ai p{margin:.35em 0;font-size:.87rem;color:#1A202C;line-height:1.58;}",
        ".reit-bubble.ai ul,.reit-bubble.ai ol{margin:.35em 0 .35em 1.1em;padding:0;font-size:.87rem;color:#1A202C;}",
        ".reit-bubble.ai li{margin:.18em 0;}",
        ".reit-bubble.ai strong{font-weight:700;color:#0F1E35;}",
        ".reit-bubble.ai code{background:#EEF2F7;color:#2D3748;padding:1px 5px;border-radius:4px;font-size:.82rem;font-family:monospace;}",
        ".reit-bubble.ai table{border-collapse:collapse;width:100%;margin:.5em 0;font-size:.82rem;}",
        ".reit-bubble.ai th{background:#E8ECF2;color:#0F1E35;padding:5px 10px;text-align:left;font-weight:700;border:1px solid #D1D9E2;}",
        ".reit-bubble.ai td{padding:5px 10px;border:1px solid #E2E8F0;color:#2D3748;vertical-align:top;}",
        ".reit-bubble.ai tr:nth-child(even) td{background:#F7F9FC;}"
    ].join('');
    pd.head.appendChild(style);

    /* ── State ── */
    var history = [];
    var savedKey = '';
    try { savedKey = localStorage.getItem('reit_ai_key') || ''; } catch(e){}

    /* ── FAB ── */
    var fab = pd.createElement('button');
    fab.id = 'reit-ai-fab';
    fab.title = 'AI Research Assistant';
    fab.textContent = '🤖'; // 🤖
    pd.body.appendChild(fab);

    /* ── Panel markup ── */
    var panel = pd.createElement('div');
    panel.id = 'reit-chat-panel';
    panel.innerHTML =
        '<div class="reit-hdr">' +
          '<span class="reit-hdr-icon">🤖</span>' +
          '<div><div class="reit-hdr-title">AI Research Assistant</div>' +
          '<div class="reit-hdr-sub">REIT Legislative Intelligence</div></div>' +
          '<span class="reit-live">LIVE</span>' +
          '<button class="reit-close" id="reit-close" title="Close">✕</button>' +
        '</div>' +
        '<div class="reit-msgs" id="reit-msgs">' +
          '<div class="reit-welcome">Ask me about rent control exposure, ballot initiatives,<br>NOI impact, or specific ticker risk profiles.</div>' +
        '</div>' +
        '<div class="reit-form">' +
          '<div class="reit-api-wrap">' +
            '<input class="reit-api-in" id="reit-api-key" type="password" placeholder="🔑 Anthropic API key (sk-ant-...)" />' +
          '</div>' +
          '<div class="reit-row">' +
            '<input class="reit-msg-in" id="reit-msg-in" type="text" placeholder="Ask about REIT exposure…" />' +
            '<button class="reit-send" id="reit-send">Send</button>' +
          '</div>' +
          '<button class="reit-clear" id="reit-clear-btn">Clear conversation</button>' +
        '</div>';
    pd.body.appendChild(panel);

    if (savedKey) pd.getElementById('reit-api-key').value = savedKey;

    /* ── Toggle open/close ── */
    fab.onclick = function() { panel.classList.toggle('reit-open'); };
    pd.getElementById('reit-close').onclick = function() { panel.classList.remove('reit-open'); };

    /* ── Add bubble ── */
    function bubble(role, text) {
        var msgs = pd.getElementById('reit-msgs');
        var d = pd.createElement('div');
        d.className = 'reit-bubble ' + role;
        if (role === 'ai' && window.marked) {
            d.innerHTML = window.marked.parse(text);
        } else {
            d.textContent = text;
        }
        msgs.appendChild(d);
        msgs.scrollTop = msgs.scrollHeight;
        return d;
    }

    /* ── Clear ── */
    pd.getElementById('reit-clear-btn').onclick = function() {
        history = [];
        var msgs = pd.getElementById('reit-msgs');
        msgs.innerHTML = '<div class="reit-welcome">Conversation cleared. Ask me anything about REIT legislative risk.</div>';
    };

    /* ── Send ── */
    function send() {
        var keyEl = pd.getElementById('reit-api-key');
        var msgEl = pd.getElementById('reit-msg-in');
        var sendBtn = pd.getElementById('reit-send');
        var key = keyEl.value.trim();
        var msg = msgEl.value.trim();
        if (!msg) return;
        if (!key) { keyEl.focus(); keyEl.style.borderColor = '#E53E3E'; setTimeout(function(){ keyEl.style.borderColor=''; }, 1500); return; }
        try { localStorage.setItem('reit_ai_key', key); } catch(e) {}

        msgEl.value = '';
        history.push({ role: 'user', content: msg });
        bubble('user', msg);
        var typing = bubble('typing', 'Analyzing…');
        sendBtn.disabled = true;

        var sys = 'You are an expert REIT analyst specializing in US legislative and regulatory risk. ' +
            'You cover 9 tracked tickers: AVB (AvalonBay), EQR (Equity Residential), ESS (Essex Property), ' +
            'MAA (Mid-America Apartment), CPT (Camden Property), UDR, INVH (Invitation Homes), ' +
            'AMH (American Homes 4 Rent), CSR (Centerspace - upper Midwest multifamily). ' +
            'CenterSquare Investment Management holds: UDR $282M, CPT $258M, INVH $185M, AMH $166M, MAA $75M, EQR $68M, ESS $52M. ' +
            'Be concise, analytical, and use specific figures where available.';

        fetch('https://api.anthropic.com/v1/messages', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'x-api-key': key,
                'anthropic-version': '2023-06-01',
                'anthropic-dangerous-direct-browser-access': 'true'
            },
            body: JSON.stringify({
                model: 'claude-haiku-4-5-20251001',
                max_tokens: 700,
                system: sys,
                messages: history.slice(-8)
            })
        })
        .then(function(r) { return r.json(); })
        .then(function(data) {
            typing.remove();
            sendBtn.disabled = false;
            if (data.error) {
                bubble('ai', 'Error: ' + (data.error.message || JSON.stringify(data.error)));
            } else {
                var text = data.content && data.content[0] ? data.content[0].text : '(no response)';
                history.push({ role: 'assistant', content: text });
                // Wait for marked.js if still loading from CDN
                if (window.marked) {
                    bubble('ai', text);
                } else {
                    var wait = setInterval(function() {
                        if (window.marked) { clearInterval(wait); bubble('ai', text); }
                    }, 50);
                    setTimeout(function() { clearInterval(wait); bubble('ai', text); }, 3000);
                }
            }
        })
        .catch(function(err) {
            typing.remove();
            sendBtn.disabled = false;
            bubble('ai', 'Network error: ' + err.message + '. Make sure your API key is valid.');
        });
    }

    pd.getElementById('reit-send').onclick = send;
    pd.getElementById('reit-msg-in').addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    });

})();
</script>
""", height=0)
