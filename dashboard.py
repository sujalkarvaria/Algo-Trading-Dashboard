import streamlit as st
from streamlit_autorefresh import st_autorefresh
import streamlit.components.v1 as components
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go

# ---------------- Page Setup ----------------
st.set_page_config(layout="wide")
st_autorefresh(interval=30000)

st.title("🚀 Algo Trading Dashboard")

# ---------------- Sidebar ----------------
stock = st.sidebar.text_input("Stock Symbol", "RELIANCE.NS")

period = st.sidebar.selectbox(
    "Period",
    ["5d", "1mo", "3mo", "6mo", "1y"]
)

interval = st.sidebar.selectbox(
    "Interval",
    ["5m", "15m", "30m", "1h", "1d"]
)

chart_type = st.sidebar.selectbox(
    "Chart Type",
    ["Candlestick", "Line"]
)

show_volume = st.sidebar.checkbox("Show Volume", True)

capital = st.sidebar.number_input(
    "Capital ₹",
    value=10000.0
)

stoploss_pct = st.sidebar.number_input(
    "Stoploss %",
    value=2.0
)

target_pct = st.sidebar.number_input(
    "Target %",
    value=4.0
)

run_backtest = st.sidebar.button("Run Backtest")

# ---------------- Load Data ----------------
df = yf.download(stock, period=period, interval=interval)

if df.empty:
    st.error("No data found. Check stock symbol.")
    st.stop()

df.reset_index(inplace=True)

time_col = "Datetime" if "Datetime" in df.columns else "Date"

# ---------------- Indicators ----------------
df["EMA20"] = df["Close"].ewm(span=20).mean()
df["EMA50"] = df["Close"].ewm(span=50).mean()

# ---------------- Current Signal ----------------
last_row = df.iloc[-1]

ema20 = last_row["EMA20"]
ema50 = last_row["EMA50"]

ema20 = float(ema20.iloc[0] if hasattr(ema20, "iloc") else ema20)
ema50 = float(ema50.iloc[0] if hasattr(ema50, "iloc") else ema50)

if ema20 > ema50:
    current_signal = "BUY"
elif ema20 < ema50:
    current_signal = "SELL"
else:
    current_signal = "HOLD"

# ---------------- Live Price Box ----------------
last_price = float(df["Close"].iloc[-1])
prev_price = float(df["Close"].iloc[-2])

change = last_price - prev_price
change_pct = (change / prev_price) * 100

html = f"""
<div style="display:flex;
justify-content:space-between;
align-items:center;
background:#111;
padding:12px;
border-radius:10px;
width:100%;">

<span style="color:white;
font-size:20px;">
{stock}
</span>

<div style="text-align:right;">

<span style="color:white;
font-size:22px;">
₹{round(last_price,2)}
</span><br>

<span style="color:{'lime' if change >= 0 else 'red'};">
{round(change,2)}
({round(change_pct,2)}%)
</span>

</div>
</div>
"""

components.html(html, height=80)

# ---------------- Signal Row ----------------
col1, col2 = st.columns([3,1])

with col1:
    st.markdown(
        f"<h3>📈 {stock}</h3>",
        unsafe_allow_html=True
    )

with col2:

    if current_signal == "BUY":
        st.markdown(
            """
            <div style='text-align:center;
            color:white;
            background:green;
            padding:6px;
            font-size:18px;
            border-radius:8px;'>
            BUY
            </div>
            """,
            unsafe_allow_html=True
        )

    elif current_signal == "SELL":
        st.markdown(
            """
            <div style='text-align:center;
            color:white;
            background:red;
            padding:6px;
            font-size:18px;
            border-radius:8px;'>
            SELL
            </div>
            """,
            unsafe_allow_html=True
        )

    else:
        st.markdown(
            """
            <div style='text-align:center;
            color:black;
            background:yellow;
            padding:6px;
            font-size:18px;
            border-radius:8px;'>
            HOLD
            </div>
            """,
            unsafe_allow_html=True
        )

# ---------------- Signals ----------------
df["Signal"] = 0

df.loc[df["EMA20"] > df["EMA50"], "Signal"] = 1
df.loc[df["EMA20"] < df["EMA50"], "Signal"] = -1

df["Trade"] = df["Signal"].diff()

# ---------------- Trades + Profit ----------------
position = 0
buy_price = 0
qty = 0

