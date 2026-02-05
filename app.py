from flask import Flask, jsonify, request
from flask_cors import CORS
from growwapi import GrowwAPI
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta
from functools import lru_cache
import time

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# ===== CONFIGURATION =====
API_AUTH_TOKEN = (
    os.getenv("GROWW_API_TOKEN")
    or os.getenv("API_AUTH_TOKEN")
    or "your_token_here"
)

USER_API_KEY = os.getenv("USER_API_KEY") or os.getenv("user_api_key")
USER_SECRET = os.getenv("USER_SECRET") or os.getenv("user_secret")
USER_TOTP = os.getenv("USER_TOTP") or os.getenv("user_totp")

# PERFORMANCE: Cache configuration
CACHE_TIMEOUT = 5  # Cache data for 5 seconds (real-time feel)
cache = {}

def _looks_like_jwt(value: str) -> bool:
    return value.count(".") == 2 and value.startswith("ey")

def _resolve_groww_token():
    if API_AUTH_TOKEN and API_AUTH_TOKEN != "your_token_here":
        return API_AUTH_TOKEN
    if not USER_API_KEY:
        return None
    if USER_SECRET or USER_TOTP:
        try:
            totp = USER_TOTP if USER_TOTP else None
            secret = None if USER_TOTP else USER_SECRET
            return GrowwAPI.get_access_token(
                api_key=USER_API_KEY,
                totp=totp,
                secret=secret,
            )
        except Exception:
            app.logger.exception("Failed to exchange API key for access token")
            return USER_API_KEY
    return USER_API_KEY

# Initialize Groww API
groww = None
resolved_token = _resolve_groww_token()

try:
    if resolved_token:
        groww = GrowwAPI(resolved_token)
        app.logger.info("Initialized GrowwAPI with access token")
except Exception as e:
    app.logger.error(f"Groww API initialization failed: {e}")

if not groww:
    app.logger.warning("GrowwAPI FAILED — backend running in SAFE MODE")
    class SafeGroww:
        def __getattr__(self, name):
            def fallback(*args, **kwargs):
                return {}
            return fallback
    groww = SafeGroww()

# ==================== CACHING UTILITIES ====================

def get_cached(key, max_age=CACHE_TIMEOUT):
    """Get cached value if not expired"""
    if key in cache:
        value, timestamp = cache[key]
        if time.time() - timestamp < max_age:
            return value
    return None

def set_cache(key, value):
    """Set cache value with timestamp"""
    cache[key] = (value, time.time())

def clear_old_cache():
    """Clear cache entries older than 60 seconds"""
    current_time = time.time()
    keys_to_delete = []
    for key, (value, timestamp) in cache.items():
        if current_time - timestamp > 60:
            keys_to_delete.append(key)
    for key in keys_to_delete:
        del cache[key]

# ==================== STOCK DATA ====================

