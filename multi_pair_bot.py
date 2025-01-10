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

        if symbol not in ALLOWED_PAIRS:
            return jsonify({"error": f"İzin verilen çiftler arasında değil: {symbol}"}), 400

        if signal == "AL":
            # İşlem mantığı burada yer alacak
            return jsonify({"success": True, "message": f"{symbol} için AL sinyali alındı"}), 200
        elif signal == "SAT":
            # İşlem mantığı burada yer alacak
            return jsonify({"success": True, "message": f"{symbol} için SAT sinyali alındı"}), 200
        else:
            return jsonify({"error": "Geçersiz sinyal"}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
