import pandas as pd
import yfinance as yf

data = yf.download("RELIANCE.NS", start="2024-01-01")

data["EMA20"] = data["Close"].ewm(span=20, adjust=False).mean()
data["EMA50"] = data["Close"].ewm(span=50, adjust=False).mean()

data["Signal"] = 0
data.loc[data["EMA20"] > data["EMA50"], "Signal"] = 1
data.loc[data["EMA20"] < data["EMA50"], "Signal"] = -1


# Backtesting
position = 0
entry_price = 0
profit = 0

for i in range(len(data)):
    if data["Signal"].iloc[i] == 1 and position == 0:
        entry_price = data["Close"].iloc[i]
        position = 1
        print("BUY at", entry_price)

    elif data["Signal"].iloc[i] == -1 and position == 1:
        exit_price = data["Close"].iloc[i]
        trade_profit = exit_price - entry_price
        profit += trade_profit
        position = 0
        print("SELL at", exit_price, "Profit:", trade_profit)

print("\nTotal Profit:", profit)