# Optimized popular stocks list (top 100)
POPULAR_STOCKS = [
    # Banking & Finance
    {"symbol": "HDFCBANK", "exchange": "NSE", "name": "HDFC Bank"},
    {"symbol": "ICICIBANK", "exchange": "NSE", "name": "ICICI Bank"},
    {"symbol": "SBIN", "exchange": "NSE", "name": "State Bank of India"},
    {"symbol": "KOTAKBANK", "exchange": "NSE", "name": "Kotak Mahindra Bank"},
    {"symbol": "AXISBANK", "exchange": "NSE", "name": "Axis Bank"},
    {"symbol": "INDUSINDBK", "exchange": "NSE", "name": "IndusInd Bank"},
    
    # IT Services
    {"symbol": "TCS", "exchange": "NSE", "name": "Tata Consultancy Services"},
    {"symbol": "INFY", "exchange": "NSE", "name": "Infosys"},
    {"symbol": "WIPRO", "exchange": "NSE", "name": "Wipro"},
    {"symbol": "HCLTECH", "exchange": "NSE", "name": "HCL Technologies"},
    {"symbol": "TECHM", "exchange": "NSE", "name": "Tech Mahindra"},
    
    # Oil & Gas
    {"symbol": "RELIANCE", "exchange": "NSE", "name": "Reliance Industries"},
    {"symbol": "ONGC", "exchange": "NSE", "name": "ONGC"},
    {"symbol": "BPCL", "exchange": "NSE", "name": "BPCL"},
    {"symbol": "IOC", "exchange": "NSE", "name": "Indian Oil Corporation"},
    
    # Telecom
    {"symbol": "BHARTIARTL", "exchange": "NSE", "name": "Bharti Airtel"},
    
    # FMCG
    {"symbol": "HINDUNILVR", "exchange": "NSE", "name": "Hindustan Unilever"},
    {"symbol": "ITC", "exchange": "NSE", "name": "ITC Limited"},
    {"symbol": "NESTLEIND", "exchange": "NSE", "name": "Nestle India"},
    {"symbol": "BRITANNIA", "exchange": "NSE", "name": "Britannia Industries"},
    
    # Automobile
    {"symbol": "MARUTI", "exchange": "NSE", "name": "Maruti Suzuki"},
    {"symbol": "TATAMOTORS", "exchange": "NSE", "name": "Tata Motors"},
    {"symbol": "M&M", "exchange": "NSE", "name": "Mahindra & Mahindra"},
    {"symbol": "BAJAJ-AUTO", "exchange": "NSE", "name": "Bajaj Auto"},
    
    # Pharma
    {"symbol": "SUNPHARMA", "exchange": "NSE", "name": "Sun Pharmaceutical"},
    {"symbol": "DRREDDY", "exchange": "NSE", "name": "Dr Reddy's Laboratories"},
    {"symbol": "CIPLA", "exchange": "NSE", "name": "Cipla"},
    
    # Metals
    {"symbol": "TATASTEEL", "exchange": "NSE", "name": "Tata Steel"},
    {"symbol": "JSWSTEEL", "exchange": "NSE", "name": "JSW Steel"},
    {"symbol": "HINDALCO", "exchange": "NSE", "name": "Hindalco Industries"},
    
    # Cement
    {"symbol": "ULTRACEMCO", "exchange": "NSE", "name": "UltraTech Cement"},
    
    # Power
    {"symbol": "NTPC", "exchange": "NSE", "name": "NTPC"},
    {"symbol": "POWERGRID", "exchange": "NSE", "name": "Power Grid Corporation"},
    
    # Infrastructure
    {"symbol": "LT", "exchange": "NSE", "name": "Larsen & Toubro"},
    {"symbol": "ADANIPORTS", "exchange": "NSE", "name": "Adani Ports"},
    
    # Consumer Durables
    {"symbol": "TITAN", "exchange": "NSE", "name": "Titan Company"},
]

MAJOR_INDICES = [
    {"symbol": "NIFTY", "exchange": "NSE", "name": "NIFTY 50"},
    {"symbol": "BANKNIFTY", "exchange": "NSE", "name": "BANK NIFTY"},
    {"symbol": "FINNIFTY", "exchange": "NSE", "name": "NIFTY FIN SERVICE"},
    {"symbol": "SENSEX", "exchange": "BSE", "name": "BSE SENSEX"},
]

# ==================== OPTIMIZED ENDPOINTS ====================

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Backend is running"}), 200

