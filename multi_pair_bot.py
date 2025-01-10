from flask import Flask, request, jsonify
from binance.client import Client
from binance.enums import *
import logging
import time
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Flask App
app = Flask(__name__)

# Binance API Keys
API_KEY = os.getenv("rMyIhf1p1yj7rPcODFYG1fM5u8RlMBa4SjoRxAdWQQWzPtstvViSU1DwVDzqHTEX")
API_SECRET = os.getenv("tRn3bRIdeHpzuznurKIQ9ZrfO5xiWayHhWt80gi3rvyolS8gLn8hsIDmjnwywGA")

# Binance Client
if API_KEY and API_SECRET:
    client = Client(API_KEY, API_SECRET)
else:
    raise ValueError("Binance API Key and Secret must be set as environment variables.")

# İşleme Girecek Coin Çiftleri
ALLOWED_PAIRS = ["BTCUSDT", "SUIUSDT"]

# Bot Settings
POSITION_SIZE_USDT = 20  # Her işlem için kullanılacak bakiye (dolar)
LEVERAGE = 10  # Kaldıraç oranı

# Set Logging
logging.basicConfig(level=logging.INFO)

# Set Leverage for All Pairs
def set_leverage(symbol):
    try:
        client.futures_change_leverage(symbol=symbol, leverage=LEVERAGE)
    except Exception as e:
        logging.error(f"Error setting leverage for {symbol}: {e}")

# Get Symbol Precision
def get_symbol_precision(symbol):
    exchange_info = client.futures_exchange_info()
    for symbol_info in exchange_info['symbols']:
        if symbol_info['symbol'] == symbol:
            for f in symbol_info['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    return int(f['stepSize'].find('1') - 1), float(f['minQty'])
    return 2, 0.1

# Close Position
def close_position(position_side, symbol):
    try:
        quantity = get_position_quantity(symbol)
        if quantity > 0:
            client.futures_create_order(
                symbol=symbol,
                side=SIDE_BUY if position_side == "SELL" else SIDE_SELL,
                type=ORDER_TYPE_MARKET,
                quantity=quantity,
            )
            logging.info(f"{position_side} position closed for {symbol}.")
        else:
            logging.info(f"No position to close for {symbol}.")
    except Exception as e:
        logging.error(f"Error closing position for {symbol}: {e}")

# Get Position Quantity
def get_position_quantity(symbol):
    positions = client.futures_position_information()
    for position in positions:
        if position["symbol"] == symbol:
            return abs(float(position["positionAmt"]))
    return 0

# Open Position
def open_position(side, symbol):
    try:
        price = float(client.futures_symbol_ticker(symbol=symbol)["price"])
        PRECISION, MIN_QUANTITY = get_symbol_precision(symbol)
        quantity = round((POSITION_SIZE_USDT * LEVERAGE) / price, PRECISION)
        if quantity < MIN_QUANTITY:
            logging.error(f"Calculated quantity ({quantity}) is less than the minimum allowed for {symbol}.")
            return
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
        )
        logging.info(f"{side} position opened for {symbol}: {order}")
    except Exception as e:
        logging.error(f"Error opening position for {symbol}: {e}")

# Webhook
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    symbol = data.get("pair")  # Sinyaldeki işlem çifti (ör. BTCUSDT)
    signal = data.get("signal")  # Sinyal türü (AL veya SAT)

    if not symbol or not signal:
        logging.error("Invalid signal or pair in webhook data.")
        return jsonify({"error": "Invalid data"}), 400

    # İşlem çifti kontrolü
    if symbol not in ALLOWED_PAIRS:
        logging.error(f"Pair {symbol} is not allowed.")
        return jsonify({"error": "Pair not allowed"}), 400

    set_leverage(symbol)  # Kaldıraç ayarla

    if signal == "AL":  # BUY sinyali geldiğinde
        close_position("SELL", symbol)  # Short pozisyonu kapat
        time.sleep(2)  # İşlemler arasında bekleme süresi
        open_position(SIDE_BUY, symbol)  # Long pozisyon aç
    elif signal == "SAT":  # SELL sinyali geldiğinde
        close_position("BUY", symbol)  # Long pozisyonu kapat
        time.sleep(2)  # İşlemler arasında bekleme süresi
        open_position(SIDE_SELL, symbol)  # Short pozisyon aç

    return jsonify({"success": True}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
