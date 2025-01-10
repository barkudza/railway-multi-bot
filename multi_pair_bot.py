from flask import Flask, request, jsonify
from binance.client import Client
from binance.enums import *

# Flask App
app = Flask(__name__)

# Binance API Keys (Doğrudan tanımlandı)
API_KEY = "rMyIhf1p1yj7rPcODFYG1fM5u8RlMBa4SjoRxAdWQQWzPtstvViSU1DwVDzqHTEX"
API_SECRET = "tRn3bRIdeHpzuznurKIQ9ZrfO5xiWayHhWt80gi3rvyolS8gLn8hsIDmjnwywGA"

# Binance Client
client = Client(API_KEY, API_SECRET)

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
    app.run(debug=True)