@app.route('/api/popular-stocks', methods=['GET'])
def get_popular_stocks():
    """OPTIMIZED: Popular stocks with aggressive caching"""
    try:
        cache_key = "popular_stocks"
        cached_data = get_cached(cache_key, max_age=3)  # 3 second cache
        
        if cached_data:
            return jsonify(cached_data), 200
        
        limit = request.args.get('limit', type=int, default=50)
        stocks = POPULAR_STOCKS[:limit]
        results = []
        
        # Batch request for better performance
        symbols = tuple([f"{s['exchange']}_{s['symbol']}" for s in stocks])
        
        try:
            ltp_data = groww.get_ltp(
                segment=groww.SEGMENT_CASH,
                exchange_trading_symbols=symbols
            )
            ohlc_data = groww.get_ohlc(
                segment=groww.SEGMENT_CASH,
                exchange_trading_symbols=symbols
            )
        except Exception as e:
            app.logger.error(f"API error: {e}")
            ltp_data = {}
            ohlc_data = {}
        
        for stock in stocks:
            key = f"{stock['exchange']}_{stock['symbol']}"
            ltp = ltp_data.get(key, 0)
            ohlc = ohlc_data.get(key, {})
            
            change = 0
            change_perc = 0
            close = ohlc.get('close', 0)
            if close != 0 and ltp:
                change = ltp - close
                change_perc = (change / close) * 100
            
            results.append({
                "symbol": stock['symbol'],
                "exchange": stock['exchange'],
                "name": stock['name'],
                "ltp": ltp,
                "open": ohlc.get('open', 0),
                "high": ohlc.get('high', 0),
                "low": ohlc.get('low', 0),
                "close": close,
                "change": change,
                "changePerc": change_perc
            })
        
        response_data = {"success": True, "data": results}
        set_cache(cache_key, response_data)
        
        return jsonify(response_data), 200
        
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/indices', methods=['GET'])
def get_indices():
    """OPTIMIZED: Indices with caching"""
    try:
        cache_key = "indices"
        cached_data = get_cached(cache_key, max_age=3)
        
        if cached_data:
            return jsonify(cached_data), 200
        
        results = []
        symbols = tuple([f"{idx['exchange']}_{idx['symbol']}" for idx in MAJOR_INDICES])
        
        ltp_data = groww.get_ltp(
            segment=groww.SEGMENT_CASH,
            exchange_trading_symbols=symbols
        )
        
        ohlc_data = groww.get_ohlc(
            segment=groww.SEGMENT_CASH,
            exchange_trading_symbols=symbols
        )
        
        for index in MAJOR_INDICES:
            key = f"{index['exchange']}_{index['symbol']}"
            ohlc = ohlc_data.get(key, {})
            ltp = ltp_data.get(key, 0)
            
            change = 0
            change_perc = 0
            close = ohlc.get('close', 0)
            if close != 0:
                change = ltp - close
                change_perc = (change / close) * 100
            
            results.append({
                "symbol": index['symbol'],
                "exchange": index['exchange'],
                "name": index['name'],
                "ltp": ltp,
                "open": ohlc.get('open', 0),
                "high": ohlc.get('high', 0),
                "low": ohlc.get('low', 0),
                "close": close,
                "change": change,
                "changePerc": change_perc
            })
        
        response_data = {"success": True, "data": results}
        set_cache(cache_key, response_data)
        
        return jsonify(response_data), 200
        
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/quote', methods=['GET'])
def get_quote():
    """OPTIMIZED: Quote with minimal caching (2 seconds)"""
    try:
        symbol = request.args.get('symbol')
        exchange = request.args.get('exchange', 'NSE')
        segment = request.args.get('segment', groww.SEGMENT_CASH)
        
        if not symbol:
            return jsonify({"success": False, "error": "Symbol required"}), 400
        
        cache_key = f"quote_{symbol}_{exchange}_{segment}"
        cached_data = get_cached(cache_key, max_age=2)  # 2 second cache
        
        if cached_data:
            return jsonify(cached_data), 200
        
        quote = groww.get_quote(
            exchange=exchange,
            segment=segment,
            trading_symbol=symbol
        )
        
        response_data = {"success": True, "data": quote}
        set_cache(cache_key, response_data)
        
        return jsonify(response_data), 200
        
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_stock():
    """OPTIMIZED: Fast search with no API calls"""
    try:
        query = request.args.get('q', '').upper()
        
        if not query or len(query) < 2:
            return jsonify({"success": True, "data": []}), 200
        
        results = []
        for stock in POPULAR_STOCKS:
            if query in stock['symbol'] or query in stock['name'].upper():
                results.append(stock)
                if len(results) >= 20:
                    break
        
        return jsonify({"success": True, "data": results}), 200
        
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/option-chain', methods=['GET'])
def get_option_chain():
    """OPTIMIZED: Option chain with caching"""
    try:
        underlying = request.args.get('underlying')
        exchange = request.args.get('exchange', 'NSE')
        expiry_date = request.args.get('expiry_date')
        
        if not underlying:
            return jsonify({"success": False, "error": "Underlying required"}), 400
        
        cache_key = f"optchain_{underlying}_{expiry_date}"
        cached_data = get_cached(cache_key, max_age=5)
        
        if cached_data:
            return jsonify(cached_data), 200
        
        try:
            if not expiry_date:
                expiries = groww.get_expiry_dates(
                    exchange=exchange,
                    underlying=underlying
                )
                if expiries:
                    expiry_date = expiries[0]
                else:
                    return jsonify({
                        "success": False, 
                        "error": "No expiry dates found"
                    }), 404
            
            option_chain = groww.get_option_chain(
                exchange=exchange,
                underlying=underlying,
                expiry_date=expiry_date
            )
            
            response_data = {
                "success": True, 
                "data": option_chain,
                "expiry_date": expiry_date
            }
            set_cache(cache_key, response_data)
            
            return jsonify(response_data), 200
            
        except Exception as api_error:
            app.logger.error(f"API error: {api_error}")
            return jsonify({
                "success": False,
                "error": "Option chain data unavailable"
            }), 500
            
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== CLEANUP ====================

@app.before_request
def before_request():
    """Clear old cache before each request"""
    if len(cache) > 100:  # Prevent cache from growing too large
        clear_old_cache()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
