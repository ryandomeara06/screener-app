"""
==========================================================
  TERMINAL // Equity Technicals & Valuation Dashboard
==========================================================
A Streamlit app styled after a professional trading terminal.

Currently wired to MOCK DATA so the app is fully functional
out of the box. Swap `fetch_price_history()` and
`fetch_fundamentals()` with a real API (Financial Modeling
Prep, Twelve Data, Finnhub) to go live -- see the
"DATA SOURCE" section near the top for the one place to edit.

Run locally:
    pip install -r requirements.txt
    streamlit run app.py
==========================================================
"""

import numpy as np
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta


# ==========================================================
# PAGE CONFIG + TERMINAL THEME
# ==========================================================
st.set_page_config(
    page_title="TERMINAL // Equity Dashboard",
    page_icon="📟",
    layout="wide",
    initial_sidebar_state="expanded",
)

TERMINAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg-main: #0a0e14;
    --bg-panel: #10151d;
    --bg-panel-alt: #141a24;
    --border-col: #1f2733;
    --text-primary: #e8ecf1;
    --text-secondary: #7d8899;
    --accent-orange: #ff9f0a;
    --accent-green: #00d97e;
    --accent-red: #ff4757;
    --accent-blue: #2196f3;
    --accent-amber: #ffb300;
}

html, body, [class*="css"]  {
    font-family: 'Inter', sans-serif;
    background-color: var(--bg-main);
    color: var(--text-primary);
}

.stApp {
    background-color: var(--bg-main);
}

/* Monospace for numbers / tickers */
.mono {
    font-family: 'IBM Plex Mono', monospace;
}

/* Header bar */
.terminal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 20px;
    background: linear-gradient(180deg, #12161f 0%, #0d1117 100%);
    border: 1px solid var(--border-col);
    border-radius: 4px;
    margin-bottom: 16px;
}
.terminal-header .brand {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 20px;
    font-weight: 700;
    letter-spacing: 2px;
    color: var(--accent-orange);
}
.terminal-header .brand span {
    color: var(--text-secondary);
    font-weight: 400;
    font-size: 12px;
    letter-spacing: 1px;
    display: block;
}
.terminal-header .clock {
    font-family: 'IBM Plex Mono', monospace;
    color: var(--text-secondary);
    font-size: 13px;
    text-align: right;
}

/* Metric cards */
.metric-card {
    background: var(--bg-panel);
    border: 1px solid var(--border-col);
    border-radius: 4px;
    padding: 14px 16px;
    height: 100%;
}
.metric-card .label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    letter-spacing: 1.5px;
    color: var(--text-secondary);
    text-transform: uppercase;
    margin-bottom: 6px;
}
.metric-card .value {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
}
.metric-card .sub {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    margin-top: 4px;
}

.pos { color: var(--accent-green) !important; }
.neg { color: var(--accent-red) !important; }
.neutral { color: var(--accent-amber) !important; }

/* Trend badge */
.badge {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 1px;
    padding: 4px 12px;
    border-radius: 3px;
    text-transform: uppercase;
}
.badge-up { background: rgba(0, 217, 126, 0.12); color: var(--accent-green); border: 1px solid rgba(0, 217, 126, 0.35); }
.badge-down { background: rgba(255, 71, 87, 0.12); color: var(--accent-red); border: 1px solid rgba(255, 71, 87, 0.35); }
.badge-mixed { background: rgba(255, 179, 0, 0.12); color: var(--accent-amber); border: 1px solid rgba(255, 179, 0, 0.35); }

/* Section divider labels */
.section-label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    letter-spacing: 2px;
    color: var(--text-secondary);
    text-transform: uppercase;
    border-bottom: 1px solid var(--border-col);
    padding-bottom: 6px;
    margin: 18px 0 10px 0;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background-color: var(--bg-panel);
    border-right: 1px solid var(--border-col);
}

