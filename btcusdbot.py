import requests
import pandas as pd
import time
import winsound
from telegram import Bot
import ta

from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "BTC bot is running", 200

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

keep_alive()

# ==============================
# TELEGRAM SETTINGS
# ==============================

TOKEN = "8402698231:AAHZjmHQ2ClH3tMY3BvOltpYQ6dG80w0aYg"
CHAT_ID = "1046367566"

bot = Bot(token=TOKEN)

def send_telegram(msg):
    try:
        bot.send_message(chat_id=CHAT_ID, text=msg)
    except Exception as e:
        print("Telegram error:", e)

def beep():
    winsound.Beep(1200, 700)

def startup_message():
    try:
        send_telegram("✅ BTC Alert Bot is now ONLINE and monitoring the market.")
        print("Startup message sent to Telegram")
    except Exception as e:
        print("Startup message failed:", e)

# ==============================
# GET BTC DATA FROM DELTA
# ==============================

def get_candles():

    end_time = int(time.time())
    start_time = end_time - (60 * 5 * 200)

    url = "https://api.delta.exchange/v2/history/candles"

    params = {
        "symbol": "BTCUSD",
        "resolution": "5m",
        "start": start_time,
        "end": end_time
    }

    try:
        r = requests.get(url, params=params, timeout=10)
        js = r.json()

        if js.get("success") != True:
            print("Delta API response:", js)
            return None

        candles = js["result"]

        df = pd.DataFrame(candles, columns=[
            "time","open","high","low","close","volume"
        ])

        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.sort_values("time")

        df["close"] = df["close"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["volume"] = df["volume"].astype(float)

        return df

    except Exception as e:
        print("Network/API error:", e)
        return None

# ==============================
# INDICATORS & SIGNALS
# ==============================

def calculate_signals(df):

    df["close"] = pd.to_numeric(df["close"])
    df["high"] = pd.to_numeric(df["high"])
    df["low"] = pd.to_numeric(df["low"])
    df["volume"] = pd.to_numeric(df["volume"])

    # EMA crossover
    df['ema10'] = ta.trend.ema_indicator(close=df['close'], window=10)
    df['ema20'] = ta.trend.ema_indicator(close=df['close'], window=20)

    # VWAP
    typical_price = (df['high'] + df['low'] + df['close']) / 3
    cumulative_tp_vol = (typical_price * df['volume']).cumsum()
    cumulative_vol = df['volume'].cumsum()
    df['vwap'] = cumulative_tp_vol / cumulative_vol

    last = df.iloc[-1]
    prev = df.iloc[-2]

    buy_signal = (
        prev['ema10'] < prev['ema20'] and
        last['ema10'] > last['ema20'] and
        last['close'] > last['vwap']
    )

    sell_signal = (
        prev['ema10'] > prev['ema20'] and
        last['ema10'] < last['ema20'] and
        last['close'] < last['vwap']
    )

    return buy_signal, sell_signal, last['close']

# ==============================
# MAIN LOOP
# ==============================

last_signal = None

print("Bot started... Watching BTCUSD")
startup_message()

while True:

    df = get_candles()

    if df is None:
        time.sleep(60)
        continue

    try:
        buy, sell, price = calculate_signals(df)

        if buy and last_signal != "BUY":
            message = f"""🟢 BTC CALL SIGNAL

Price: {price}

Action:
Buy nearest ATM CALL option

Timeframe: 30–90 minutes
(Session volatility expected)
"""
            print(message)
            send_telegram(message)
            beep()
            last_signal = "BUY"

        elif sell and last_signal != "SELL":
            message = f"""🔴 BTC PUT SIGNAL

Price: {price}

Action:
Buy nearest ATM PUT option

Timeframe: 30–90 minutes
(Session volatility expected)
"""
            print(message)
            send_telegram(message)
            beep()
            last_signal = "SELL"

    except Exception as e:
        print("Processing error:", e)

    time.sleep(60)
