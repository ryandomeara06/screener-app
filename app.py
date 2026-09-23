import streamlit as st
from polygon import RESTClient
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(
    page_title="Stock Analysis Dashboard",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("⚙️ Settings")

api_key = st.sidebar.text_input("Polygon API Key", type="password")
ticker = st.sidebar.text_input("Ticker Symbol", "AAPL").upper()

date_start = st.sidebar.date_input("Start Date", pd.to_datetime("2020-01-01"))
date_end = st.sidebar.date_input("End Date", pd.to_datetime("today"))

show_ma = st.sidebar.checkbox("Show Moving Averages", True)
show_bb = st.sidebar.checkbox("Show Bollinger Bands", True)
show_macd = st.sidebar.checkbox("Show MACD", True)
show_rsi = st.sidebar.checkbox("Show RSI", True)
show_dcf = st.sidebar.checkbox("Show DCF Valuation", True)

if not api_key:
    st.warning("Enter your Polygon API key in the sidebar.")
    st.stop()

client = RESTClient(api_key)

# -----------------------------
# PRICE DATA
# -----------------------------
def get_price_data(ticker, start, end):
    bars = client.list_aggs(
        ticker=ticker,
        multiplier=1,
        timespan="day",
        from_=str(start),
        to=str(end),
        limit=50000
    )

    df = pd.DataFrame([{
        "Date": b.timestamp,
        "Open": b.open,
        "High": b.high,
        "Low": b.low,
        "Close": b.close,
        "Volume": b.volume
    } for b in bars])

    df["Date"] = pd.to_datetime(df["Date"], unit="ms")
    df = df.set_index("Date")
    return df

data = get_price_data(ticker, date_start, date_end)
current_price = data["Close"].iloc[-1]

# -----------------------------
# KPI CARDS
# -----------------------------
st.title(f"📊 {ticker} Stock Dashboard")

col1, col2, col3 = st.columns(3)
col1.metric("Current Price", f"${current_price:.2f}")
col2.metric("Latest Volume", f"{data['Volume'].iloc[-1]:,}")
col3.metric("Data Points Loaded", len(data))

# -----------------------------
# MOVING AVERAGES
# -----------------------------
data["MA20"] = data["Close"].rolling(20).mean()
data["MA50"] = data["Close"].rolling(50).mean()
data["MA200"] = data["Close"].rolling(200).mean()

# -----------------------------
# BOLLINGER BANDS
# -----------------------------
data["BB_MID"] = data["Close"].rolling(20).mean()
data["BB_STD"] = data["Close"].rolling(20).std()
data["BB_UPPER"] = data["BB_MID"] + (2 * data["BB_STD"])
data["BB_LOWER"] = data["BB_MID"] - (2 * data["BB_STD"])

# -----------------------------
# PRICE CHART
# -----------------------------
fig = go.Figure()

fig.add_trace(go.Scatter(x=data.index, y=data["Close"], name="Close", line=dict(color="white")))

if show_ma:
    fig.add_trace(go.Scatter(x=data.index, y=data["MA20"], name="MA20"))
    fig.add_trace(go.Scatter(x=data.index, y=data["MA50"], name="MA50"))
    fig.add_trace(go.Scatter(x=data.index, y=data["MA200"], name="MA200"))

if show_bb:
    fig.add_trace(go.Scatter(x=data.index, y=data["BB_UPPER"], name="Upper Band"))
    fig.add_trace(go.Scatter(x=data.index, y=data["BB_MID"], name="Middle Band"))
    fig.add_trace(go.Scatter(x=data.index, y=data["BB_LOWER"], name="Lower Band"))

fig.update_layout(
    title=f"{ticker} Price Chart",
    template="plotly_dark",
    hovermode="x unified",
    height=500
)

st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# MACD
# -----------------------------
if show_macd:
    data["EMA12"] = data["Close"].ewm(span=12, adjust=False).mean()
    data["EMA26"] = data["Close"].ewm(span=26, adjust=False).mean()
    data["MACD"] = data["EMA12"] - data["EMA26"]
    data["Signal"] = data["MACD"].ewm(span=9, adjust=False).mean()
    data["Histogram"] = data["MACD"] - data["Signal"]

    fig_macd = go.Figure()
    fig_macd.add_trace(go.Scatter(x=data.index, y=data["MACD"], name="MACD"))
    fig_macd.add_trace(go.Scatter(x=data.index, y=data["Signal"], name="Signal"))
    fig_macd.add_trace(go.Bar(x=data.index, y=data["Histogram"], name="Histogram"))

    fig_macd.update_layout(
        title="MACD Indicator",
        template="plotly_dark",
        hovermode="x unified",
        height=300
    )

    st.plotly_chart(fig_macd, use_container_width=True)

# -----------------------------
# RSI
# -----------------------------
if show_rsi:
    delta = data["Close"].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)

    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(x=data.index, y=rsi, name="RSI", line=dict(color="purple")))
    fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
    fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")

    fig_rsi.update_layout(
        title="RSI (14)",
        template="plotly_dark",
        hovermode="x unified",
        height=300
    )

    st.plotly_chart(fig_rsi, use_container_width=True)

# -----------------------------
# DCF
# -----------------------------
if show_dcf:
    fin = client.get_financials(ticker, limit=1)
    f = fin.results[0]

    ocf = f.cash_flow_statement.total_cash_from_operating_activities.value
    capex = f.cash_flow_statement.capital_expenditures.value
    fcf = ocf + capex
    shares_outstanding = f.balance_sheet.weighted_average_shares_outstanding_basic.value

    growth_rate = 0.05
    discount_rate = 0.10
    terminal_growth = 0.02
    years = 5

    fcf_forecast = [fcf * ((1 + growth_rate)**i) for i in range(1, years+1)]
    discounted_fcf = [fcf_forecast[i] / ((1 + discount_rate)**(i+1)) for i in range(years)]
    terminal_value = fcf_forecast[-1] * (1 + terminal_growth) / (discount_rate - terminal_growth)
    terminal_value_discounted = terminal_value / ((1 + discount_rate)**years)

    intrinsic_value = sum(discounted_fcf) + terminal_value_discounted
    intrinsic_value_per_share = intrinsic_value / shares_outstanding

    st.subheader("💰 DCF Valuation")
    st.write(f"**Intrinsic Value per Share:** ${intrinsic_value_per_share:.2f}")

    if intrinsic_value_per_share > current_price:
        st.success(f"{ticker} appears UNDERVALUED by ${intrinsic_value_per_share - current_price:.2f}")
    else:
        st.error(f"{ticker} appears OVERVALUED by ${current_price - intrinsic_value_per_share:.2f}")