/* Data table tweaks */
.stDataFrame { font-family: 'IBM Plex Mono', monospace; }

/* Hide default streamlit chrome */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}
</style>
"""

st.markdown(TERMINAL_CSS, unsafe_allow_html=True)

PLOTLY_LAYOUT = dict(
    paper_bgcolor="#10151d",
    plot_bgcolor="#10151d",
    font=dict(family="IBM Plex Mono, monospace", color="#e8ecf1", size=12),
    xaxis=dict(gridcolor="#1f2733", zerolinecolor="#1f2733"),
    yaxis=dict(gridcolor="#1f2733", zerolinecolor="#1f2733"),
    legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", y=1.02, x=0),
    margin=dict(l=10, r=10, t=30, b=10),
)


# ==========================================================
# DATA SOURCE  -- swap this section for a real API later
# ==========================================================
# To go live: replace the bodies of fetch_price_history() and
# fetch_fundamentals() with calls to e.g. Financial Modeling Prep,
# Twelve Data, or Finnhub. Keep the same return shape and every
# calculation below keeps working unchanged.

@st.cache_data(ttl=300)
def fetch_price_history(ticker: str, years: int = 5) -> pd.DataFrame:
    """
    MOCK price history generator (deterministic per-ticker via seed).
    Replace with a real API call, e.g.:

        import requests
        r = requests.get(f"https://api.twelvedata.com/time_series?symbol={ticker}&interval=1day&outputsize=1300&apikey=YOUR_KEY")
        df = pd.DataFrame(r.json()["values"])
        ...
    Must return a DataFrame indexed by date with a "Close" column
    (and ideally Open/High/Low/Volume).
    """
    seed = abs(hash(ticker)) % (2**32)
    rng = np.random.default_rng(seed)

    n_days = years * 252
    dates = pd.bdate_range(end=datetime.today(), periods=n_days)

    start_price = rng.uniform(15, 250)
    drift = rng.uniform(-0.0003, 0.0007)
    vol = rng.uniform(0.015, 0.035)

    returns = rng.normal(drift, vol, n_days)
    # occasional regime shocks for realism
    shock_idx = rng.choice(n_days, size=max(3, n_days // 150), replace=False)
    returns[shock_idx] += rng.normal(0, 0.06, len(shock_idx))

    price = start_price * np.exp(np.cumsum(returns))
    close = pd.Series(price, index=dates)

    daily_range = close * rng.uniform(0.01, 0.03, n_days)
    high = close + daily_range * rng.uniform(0.2, 1.0, n_days)
    low = close - daily_range * rng.uniform(0.2, 1.0, n_days)
    open_ = low + (high - low) * rng.uniform(0.2, 0.8, n_days)
    volume = rng.integers(500_000, 15_000_000, n_days)

    df = pd.DataFrame({
        "Open": open_, "High": high, "Low": low,
        "Close": close, "Volume": volume,
    }, index=dates)
    df.index.name = "Date"
    return df


@st.cache_data(ttl=300)
def fetch_fundamentals(ticker: str, last_price: float) -> dict:
    """
    MOCK fundamentals generator. Replace with a real API call
    returning at least: marketCap, totalRevenue, sector, name.
    """
    seed = abs(hash(ticker + "fund")) % (2**32)
    rng = np.random.default_rng(seed)

    shares_out = rng.uniform(20e6, 2e9)
    market_cap = shares_out * last_price
    revenue = market_cap / rng.uniform(1.5, 12)  # implies a P/S range
    sectors = ["Technology", "Healthcare", "Financials", "Energy",
               "Consumer Discretionary", "Industrials", "Materials"]
    return {
        "name": f"{ticker} Corp.",
        "sector": sectors[int(seed) % len(sectors)],
        "marketCap": market_cap,
        "totalRevenue": revenue,
        "sharesOutstanding": shares_out,
    }


# ==========================================================
# CALCULATION ENGINE  (from the notebook, generalized)
# ==========================================================

def add_moving_averages(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()
    df["MA200"] = df["Close"].rolling(200).mean()
    return df


def compute_trend(df: pd.DataFrame) -> str:
    current_price = df["Close"].iloc[-1]
    ma20, ma50, ma200 = df["MA20"].iloc[-1], df["MA50"].iloc[-1], df["MA200"].iloc[-1]

    if any(pd.isna(x) for x in [ma20, ma50, ma200]):
        return "mixed"

    if current_price > ma20 and current_price > ma50 and current_price > ma200:
        return "up"
    elif current_price < ma20 and current_price < ma50 and current_price < ma200:
        return "down"
    else:
        return "mixed"


def compute_rsi_series(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.fillna(50)  # neutral when undefined
    rsi[(avg_loss == 0) & (avg_gain > 0)] = 100
    rsi[(avg_gain == 0) & (avg_loss > 0)] = 0
    return rsi


def compute_macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def compute_bollinger_bands(close: pd.Series, period=20, num_std=2):
    mid = close.rolling(period).mean()
    std = close.rolling(period).std()
    upper = mid + num_std * std
    lower = mid - num_std * std
    return upper, mid, lower


def compute_price_to_sales(market_cap, revenue):
    if not market_cap or not revenue or revenue == 0:
        return None
    return market_cap / revenue


def fmt_money(x):
    if x is None or pd.isna(x):
        return "N/A"
    if abs(x) >= 1e12:
        return f"${x/1e12:.2f}T"
    if abs(x) >= 1e9:
        return f"${x/1e9:.2f}B"
    if abs(x) >= 1e6:
        return f"${x/1e6:.2f}M"
    return f"${x:,.2f}"


# ==========================================================
# SIDEBAR -- CONTROLS
# ==========================================================
with st.sidebar:
    st.markdown('<div class="section-label">TICKER LOOKUP</div>', unsafe_allow_html=True)
    ticker_input = st.text_input("Symbol", value="AAPL", label_visibility="collapsed").strip().upper()

    st.markdown('<div class="section-label">TIME RANGE</div>', unsafe_allow_html=True)
    range_choice = st.select_slider(
        "Lookback",
        options=["3M", "6M", "1Y", "2Y", "5Y"],
        value="1Y",
        label_visibility="collapsed",
    )

    st.markdown('<div class="section-label">CHART OVERLAY</div>', unsafe_allow_html=True)
    overlay = st.radio(
        "Overlay",
        options=["Moving Averages", "Bollinger Bands", "MACD"],
        label_visibility="collapsed",
    )

    st.markdown('<div class="section-label">DATA SOURCE</div>', unsafe_allow_html=True)
    st.caption("🟡 Mock data mode — swap in a live API in `fetch_price_history()` / `fetch_fundamentals()`.")

    st.markdown("---")
    st.caption("Built for deployment on Streamlit Community Cloud. See `requirements.txt`.")


RANGE_DAYS = {"3M": 63, "6M": 126, "1Y": 252, "2Y": 504, "5Y": 1260}


# ==========================================================
# HEADER
# ==========================================================
now_str = datetime.now().strftime("%a %d %b %Y  %H:%M:%S")
st.markdown(f"""
<div class="terminal-header">
    <div class="brand">TERMINAL <span>EQUITY TECHNICALS &amp; VALUATION</span></div>
    <div class="clock">{now_str}<br>SESSION: MOCK DATA FEED</div>
