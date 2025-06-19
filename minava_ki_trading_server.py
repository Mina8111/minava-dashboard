import time
import threading
import requests
import pandas as pd
from binance.client import Client
from flask import Flask, jsonify, send_from_directory
import os

# === KONFIGURATION ===
BINANCE_API_KEY = "z56G3rQpIEX0pFRlgFuxk0BlywyC3V96JCSjkoOs6tPoeS15gGhcKuJCtpKLUco8"
BINANCE_API_SECRET = "RDAZ1RloN0KjPffpQJr327SJqWZcjEpba8s9LU4k4TMwSwF4N3wGOwZjMkO8KDxd"
TELEGRAM_TOKEN = "AAHZHG-lC9Rpk_Ri4uCz-YMjijec-s-5cPI"
TELEGRAM_CHAT_ID = "6758935708"
SCAN_INTERVAL = 900  # 15 Minuten (900 Sekunden)

client = Client(BINANCE_API_KEY, BINANCE_API_SECRET)
app = Flask(__name__)
latest_signals = []

# === TELEGRAM SENDEN ===
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
        requests.post(url, data=data)
    except Exception as e:
        print("Telegram Error:", e)

# === SIGNAL-LOGIK ===
def analyze_coin(symbol):
    try:
        klines = client.get_klines(symbol=symbol, interval=Client.KLINE_INTERVAL_15MINUTE, limit=50)
        df = pd.DataFrame(klines, columns=[
            "ts", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset", "trades",
            "taker_buy_base", "taker_buy_quote", "ignore"
        ])
        df["close"] = df["close"].astype(float)
        df["EMA20"] = df["close"].ewm(span=20).mean()
        df["EMA50"] = df["close"].ewm(span=50).mean()
        last = df.iloc[-1]
        if last["EMA20"] > last["EMA50"]:
            return f"🚀 [{symbol}] Bullisches Crossover: EMA20 > EMA50"
    except Exception as e:
        print(f"Analysefehler bei {symbol}: {e}")
    return None

# === ALLE COINS HOLEN ===
def fetch_all_symbols():
    info = client.get_exchange_info()
    return [
        s['symbol']
        for s in info['symbols']
        if s['status'] == 'TRADING' and s['isSpotTradingAllowed']
    ]

# === BACKGROUND-SCANNER ===
def scanner():
    global latest_signals
    while True:
        all_symbols = fetch_all_symbols()
        signals = []
        for symbol in all_symbols:
            if not symbol.endswith("USDT"):
                continue
            print(f"Prüfe: {symbol}")
            signal = analyze_coin(symbol)
            print(f"Signal: {signal}")
            if signal:
                signals.append(signal)
                send_telegram(signal)
        # Debug-Testsignal
        test_signal = "🚀 Testsignal [BTCUSDT] Bullisch!"
        signals.append(test_signal)
        send_telegram(test_signal)
        latest_signals = signals
        time.sleep(SCAN_INTERVAL)

# === /signals API ===
@app.route("/signals")
def get_signals():
    return jsonify(latest_signals)

# === /dashboard Route für HTML-Visualisierung ===
@app.route("/dashboard")
def serve_dashboard():
    return send_from_directory(directory=os.getcwd(), path="minava_dashboard.html")

# === START ===
if __name__ == "__main__":
    threading.Thread(target=scanner, daemon=True).start()
    app.run(host="0.0.0.0", port=8080)
    
from flask import send_file

@app.route("/dashboard")
def serve_dashboard():
    return send_file("minava_dashboard.html")
