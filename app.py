import os
import time
import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta

FINNHUB_BASE = "https://finnhub.io/api/v1"
FMP_BASE = "https://financialmodelingprep.com/api/v3"

# -----------------------------
# Load API keys from local files
# -----------------------------
def load_key(filename):
    try:
        with open(filename, "r") as f:
            return f.read().strip()
    except:
        return None

FINNHUB_KEY = load_key("finnhub_key.txt")
FMP_KEY = load_key("fmp_key.txt")

st.set_page_config(page_title="Stock Analysis App", layout="wide")

# -----------------------------
# Finnhub helpers
# -----------------------------
def fh_get(path, params=None):
    if params is None:
        params = {}
    params["token"] = FINNHUB_KEY
    resp = requests.get(f"{FINNHUB_BASE}/{path}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_price_series(symbol, days=365):
    now = int(time.time())
    frm = now - days * 24 * 60 * 60
    data = fh_get("stock/candle", {
        "symbol": symbol,
        "resolution": "D",
        "from": frm,
        "to": now
    })
    if data.get("s") != "ok":
        return pd.DataFrame()

    df = pd.DataFrame({
        "t": data["t"],
        "open": data["o"],
        "high": data["h"],
        "low": data["l"],
        "close": data["c"],
        "volume": data["v"],
    })
    df["date"] = pd.to_datetime(df["t"], unit="s")
    df.set_index("date", inplace=True)
    df.drop(columns=["t"], inplace=True)
    return df

def get_indicator(symbol, indicator, extra_params=None, days=365):
    if extra_params is None:
        extra_params = {}
    now = int(time.time())
    frm = now - days * 24 * 60 * 60
    params = {
        "symbol": symbol,
        "resolution": "D",
        "from": frm,
        "to": now,
        "indicator": indicator,
    }
    params.update(extra_params)
    data = fh_get("indicator", params)
    if "t" not in data or len(data["t"]) == 0:
        return pd.DataFrame()

    df = pd.DataFrame({"t": data["t"]})
    df["date"] = pd.to_datetime(df["t"], unit="s")
    df.set_index("date", inplace=True)
    df.drop(columns=["t"], inplace=True)

    for key, values in data.items():
        if key in ["s", "t"]:
            continue
        df[key] = values

    return df

# -----------------------------
# FMP helpers
# -----------------------------
def fmp_get(path, params=None):
    if params is None:
        params = {}
    params["apikey"] = FMP_KEY
    resp = requests.get(f"{FMP_BASE}/{path}", params=params, timeout=10)
    resp.raise_for_status()
    return resp.json()

def get_fmp_profile(symbol):
    data = fmp_get(f"profile/{symbol}")
    return data[0] if data else {}

def get_fmp_ratios(symbol):
    data = fmp_get(f"ratios-ttm/{symbol}")
    return data[0] if data else {}

def get_fmp_cashflow(symbol):
    data = fmp_get(f"cash-flow-statement/{symbol}", {"limit": 1})
    return data[0] if data else {}

# -----------------------------
# Trend logic
# -----------------------------
def trend_from_ma(price_df, short=20, long=50):
    df = price_df.copy()
    df["MA_short"] = df["close"].rolling(short).mean()
    df["MA_long"] = df["close"].rolling(long).mean()
    latest = df.iloc[-1]
    if pd.isna(latest["MA_short"]) or pd.isna(latest["MA_long"]):
        return "Not enough data"
    if latest["MA_short"] > latest["MA_long"]:
        return "Uptrend"
    elif latest["MA_short"] < latest["MA_long"]:
        return "Downtrend"
    else:
        return "Sideways"

# -----------------------------
# DCF valuation (simple version)
# -----------------------------
def dcf_valuation(symbol):
    profile = get_fmp_profile(symbol)
    cashflow = get_fmp_cashflow(symbol)

    try:
        fcf = float(cashflow.get("freeCashFlow", 0))
    except:
        fcf = 0.0

    try:
        shares = float(profile.get("sharesOutstanding", 0))
    except:
        shares = 0.0

    if fcf <= 0 or shares <= 0:
        return None

    growth = 0.10
    discount = 0.10
    terminal_multiple = 10

    cash_flows = []
    for year in range(1, 6):
        cf = fcf * ((1 + growth) ** year)
        cash_flows.append(cf)

    pv_cash_flows = [cf / ((1 + discount) ** i) for i, cf in enumerate(cash_flows, start=1)]
    terminal_value = cash_flows[-1] * terminal_multiple
    pv_terminal = terminal_value / ((1 + discount) ** 5)

    intrinsic_equity = sum(pv_cash_flows) + pv_terminal
    intrinsic_per_share = intrinsic_equity / shares
    return intrinsic_per_share

# -----------------------------
# UI - Page 1
# -----------------------------
st.title("📈 Stock Analysis (Finnhub + FMP)")

if not FINNHUB_KEY or not FMP_KEY:
    st.error("Missing API keys. Create finnhub_key.txt and fmp_key.txt with your API keys.")
    st.stop()

with st.sidebar:
    symbol = st.text_input("Ticker", value="AAPL").upper()
    days = st.slider("Days of history", 90, 1500, 365)
    overlay = st.selectbox(
        "Chart overlay",
        ["Moving Averages", "Bollinger Bands", "MACD"]
    )

if st.button("Analyze"):
    try:
        with st.spinner(f"Fetching data for {symbol}..."):
            price_df = get_price_series(symbol, days=days)
            if price_df.empty:
                st.error("No price data returned.")
                st.stop()

            rsi_df = get_indicator(symbol, "rsi", {"timeperiod": 14}, days=days)
            macd_df = get_indicator(symbol, "macd", {
                "fastperiod": 12,
                "slowperiod": 26,
                "signalperiod": 9
            }, days=days)
            bb_df = get_indicator(symbol, "bbands", {
                "timeperiod": 20,
                "nbdevup": 2,
                "nbdevdn": 2
            }, days=days)

            profile = get_fmp_profile(symbol)
            ratios = get_fmp_ratios(symbol)
            intrinsic = dcf_valuation(symbol)

        # Moving averages
        price_df["MA20"] = price_df["close"].rolling(20).mean()
        price_df["MA50"] = price_df["close"].rolling(50).mean()
        price_df["MA200"] = price_df["close"].rolling(200).mean()

        # Merge overlays
        chart_df = price_df.copy()

        if overlay == "Moving Averages":
            st.subheader("Price with Moving Averages")
            st.line_chart(chart_df[["close", "MA20", "MA50", "MA200"]])

        elif overlay == "Bollinger Bands":
            if not bb_df.empty:
                chart_df = chart_df.join(bb_df[["upper", "middle", "lower"]], how="left")
                st.subheader("Price with Bollinger Bands")
                st.line_chart(chart_df[["close", "upper", "middle", "lower"]])
            else:
                st.subheader("Price (no Bollinger data)")
                st.line_chart(chart_df["close"])

        elif overlay == "MACD":
            st.subheader("Price (MACD shown below)")
            st.line_chart(chart_df["close"])
            if not macd_df.empty:
                st.subheader("MACD")
                st.line_chart(macd_df[["macd", "signal", "hist"]])
            else:
                st.write("No MACD data.")

        # Trend
        trend = trend_from_ma(price_df)
        st.write(f"**Trend:** {trend}")

        # Indicators summary
        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("RSI")
            if not rsi_df.empty:
                latest_rsi = rsi_df.iloc[-1]["rsi"]
                st.write(f"Latest RSI: {latest_rsi:.2f}")
            else:
                st.write("No RSI data.")

        with col2:
            st.subheader("MACD (latest)")
            if not macd_df.empty:
                latest = macd_df.iloc[-1]
                st.write(f"MACD: {latest['macd']:.4f}")
                st.write(f"Signal: {latest['signal']:.4f}")
                st.write(f"Hist: {latest['hist']:.4f}")
            else:
                st.write("No MACD data.")

        with col3:
            st.subheader("Bollinger Bands (latest)")
            if not bb_df.empty:
                latest = bb_df.iloc[-1]
                st.write(f"Upper: {latest['upper']:.2f}")
                st.write(f"Middle: {latest['middle']:.2f}")
                st.write(f"Lower: {latest['lower']:.2f}")
            else:
                st.write("No Bollinger data.")

        # Fundamentals
        st.subheader("Fundamentals (FMP)")
        if profile:
            st.write(f"**Company:** {profile.get('companyName')}")
            st.write(f"**Sector:** {profile.get('sector')}")
            st.write(f"**Country:** {profile.get('country')}")
            st.write(f"**Market Cap:** {profile.get('marketCap')}")
        else:
            st.write("No profile data.")

        if ratios:
            st.write(f"**Price-to-Sales (TTM):** {ratios.get('priceToSalesTTM')}")

        # DCF valuation
        st.subheader("Intrinsic Value (Simple DCF)")
        if intrinsic is not None:
            current_price = profile.get("price")
            st.write(f"**Intrinsic value per share:** {intrinsic:.2f}")
            if current_price:
                try:
