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
ALLOWED_PAIRS = ["BTCUSDT", "XRPUSDT", "DOGEUSDT", "SOLUSDT", "SUIUSDT", "AVAXUSDT", "ALGOUSDT", "ADAUSDT", "LINKUSDT", "TRXUSDT", "FILUSDT", "DOTUSDT", "XLMUSDT", "ZENUSDT", "VETUSDT", "ZILUSDT", "JASMYUSDT", "HBARUSDT", "COOKIEUSDT", "CGPTUSDT", "MOVEUSDT", "WLDUSDT", "COWUSDT", "BIOUSDT", "AGLDUSDT", "LQTYUSDT", "DEXEUSDT", "PNUTUSDT", "GOATUSDT", "VIRTUALUSDT", "ZEREBROUSDT", "KAIAUSDT", "VVAIFUUSDT", "SONICUSDT", "VELODROMEUSDT", "VANAUSDT", "PENGUUSDT", "FETUSDT", "FARTCOINUSDT"
]  # İşlem yapmak istediğiniz çiftler

# Bot Settings
POSITION_SIZE_USDT = 40  # Her işlem için kullanılacak bakiye (dolar)
LEVERAGE = 10  # Kaldıraç oranı

# Set Logging
logging.basicConfig(level=logging.INFO)

# Set Leverage for All Pairs
def set_leverage(symbol):
    try:
        response = client.futures_change_leverage(symbol=symbol, leverage=LEVERAGE)
        logging.info(f"Leverage set to {LEVERAGE}x for {symbol}: {response}")
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
        # Coin fiyatını al
        price = float(client.futures_symbol_ticker(symbol=symbol)["price"])
        
        # İşlem miktarını hesapla (10 USDT)
        quantity = (POSITION_SIZE_USDT * LEVERAGE) / price
        
        # Coin miktarının Binance minimum miktarını kontrol et
        PRECISION, MIN_QUANTITY = get_symbol_precision(symbol)
        quantity = round(quantity, PRECISION)
        if quantity < MIN_QUANTITY:
            logging.error(f"Calculated quantity ({quantity}) is less than the minimum allowed for {symbol}.")
            return
        
        # Kaldıraç ayarını kontrol et
        set_leverage(symbol)
        
        # İşlem aç
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
    symbol = data.get("pair")  # Sinyaldeki işlem çifti (ör. BTCUSDT veya BTCUSDT.P)
    signal = data.get("signal")  # Sinyal türü (AL veya SAT)

    if not symbol or not signal:
        logging.error("Invalid signal or pair in webhook data.")
        return jsonify({"error": "Invalid data"}), 400

    # ".P" gibi ekleri temizle
    symbol = symbol.replace(".P", "")

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
    app.run(host="0.0.0.0", port=5001)
