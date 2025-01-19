import os
from flask import Flask, request, jsonify
from binance.client import Client
from binance.enums import *
import logging
import time

# Flask App
app = Flask(__name__)

# Binance API Keys from Environment Variables
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# Binance Client
client = Client(API_KEY, API_SECRET)

# İşleme Girecek Coin Çiftleri
ALLOWED_PAIRS = ["BTCUSDT", "XRPUSDT", "DOGEUSDT", "SOLUSDT", "SUIUSDT", "1000SHIBUSDT", "AVAXUSDT", "FARTCOINUSDT", "1000PEPEUSDT", "KOMAUSDT", "TURBOUSDT", "ALGOUSDT", "ADAUSDT", "LINKUSDT", "TRXUSDT", "FILUSDT", "DOTUSDT", "XLMUSDT", "ZENUSDT", "VETUSDT", "ZILUSDT", "JASMYUSDT", "HBARUSDT", "COOKIEUSDT", "CGPTUSDT", "MOVEUSDT", "WLDUSDT", "COWUSDT", "BIOUSDT", "AGLDUSDT", "LQTYUSDT", "DEXEUSDT", "PNUTUSDT", "GOATUSDT", "VIRTUALUSDT", "ZEREBROUSDT", "1000SHIBUSDT", "VVAIFUUSDT", "SONICUSDT", "VELODROMEUSDT", "VANAUSDT", "PENGUUSDT", "FETUSDT", "FARTCOINUSDT"
]  # İşlem yapmak istediğiniz çiftler

# Bot Settings
POSITION_SIZE_USDT = 10  # Her işlem için kullanılacak bakiye (dolar)
LEVERAGE = 15  # Kaldıraç oranı
STOP_LOSS_PERCENT = 0.02  # %2 zarar stop-loss
TAKE_PROFIT_PERCENT = 0.05  # %5 kâr take-profit

# Logging Settings
logging.basicConfig(level=logging.INFO)

# Get Symbol Precision
def get_symbol_precision(symbol):
    exchange_info = client.futures_exchange_info()
    for symbol_info in exchange_info['symbols']:
        if symbol_info['symbol'] == symbol:
            for f in symbol_info['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    return int(f['stepSize'].find('1') - 1), float(f['minQty'])
    return 2, 0.1

# Set Leverage for All Pairs
def set_leverage(symbol):
    try:
        response = client.futures_change_leverage(symbol=symbol, leverage=LEVERAGE)
        logging.info(f"Leverage set to {LEVERAGE}x for {symbol}: {response}")
    except Exception as e:
        logging.error(f"Error setting leverage for {symbol}: {e}")

# Open Long Position
def open_long_position(symbol):
    try:
        price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        
        # İşlem miktarını hesapla
        quantity = (POSITION_SIZE_USDT * LEVERAGE) / price

        # Minimum miktar kontrolü
        precision, min_qty = get_symbol_precision(symbol)
        quantity = max(round(quantity, precision), min_qty)
        
        set_leverage(symbol)
        order = client.futures_create_order(
            symbol=symbol,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
        )
        logging.info(f"Long position opened for {symbol}: {order}")

        # Stop-loss ve take-profit emirleri ekle
        stop_loss_price = round(price * (1 - STOP_LOSS_PERCENT), 2)
        take_profit_price = round(price * (1 + TAKE_PROFIT_PERCENT), 2)

        client.futures_create_order(
            symbol=symbol,
            side=SIDE_SELL,
            type=ORDER_TYPE_STOP_MARKET,
            stopPrice=stop_loss_price,
            quantity=quantity,
        )
        logging.info(f"Stop-loss set at {stop_loss_price} for {symbol}")

        client.futures_create_order(
            symbol=symbol,
            side=SIDE_SELL,
            type=ORDER_TYPE_LIMIT,
            price=take_profit_price,
            timeInForce="GTC",
            quantity=quantity,
        )
        logging.info(f"Take-profit set at {take_profit_price} for {symbol}")

    except Exception as e:
        logging.error(f"Error opening long position for {symbol}: {e}")

# Webhook Route
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    symbol = data.get("pair")
    signal = data.get("signal")

    if not symbol or not signal:
        logging.error("Invalid data received.")
        return jsonify({"error": "Invalid data"}), 400

    if symbol not in ALLOWED_PAIRS:
        logging.error(f"Pair {symbol} is not allowed.")
        return jsonify({"error": "Pair not allowed"}), 400

    if signal == "AL":
        open_long_position(symbol)
    elif signal == "SAT":
        logging.info(f"SELL signal received for {symbol}, but short positions are disabled.")

    return jsonify({"success": True}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
