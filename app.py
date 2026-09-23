import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import requests

st.set_page_config(page_title="Stock Dashboard", layout="wide")

# -----------------------------
# SIDEBAR
# -----------------------------
st.sidebar.title("Settings")

alpha_key = st.sidebar.text_input("Alpha Vantage API Key", type="password")
ticker = st.sidebar.text_input("Ticker", "AAPL").upper()

if not alpha_key:
    st.warning("Enter your Alpha Vantage API key.")
    st.stop()

# -----------------------------
# PRICE DATA
# -----------------------------
url = f"https://www.alphavantage.co/query?function=TIME_SERIES_DAILY_ADJUSTED&symbol={ticker}&outputsize=full&apikey={alpha_key}"
r = requests.get(url).json()

if "Time Series (Daily)" not in r:
    st.error("Invalid ticker or API limit reached.")
    st.stop()

df = pd.DataFrame(r["Time Series (Daily)"]).T
df.index = pd.to_datetime(df.index)
df = df.sort_index()

df["Close"] = df["5. adjusted close"].astype(float)
df["Volume"] = df["6. volume"].astype(float)

# -----------------------------
# KPI CARDS
# -----------------------------
st.title(f"{ticker} Dashboard")

col1, col2, col3 = st.columns(3)
col1.metric("Price", f"${df['Close'][-1]:.2f}")
col2.metric("Volume", f"{int(df['Volume'][-1])}")
col3.metric("Data Points", len(df))

# -----------------------------
# INDICATORS
# -----------------------------
df["MA20"] = df["Close"].rolling(20).mean()
df["MA50"] = df["Close"].rolling(50).mean()
df["MA200"] = df["Close"].rolling(200).mean()

df["BB_MID"] = df["Close"].rolling(20).mean()
df["BB_STD"] = df["Close"].rolling(20).std()
df["BB_UPPER"] = df["BB_MID"] + 2 * df["BB_STD"]
df["BB_LOWER"] = df["BB_MID"] - 2 * df["BB_STD"]

# -----------------------------
# PRICE CHART
# -----------------------------
fig = go.Figure()
fig.add_trace(go.Scatter(x=df.index, y=df["Close"], name="Close"))
fig.add_trace(go.Scatter(x=df.index, y=df["MA20"], name="MA20"))
fig.add_trace(go.Scatter(x=df.index, y=df["MA50"], name="MA50"))
fig.add_trace(go.Scatter(x=df.index, y=df["MA200"], name="MA200"))
fig.add_trace(go.Scatter(x=df.index, y=df["BB_UPPER"], name="Upper BB"))
fig.add_trace(go.Scatter(x=df.index, y=df["BB_LOWER"], name="Lower BB"))
fig.update_layout(template="plotly_dark", height=500)
st.plotly_chart(fig, use_container_width=True)

# -----------------------------
# MACD
# -----------------------------
df["EMA12"] = df["Close"].ewm(span=12).mean()
df["EMA26"] = df["Close"].ewm(span=26).mean()
df["MACD"] = df["EMA12"] - df["EMA26"]
df["Signal"] = df["MACD"].ewm(span=9).mean()

fig_macd = go.Figure()
fig_macd.add_trace(go.Scatter(x=df.index, y=df["MACD"], name="MACD"))
fig_macd.add_trace(go.Scatter(x=df.index, y=df["Signal"], name="Signal"))
fig_macd.update_layout(template="plotly_dark", height=300)
st.plotly_chart(fig_macd, use_container_width=True)

# -----------------------------
# RSI
# -----------------------------
delta = df["Close"].diff()
gain = delta.where(delta > 0, 0)
loss = -delta.where(delta < 0, 0)
avg_gain = gain.rolling(14).mean()
avg_loss = loss.rolling(14).mean()
rs = avg_gain / avg_loss
rsi = 100 - (100 / (1 + rs))

fig_rsi = go.Figure()
fig_rsi.add_trace(go.Scatter(x=df.index, y=rsi, name="RSI"))
fig_rsi.add_hline(y=70, line_dash="dash", line_color="red")
fig_rsi.add_hline(y=30, line_dash="dash", line_color="green")
fig_rsi.update_layout(template="plotly_dark", height=300)
st.plotly_chart(fig_rsi, use_container_width=True)
