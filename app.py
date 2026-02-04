from flask import Flask, jsonify, request
from flask_cors import CORS
from growwapi import GrowwAPI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# ===== PUT YOUR GROWW API TOKEN HERE =====
API_AUTH_TOKEN = os.getenv('GROWW_API_TOKEN', 'your_token_here')
# ==========================================

# Initialize Groww API
groww = GrowwAPI(API_AUTH_TOKEN)

# Popular stocks and indices
POPULAR_STOCKS = [
    {"symbol": "RELIANCE", "exchange": "NSE", "name": "Reliance Industries"},
    {"symbol": "TCS", "exchange": "NSE", "name": "Tata Consultancy Services"},
    {"symbol": "HDFCBANK", "exchange": "NSE", "name": "HDFC Bank"},
    {"symbol": "INFY", "exchange": "NSE", "name": "Infosys"},
    {"symbol": "ICICIBANK", "exchange": "NSE", "name": "ICICI Bank"},
    {"symbol": "HINDUNILVR", "exchange": "NSE", "name": "Hindustan Unilever"},
    {"symbol": "ITC", "exchange": "NSE", "name": "ITC Limited"},
    {"symbol": "SBIN", "exchange": "NSE", "name": "State Bank of India"},
    {"symbol": "BHARTIARTL", "exchange": "NSE", "name": "Bharti Airtel"},
    {"symbol": "KOTAKBANK", "exchange": "NSE", "name": "Kotak Mahindra Bank"}
]

MAJOR_INDICES = [
    {"symbol": "NIFTY", "exchange": "NSE", "name": "NIFTY 50"},
    {"symbol": "BANKNIFTY", "exchange": "NSE", "name": "BANK NIFTY"},
    {"symbol": "FINNIFTY", "exchange": "NSE", "name": "NIFTY FIN SERVICE"},
    {"symbol": "SENSEX", "exchange": "BSE", "name": "BSE SENSEX"},
    {"symbol": "BANKEX", "exchange": "BSE", "name": "BSE BANKEX"}
]

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Backend is running"})

@app.route('/api/popular-stocks', methods=['GET'])
def get_popular_stocks():
    try:
        results = []
        # Get LTP for all popular stocks
        symbols = [f"{stock['exchange']}_{stock['symbol']}" for stock in POPULAR_STOCKS]
        
        ltp_data = groww.get_ltp(
            segment=groww.SEGMENT_CASH,
            exchange_trading_symbols=tuple(symbols)
        )
        
        for stock in POPULAR_STOCKS:
            key = f"{stock['exchange']}_{stock['symbol']}"
            results.append({
                "symbol": stock['symbol'],
                "exchange": stock['exchange'],
                "name": stock['name'],
                "ltp": ltp_data.get(key, 0)
            })
        
        return jsonify({"success": True, "data": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/indices', methods=['GET'])
def get_indices():
    try:
        results = []
        symbols = [f"{index['exchange']}_{index['symbol']}" for index in MAJOR_INDICES]
        
        ltp_data = groww.get_ltp(
            segment=groww.SEGMENT_CASH,
            exchange_trading_symbols=tuple(symbols)
        )
        
        ohlc_data = groww.get_ohlc(
            segment=groww.SEGMENT_CASH,
            exchange_trading_symbols=tuple(symbols)
        )
        
        for index in MAJOR_INDICES:
            key = f"{index['exchange']}_{index['symbol']}"
            ohlc = ohlc_data.get(key, {})
            ltp = ltp_data.get(key, 0)
            
            change = 0
            change_perc = 0
            if ohlc.get('close', 0) != 0:
                change = ltp - ohlc.get('close', 0)
                change_perc = (change / ohlc.get('close', 0)) * 100
            
            results.append({
                "symbol": index['symbol'],
                "exchange": index['exchange'],
                "name": index['name'],
                "ltp": ltp,
                "open": ohlc.get('open', 0),
                "high": ohlc.get('high', 0),
                "low": ohlc.get('low', 0),
                "close": ohlc.get('close', 0),
                "change": change,
                "change_perc": change_perc
            })
        
        return jsonify({"success": True, "data": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/quote', methods=['GET'])
def get_quote():
    try:
        symbol = request.args.get('symbol')
        exchange = request.args.get('exchange', 'NSE')
        segment = request.args.get('segment', groww.SEGMENT_CASH)
        
        if not symbol:
            return jsonify({"success": False, "error": "Symbol is required"}), 400
        
        quote = groww.get_quote(
            exchange=exchange,
            segment=segment,
            trading_symbol=symbol
        )
        
        return jsonify({"success": True, "data": quote})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_stock():
    try:
        query = request.args.get('q', '').upper()
        
        if not query or len(query) < 2:
            return jsonify({"success": True, "data": []})
        
        # Simple search in popular stocks
        results = []
        for stock in POPULAR_STOCKS:
            if query in stock['symbol'] or query in stock['name'].upper():
                results.append(stock)
        
        return jsonify({"success": True, "data": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/option-chain', methods=['GET'])
def get_option_chain():
    try:
        underlying = request.args.get('underlying')
        exchange = request.args.get('exchange', 'NSE')
        expiry_date = request.args.get('expiry_date')
        
        if not underlying or not expiry_date:
            return jsonify({"success": False, "error": "Underlying and expiry_date are required"}), 400
        
        option_chain = groww.get_option_chain(
            exchange=exchange,
            underlying=underlying,
            expiry_date=expiry_date
        )
        
        return jsonify({"success": True, "data": option_chain})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/greeks', methods=['GET'])
def get_greeks():
    try:
        underlying = request.args.get('underlying')
        trading_symbol = request.args.get('trading_symbol')
        exchange = request.args.get('exchange', 'NSE')
        expiry = request.args.get('expiry')
        
        if not all([underlying, trading_symbol, expiry]):
            return jsonify({"success": False, "error": "All parameters are required"}), 400
        
        greeks = groww.get_greeks(
            exchange=exchange,
            underlying=underlying,
            trading_symbol=trading_symbol,
            expiry=expiry
        )
        
        return jsonify({"success": True, "data": greeks})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
