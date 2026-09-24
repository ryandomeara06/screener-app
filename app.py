import os
import requests
import pandas as pd
import streamlit as st
from datetime import datetime

API_KEY = os.environ.get("ALPHAVANTAGE_API_KEY")
BASE_URL = "https://www.alphavantage.co/query"

st.set_page_config(page_title="Stock Indicator App", layout="wide")

def av_get(function, **params):
    resp = requests.get(
        BASE_URL,
        params={"function": function, "apikey": API_KEY, **params},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()

def get_price_series(symbol):
    ts = av_get("TIME_SERIES_DAILY", symbol=symbol, outputsize="compact")
    data = ts.get("Time Series (Daily)", {})
    df = pd.DataFrame.from_dict(data, orient="index", dtype=float)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    df.rename(
        columns={
            "1. open": "open",
            "2. high": "high",
            "3. low": "low",
            "4. close": "close",
            "5. volume": "volume",
        },
        inplace=True,
    )
    return df

def get_overview(symbol):
    return av_get("OVERVIEW", symbol=symbol)

def parse_indicator_series(ind_json, key_name):
    series = ind_json.get(key_name, {})
    df = pd.DataFrame.from_dict(series, orient="index", dtype=float)
    df.index = pd.to_datetime(df.index)
    df = df.sort_index()
    return df

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

st.title("📈 Stock Indicator App (Alpha Vantage)")

if not API_KEY:
    st.error("Set ALPHAVANTAGE_API_KEY environment variable.")
    st.stop()

symbol = st.text_input("Ticker", value="AAPL").upper()

if st.button("Analyze"):
    try:
        with st.spinner(f"Fetching data for {symbol}..."):
            price_df = get_price_series(symbol)
            rsi_json = av_get("RSI", symbol=symbol, interval="daily", time_period=14, series_type="close")
            macd_json = av_get("MACD", symbol=symbol, interval="daily", series_type="close")
            bb_json = av_get("BBANDS", symbol=symbol, interval="daily", time_period=20, series_type="close")
            overview = get_overview(symbol)

        st.subheader(f"Price History — {symbol}")
        st.line_chart(price_df["close"])

        trend = trend_from_ma(price_df)
        st.write(f"**Trend:** {trend}")

        rsi_df = parse_indicator_series(rsi_json, "Technical Analysis: RSI")
        macd_df = parse_indicator_series(macd_json, "Technical Analysis: MACD")
        bb_df = parse_indicator_series(bb_json, "Technical Analysis: BBANDS")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("RSI")
            if not rsi_df.empty:
                st.write(f"Latest RSI: {rsi_df.iloc[-1]['RSI']:.2f}")
            else:
                st.write("No RSI data")

        with col2:
            st.subheader("MACD")
            if not macd_df.empty:
                latest = macd_df.iloc[-1]
                st.write(f"MACD: {latest['MACD']:.4f}")
                st.write(f"Signal: {latest['MACD_Signal']:.4f}")
                st.write(f"Hist: {latest['MACD_Hist']:.4f}")
            else:
                st.write("No MACD data")

        with col3:
            st.subheader("Bollinger Bands")
            if not bb_df.empty:
                latest = bb_df.iloc[-1]
                st.write(f"Upper: {latest['Real Upper Band']:.2f}")
                st.write(f"Middle: {latest['Real Middle Band']:.2f}")
                st.write(f"Lower: {latest['Real Lower Band']:.2f}")
            else:
                st.write("No Bollinger data")

        st.subheader("Fundamentals")
        if overview:
            st.write(f"**Market Cap:** {overview.get('MarketCapitalization')}")
            st.write(f"**Sector:** {overview.get('Sector')}")
            st.write(f"**Price-to-Sales (TTM):** {overview.get('PriceToSalesRatioTTM')}")
        else:
            st.write("No overview data.")

    except Exception as e:
        st.error(f"Error: {e}")
