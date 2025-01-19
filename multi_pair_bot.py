import os
from flask import Flask, request, jsonify
from binance.client import Client
from binance.enums import *
import logging

# Flask App
app = Flask(__name__)

# Binance API Keys from Environment Variables
API_KEY = os.getenv("API_KEY")
API_SECRET = os.getenv("API_SECRET")

# Binance Client
client = Client(API_KEY, API_SECRET)

# İşleme Girecek Coin Çiftleri
AALLOWED_PAIRS = ["BTCUSDT", "XRPUSDT", "DOGEUSDT", "SOLUSDT", "COWUSDT", "1000SHIBUSDT", "1000BONKUSDT", "FARTCOINUSDT", "1000PEPEUSDT", "JUPUSDT", "DEXEUSDT", "ALGOUSDT", "ADAUSDT", "LINKUSDT", "TRXUSDT", "FILUSDT", "DOTUSDT", "XLMUSDT", "ZENUSDT", "VETUSDT", "ZILUSDT", "JASMYUSDT", "HBARUSDT", "COOKIEUSDT", "CGPTUSDT", "MOVEUSDT", "WLDUSDT", "COWUSDT", "BIOUSDT", "AGLDUSDT", "LQTYUSDT", "DEXEUSDT", "PNUTUSDT", "GOATUSDT", "VIRTUALUSDT", "ZEREBROUSDT", "1000SHIBUSDT", "VVAIFUUSDT", "SONICUSDT", "VELODROMEUSDT", "VANAUSDT", "PENGUUSDT", "FETUSDT", "FARTCOINUSDT"
]  # İşlem yapmak istediğiniz çiftler

# Bot Settings
POSITION_SIZE_USDT = 10  # Her işlem için kullanılacak bakiye (dolar)
LEVERAGE = 15  # Kaldıraç oranı
STOP_LOSS_PERCENT = 0.006  # %0.6 zarar stop-loss
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

# Open Long Position with Stop Loss and Take Profit
def open_long_position_with_stop_and_take_profit(symbol):
    try:
        # Get current price
        entry_price = float(client.futures_symbol_ticker(symbol=symbol)["price"])

        # Calculate quantity
        quantity = (POSITION_SIZE_USDT * LEVERAGE) / entry_price
        precision, min_qty = get_symbol_precision(symbol)
        quantity = max(round(quantity, precision), min_qty)

        # Open long position
        set_leverage(symbol)
        client.futures_create_order(
            symbol=symbol,
            side=SIDE_BUY,
            type=ORDER_TYPE_MARKET,
            quantity=quantity,
        )
        logging.info(f"Long position opened for {symbol} with quantity {quantity}.")

        # Place stop loss and take profit orders
        stop_loss_price = entry_price * (1 - STOP_LOSS_PERCENT)
        take_profit_price = entry_price * (1 + TAKE_PROFIT_PERCENT)

        client.futures_create_order(
            symbol=symbol,
            side=SIDE_SELL,
            type=ORDER_TYPE_STOP_MARKET,
            stopPrice=round(stop_loss_price, precision),
            quantity=quantity,
        )
        logging.info(f"Stop loss set at {stop_loss_price} for {symbol}.")

        client.futures_create_order(
            symbol=symbol,
            side=SIDE_SELL,
            type=ORDER_TYPE_LIMIT,
            price=round(take_profit_price, precision),
            timeInForce=TIME_IN_FORCE_GTC,
            quantity=quantity,
        )
        logging.info(f"Take profit set at {take_profit_price} for {symbol}.")

    except Exception as e:
        logging.error(f"Error opening position for {symbol}: {e}")

# Close Long Position
def close_long_position(symbol):
    try:
        # Get current position quantity
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
                logging.info(f"Long position closed for {symbol} with quantity {quantity}.")
                return
        logging.info(f"No long position to close for {symbol}.")
    except Exception as e:
        logging.error(f"Error closing long position for {symbol}: {e}")

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

    if signal == "SAT":
        close_long_position(symbol)
        logging.info(f"SELL signal received for {symbol}. Long position closed.")
    elif signal == "AL":
        open_long_position_with_stop_and_take_profit(symbol)
        logging.info(f"BUY signal received for {symbol}. Long position opened with stop loss and take profit.")

    return jsonify({"success": True}), 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
