import os
import requests
from flask import Flask, request, jsonify
from binance.client import Client
from binance.enums import *

# Flask App
app = Flask(__name__)

# Binance API Keys
API_KEY = "fKpytFYxYTigkaS7QN0AGGDLAYwCEjHpAGWdrvg9FVKWJOd6rqrbXpJiMxmF9A6E"  # Binance API anahtarınızı buraya ekleyin
API_SECRET = "1rGYNrn1BH14svjoWKC761Xh5zhA1i7B7mhjCCj9xOYL7TGzFniocsHhIDFmF2WO"  # Binance Secret anahtarınızı buraya ekleyin

# Proxy Ayarları
session = requests.Session()
session.proxies = {
    'http': 'http://188.132.222.40:8080',
    'https': 'http://188.132.222.40:8080',
}

# Binance Client
client = Client(API_KEY, API_SECRET, requests_params={"session": session})

# İşleme Girecek Coin Çiftleri
ALLOWED_PAIRS = ["BTCUSDT", "SUIUSDT"]

# Bot Ayarları
POSITION_SIZE_USDT = 20  # İşlem başına kullanılacak bakiye
LEVERAGE = 10  # Kaldıraç oranı

@app.route('/')
def home():
    return "Bot başarıyla çalışıyor!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        data = request.json
        symbol = data.get("pair")
        signal = data.get("signal")

        if not symbol or not signal:
            return jsonify({"error": "Eksik veri"}), 400

        if symbol not in ALLOWED_PAIRS:
            return jsonify({"error": f"İzin verilen çiftler arasında değil: {symbol}"}), 400

        if signal == "AL":
            try:
                client.futures_change_leverage(symbol=symbol, leverage=LEVERAGE)
                order = client.futures_create_order(
                    symbol=symbol,
                    side=SIDE_BUY,
                    type=ORDER_TYPE_MARKET,
                    quantity=POSITION_SIZE_USDT
                )
                return jsonify({"success": True, "message": f"{symbol} için AL sinyali işlendi", "order": order}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        elif signal == "SAT":
            try:
                client.futures_change_leverage(symbol=symbol, leverage=LEVERAGE)
                order = client.futures_create_order(
                    symbol=symbol,
                    side=SIDE_SELL,
                    type=ORDER_TYPE_MARKET,
                    quantity=POSITION_SIZE_USDT
                )
                return jsonify({"success": True, "message": f"{symbol} için SAT sinyali işlendi", "order": order}), 200
            except Exception as e:
                return jsonify({"error": str(e)}), 500
        else:
            return jsonify({"error": "Geçersiz sinyal"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