trades = []
total_profit = 0.0

for i in range(len(df)):

    price = float(df["Close"].iloc[i])

    trade_signal = (
        0 if pd.isna(df["Trade"].iloc[i])
        else int(df["Trade"].iloc[i])
    )

    # BUY
    if trade_signal == 2 and position == 0:

        buy_price = price
        buy_time = df[time_col].iloc[i]

        qty = capital / buy_price

        stoploss = buy_price * (1 - stoploss_pct / 100)
        target = buy_price * (1 + target_pct / 100)

        position = 1

    # SELL
    elif position == 1:

        if (
            price <= stoploss
            or price >= target
            or trade_signal == -2
        ):

            sell_price = price
            sell_time = df[time_col].iloc[i]

            profit = (
                (sell_price - buy_price)
                * qty
            )

            total_profit += profit

            trades.append([
                buy_time,
                round(buy_price,2),
                sell_time,
                round(sell_price,2),
                round(profit,2)
            ])

            position = 0

# ---------------- Trade Data ----------------
trade_df = pd.DataFrame(
    trades,
    columns=[
        "Buy Time",
        "Buy Price",
        "Sell Time",
        "Sell Price",
        "Profit"
    ]
)

trade_count = len(trade_df)

percent_return = (
    (total_profit / capital) * 100
    if capital > 0 else 0
)

# ---------------- Chart ----------------
fig = go.Figure()

# Candlestick / Line
if chart_type == "Candlestick":

    fig.add_trace(go.Candlestick(
        x=df[time_col],
        open=df["Open"],
        high=df["High"],
        low=df["Low"],
        close=df["Close"],
        name="Price"
    ))

else:

    fig.add_trace(go.Scatter(
        x=df[time_col],
        y=df["Close"],
        mode="lines",
        name="Close"
    ))

# EMA Lines
fig.add_trace(go.Scatter(
    x=df[time_col],
    y=df["EMA20"],
    name="EMA20"
))

fig.add_trace(go.Scatter(
    x=df[time_col],
    y=df["EMA50"],
    name="EMA50"
))

# BUY markers
fig.add_trace(go.Scatter(
    x=df[df["Trade"] == 2][time_col],
    y=df[df["Trade"] == 2]["Close"],
    mode="markers",
    marker_symbol="triangle-up",
    marker_size=12,
    name="BUY"
))

# SELL markers
fig.add_trace(go.Scatter(
    x=df[df["Trade"] == -2][time_col],
    y=df[df["Trade"] == -2]["Close"],
    mode="markers",
    marker_symbol="triangle-down",
    marker_size=12,
    name="SELL"
))

# Volume
if show_volume:

    fig.add_trace(go.Bar(
        x=df[time_col],
        y=df["Volume"],
        name="Volume",
        yaxis="y2"
    ))

fig.update_layout(
    xaxis_rangeslider_visible=False,
    yaxis2=dict(
        overlaying="y",
        side="right",
        showgrid=False
    ),
    height=700
)

st.plotly_chart(fig, use_container_width=True)

# ---------------- Metrics ----------------
c1, c2, c3, c4 = st.columns(4)

c1.metric("Capital", f"₹{round(capital,2)}")
c2.metric("Total Profit", f"₹{round(total_profit,2)}")
c3.metric("% Return", f"{round(percent_return,2)}%")
c4.metric("Trades", trade_count)

# ---------------- Trade History ----------------
st.subheader("Trade History")
st.dataframe(trade_df)

# ---------------- Backtesting ----------------
if run_backtest:

    wins = trade_df[trade_df["Profit"] > 0]

    total_trades = len(trade_df)
    winning_trades = len(wins)

    win_rate = (
        (winning_trades / total_trades) * 100
        if total_trades > 0 else 0
    )

    net_profit = trade_df["Profit"].sum()

    return_pct = (
        (net_profit / capital) * 100
        if capital > 0 else 0
    )

    st.subheader("📊 Backtest Result")

    b1, b2, b3, b4 = st.columns(4)

    b1.metric("Total Trades", total_trades)
    b2.metric("Winning Trades", winning_trades)
    b3.metric("Win %", f"{round(win_rate,2)}%")
    b4.metric("Net Profit", f"₹{round(net_profit,2)}")

    st.metric("Return %", f"{round(return_pct,2)}%")