</div>
""", unsafe_allow_html=True)

if not ticker_input:
    st.stop()

# ==========================================================
# FETCH + COMPUTE
# ==========================================================
raw = fetch_price_history(ticker_input, years=5)
df_full = add_moving_averages(raw)
df_full["RSI"] = compute_rsi_series(df_full["Close"])
df_full["MACD"], df_full["MACD_SIGNAL"], df_full["MACD_HIST"] = compute_macd(df_full["Close"])
df_full["BB_UPPER"], df_full["BB_MID"], df_full["BB_LOWER"] = compute_bollinger_bands(df_full["Close"])

trend = compute_trend(df_full)
current_price = df_full["Close"].iloc[-1]
prev_price = df_full["Close"].iloc[-2]
change = current_price - prev_price
change_pct = (change / prev_price) * 100

fundamentals = fetch_fundamentals(ticker_input, current_price)
ps_ratio = compute_price_to_sales(fundamentals["marketCap"], fundamentals["totalRevenue"])
rsi_now = df_full["RSI"].iloc[-1]

n_days = RANGE_DAYS[range_choice]
df = df_full.tail(n_days).copy()

trend_badge_class = {"up": "badge-up", "down": "badge-down", "mixed": "badge-mixed"}[trend]
trend_label = {"up": "▲ UPTREND", "down": "▼ DOWNTREND", "mixed": "◆ MIXED"}[trend]
price_color_class = "pos" if change >= 0 else "neg"
arrow = "▲" if change >= 0 else "▼"

if rsi_now >= 70:
    rsi_class, rsi_note = "neg", "OVERBOUGHT"
elif rsi_now <= 30:
    rsi_class, rsi_note = "pos", "OVERSOLD"
else:
    rsi_class, rsi_note = "neutral", "NEUTRAL"


# ==========================================================
# TOP METRIC ROW
# ==========================================================
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">{fundamentals['name']} · {ticker_input}</div>
        <div class="value">${current_price:,.2f}</div>
        <div class="sub {price_color_class}">{arrow} {change:+.2f} ({change_pct:+.2f}%)</div>
    </div>""", unsafe_allow_html=True)

