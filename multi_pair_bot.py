import os
from flask import Flask, request, jsonify
from binance.client import Client
from binance.enums import *

# Çevresel Değişkenlerden API Anahtarlarını Alın
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# Binance Client
client = Client(API_KEY, API_SECRET)

# İşleme Girecek Coin Çiftleri
ALLOWED_PAIRS = ["BTCUSDT", "SUIUSDT", "COOKIEUSDT", "CGPTUSDT", "AVAXUSDT", "MOVEUSDT", "SOLUSDT", "USUALUSDT", "EIGENUSDT", "PENGUUSDT", "BIOUSDT", "AGLDUSDT", "XRPUSDT", "HIVEUSDT"]

# Bot Ayarları
POSITION_SIZE_USDT = 10  # İşlem başına kullanılacak bakiye
LEVERAGE = 15  # Kaldıraç oranı

app = Flask(__name__)

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

        # Mevcut pozisyonu kontrol edin
        positions = client.futures_position_information()
        current_position = None
        for position in positions:
            if position['symbol'] == symbol:
                current_position = position
                break

        # Pozisyon kapatma ve ters işlem açma
        if current_position and float(current_position['positionAmt']) != 0:
            try:
                # Mevcut pozisyonu kapat
                side_to_close = SIDE_SELL if float(current_position['positionAmt']) > 0 else SIDE_BUY
                client.futures_create_order(
                    symbol=symbol,
                    side=side_to_close,
                    type=ORDER_TYPE_MARKET,
                    quantity=abs(float(current_position['positionAmt']))
                )
            except Exception as e:
                return jsonify({"error": f"Pozisyon kapatılamadı: {str(e)}"}), 500

        # Yeni işlem aç
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
