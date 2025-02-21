import os
import logging
from dotenv import load_dotenv
from flask import Flask, request, jsonify
from binance.client import Client
from binance.enums import *
import requests

# .env Dosyasını Yükle
load_dotenv()

# Binance API Bilgileri
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# Telegram Bot Bilgileri
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Flask App
app = Flask(__name__)

# Binance Client
client = Client(API_KEY, API_SECRET)

# İşlem Yapılacak Coin Çiftleri
ALLOWED_PAIRS = ["BERAUSDT", "LAYERUSDT", "SUSDT"]

# İşlem Parametreleri
POSITION_SIZE_USDT = 10  # İşlem başına kullanılacak USDT miktarı
LEVERAGE = 20  # Kaldıraç

# Logging Ayarları
logging.basicConfig(level=logging.INFO)

# Telegram Mesajı Gönderme Fonksiyonu
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            logging.info(f"Telegram mesajı gönderildi: {message}")
        else:
            logging.error(f"Telegram mesajı gönderilemedi: {response.text}")
    except Exception as e:
        logging.error(f"Telegram hatası: {e}")

# Sembolün Hassasiyetini Alma
def get_symbol_precision(symbol):
    exchange_info = client.futures_exchange_info()
    for symbol_info in exchange_info['symbols']:
        if symbol_info['symbol'] == symbol:
            for f in symbol_info['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    return int(f['stepSize'].find('1') - 1), float(f['minQty'])
    return 2, 0.1

# Kaldıraç Ayarla
def set_leverage(symbol):
    try:
        response = client.futures_change_leverage(symbol=symbol, leverage=LEVERAGE)
        logging.info(f"{symbol} için kaldıraç {LEVERAGE}x olarak ayarlandı: {response}")
    except Exception as e:
        logging.error(f"{symbol} için kaldıraç ayarlanırken hata oluştu: {e}")

# Long Pozisyon Açma (Stop Loss ve Take Profit Yok!)
def open_long_position(symbol):
    try:
        entry_price = float(client.futures_symbol_ticker(symbol=symbol)["price"])
        quantity = (POSITION_SIZE_USDT * LEVERAGE) / entry_price
        precision, min_qty = get_symbol_precision(symbol)
        quantity = max(round(quantity, precision), min_qty)

        set_leverage(symbol)
        client.futures_create_order(
            symbol=symbol,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
        )
        logging.info(f"{symbol} için long pozisyon açıldı. Miktar: {quantity}")
        send_telegram_message(f"🚀 **ALIM YAPILDI!**\n\n📌 **Sembol:** {symbol}\n📊 **Fiyat:** {entry_price}\n📈 **Miktar:** {quantity}")
    
    except Exception as e:
        logging.error(f"{symbol} için pozisyon açarken hata oluştu: {e}")
        send_telegram_message(f"⚠️ **HATA:** {symbol} için alım yapılamadı!\nHata: {e}")

# Long Pozisyon Kapatma
def close_long_position(symbol):
    try:
        positions = client.futures_position_information()
        for position in positions:
            if position["symbol"] == symbol and float(position["positionAmt"]) > 0:
                quantity = abs(float(position["positionAmt"]))
                client.futures_create_order(
                    symbol=symbol,
                    side=SIDE_SELL,
                    type=ORDER_TYPE_MARKET,
                    quantity=quantity,
                )
                logging.info(f"{symbol} için long pozisyon kapatıldı. Miktar: {quantity}")
                send_telegram_message(f"📉 **SATIŞ YAPILDI!**\n\n📌 **Sembol:** {symbol}\n📊 **Miktar:** {quantity}")
                return
        logging.info(f"{symbol} için açık long pozisyon bulunamadı.")
    
    except Exception as e:
        logging.error(f"{symbol} için pozisyon kapatırken hata oluştu: {e}")
        send_telegram_message(f"⚠️ **HATA:** {symbol} için satış yapılamadı!\nHata: {e}")

# Webhook Endpoint (TradingView Webhook ile Çalışacak)
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    symbol = data.get("pair")
    signal = data.get("signal")

    if not symbol or not signal:
        logging.error("Geçersiz veri alındı!")
        return jsonify({"error": "Invalid data"}), 400

    if symbol not in ALLOWED_PAIRS:
        logging.error(f"{symbol} işlem listesinde değil!")
        return jsonify({"error": "Pair not allowed"}), 400

    if signal == "SAT":
        close_long_position(symbol)
        logging.info(f"SELL sinyali alındı, {symbol} için pozisyon kapatılıyor.")
    elif signal == "AL":
        open_long_position(symbol)
        logging.info(f"BUY sinyali alındı, {symbol} için long pozisyon açılıyor.")

    return jsonify({"success": True}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