with c2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Trend Signal</div>
        <div class="value"><span class="badge {trend_badge_class}">{trend_label}</span></div>
        <div class="sub mono" style="color:var(--text-secondary)">vs MA20/50/200</div>
    </div>""", unsafe_allow_html=True)

with c3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">RSI (14)</div>
        <div class="value">{rsi_now:.1f}</div>
        <div class="sub {rsi_class}">{rsi_note}</div>
    </div>""", unsafe_allow_html=True)

with c4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Market Cap</div>
        <div class="value">{fmt_money(fundamentals['marketCap'])}</div>
        <div class="sub mono" style="color:var(--text-secondary)">{fundamentals['sector']}</div>
    </div>""", unsafe_allow_html=True)

with c5:
    ps_display = f"{ps_ratio:.2f}x" if ps_ratio else "N/A"
    st.markdown(f"""
    <div class="metric-card">
        <div class="label">Price / Sales</div>
        <div class="value">{ps_display}</div>
        <div class="sub mono" style="color:var(--text-secondary)">Rev {fmt_money(fundamentals['totalRevenue'])}</div>
    </div>""", unsafe_allow_html=True)


# ==========================================================
# MAIN CHART -- toggleable overlay
# ==========================================================
st.markdown(f'<div class="section-label">PRICE CHART — {overlay.upper()}</div>', unsafe_allow_html=True)

if overlay == "MACD":
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True,
        row_heights=[0.65, 0.35], vertical_spacing=0.04,
    )
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"], name="Price",
        line=dict(color="#e8ecf1", width=1.6)
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD"], name="MACD",
        line=dict(color="#2196f3", width=1.4)
    ), row=2, col=1)
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MACD_SIGNAL"], name="Signal",
        line=dict(color="#ff9f0a", width=1.4)
    ), row=2, col=1)

    hist_colors = ["#00d97e" if v >= 0 else "#ff4757" for v in df["MACD_HIST"]]
    fig.add_trace(go.Bar(
        x=df.index, y=df["MACD_HIST"], name="Histogram",
        marker_color=hist_colors, opacity=0.6
    ), row=2, col=1)

    fig.update_layout(**PLOTLY_LAYOUT, height=560)
    fig.update_xaxes(gridcolor="#1f2733")
    fig.update_yaxes(gridcolor="#1f2733")

elif overlay == "Bollinger Bands":
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["BB_UPPER"], name="Upper Band",
        line=dict(color="#7d8899", width=1, dash="dot")
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["BB_LOWER"], name="Lower Band",
        line=dict(color="#7d8899", width=1, dash="dot"),
        fill="tonexty", fillcolor="rgba(125,136,153,0.08)"
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["BB_MID"], name="MA20 (Basis)",
        line=dict(color="#ffb300", width=1.2, dash="dash")
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"], name="Price",
        line=dict(color="#e8ecf1", width=1.8)
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=560)

else:  # Moving Averages
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, y=df["Close"], name="Price",
        line=dict(color="#e8ecf1", width=1.8)
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MA20"], name="MA20",
        line=dict(color="#2196f3", width=1.3)
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MA50"], name="MA50",
        line=dict(color="#ff9f0a", width=1.3)
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df["MA200"], name="MA200",
        line=dict(color="#ff4757", width=1.3)
    ))
    fig.update_layout(**PLOTLY_LAYOUT, height=560)

st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ==========================================================
# VOLUME STRIP
# ==========================================================
st.markdown('<div class="section-label">VOLUME</div>', unsafe_allow_html=True)
vol_colors = [
    "#00d97e" if df["Close"].iloc[i] >= df["Open"].iloc[i] else "#ff4757"
    for i in range(len(df))
]
vol_fig = go.Figure(go.Bar(x=df.index, y=df["Volume"], marker_color=vol_colors, opacity=0.7))
vol_fig.update_layout(**PLOTLY_LAYOUT, height=140)
vol_fig.update_yaxes(title=None)
st.plotly_chart(vol_fig, use_container_width=True, config={"displayModeBar": False})


# ==========================================================
# BOTTOM ROW -- RSI history + fundamentals table
# ==========================================================
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown('<div class="section-label">RSI (14) — HISTORY</div>', unsafe_allow_html=True)
    rsi_fig = go.Figure()
    rsi_fig.add_trace(go.Scatter(
        x=df.index, y=df["RSI"], name="RSI",
        line=dict(color="#2196f3", width=1.5), fill="tozeroy",
        fillcolor="rgba(33,150,243,0.08)"
    ))
    rsi_fig.add_hline(y=70, line_dash="dash", line_color="#ff4757", opacity=0.6)
    rsi_fig.add_hline(y=30, line_dash="dash", line_color="#00d97e", opacity=0.6)
    rsi_fig.update_layout(**PLOTLY_LAYOUT, height=260)
    rsi_fig.update_yaxes(range=[0, 100])
    st.plotly_chart(rsi_fig, use_container_width=True, config={"displayModeBar": False})

with col_right:
    st.markdown('<div class="section-label">FUNDAMENTALS SNAPSHOT</div>', unsafe_allow_html=True)
    snap = pd.DataFrame({
        "Metric": ["Sector", "Market Cap", "Revenue (TTM)", "Price / Sales", "Shares Out", "52W High", "52W Low"],
        "Value": [
            fundamentals["sector"],
            fmt_money(fundamentals["marketCap"]),
            fmt_money(fundamentals["totalRevenue"]),
            f"{ps_ratio:.2f}x" if ps_ratio else "N/A",
            f"{fundamentals['sharesOutstanding']/1e6:.1f}M",
            f"${df_full['Close'].tail(252).max():.2f}",
            f"${df_full['Close'].tail(252).min():.2f}",
        ],
    })
    st.dataframe(snap, hide_index=True, use_container_width=True, height=280)

st.markdown(
    '<div style="text-align:center; color:#4a5568; font-family:\'IBM Plex Mono\',monospace; '
    'font-size:11px; margin-top:20px;">MOCK DATA — for real-time quotes, connect a live market data API. '
    'Not investment advice.</div>',
    unsafe_allow_html=True,
)
