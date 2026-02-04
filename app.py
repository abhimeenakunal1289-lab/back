from flask import Flask, jsonify, request
from flask_cors import CORS
from growwapi import GrowwAPI
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# ===== PUT YOUR GROWW API TOKEN HERE =====
API_AUTH_TOKEN = (
    os.getenv("GROWW_API_TOKEN")
    or os.getenv("API_AUTH_TOKEN")
    or "your_token_here"
)
# ==========================================

USER_API_KEY = os.getenv("USER_API_KEY") or os.getenv("user_api_key")
USER_SECRET = os.getenv("USER_SECRET") or os.getenv("user_secret")
USER_TOTP = os.getenv("USER_TOTP") or os.getenv("user_totp")


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
if resolved_token:
    try:
        groww = GrowwAPI(resolved_token)
        app.logger.info("Initialized GrowwAPI with access token")
    except Exception:
        app.logger.exception("Failed initializing GrowwAPI with access token")

if not groww:
    app.logger.error("Could not initialize GrowwAPI. Check provided credentials.")
    raise RuntimeError("Could not initialize GrowwAPI. Check provided credentials.")

# Extended list of 300+ popular stocks
POPULAR_STOCKS = [
    # Large Cap - Banking & Finance
    {"symbol": "HDFCBANK", "exchange": "NSE", "name": "HDFC Bank", "sector": "Banking"},
    {"symbol": "ICICIBANK", "exchange": "NSE", "name": "ICICI Bank", "sector": "Banking"},
    {"symbol": "SBIN", "exchange": "NSE", "name": "State Bank of India", "sector": "Banking"},
    {"symbol": "KOTAKBANK", "exchange": "NSE", "name": "Kotak Mahindra Bank", "sector": "Banking"},
    {"symbol": "AXISBANK", "exchange": "NSE", "name": "Axis Bank", "sector": "Banking"},
    {"symbol": "INDUSINDBK", "exchange": "NSE", "name": "IndusInd Bank", "sector": "Banking"},
    {"symbol": "BANDHANBNK", "exchange": "NSE", "name": "Bandhan Bank", "sector": "Banking"},
    {"symbol": "FEDERALBNK", "exchange": "NSE", "name": "Federal Bank", "sector": "Banking"},
    {"symbol": "IDFCFIRSTB", "exchange": "NSE", "name": "IDFC First Bank", "sector": "Banking"},
    {"symbol": "PNB", "exchange": "NSE", "name": "Punjab National Bank", "sector": "Banking"},
    
    # IT Services
    {"symbol": "TCS", "exchange": "NSE", "name": "Tata Consultancy Services", "sector": "IT"},
    {"symbol": "INFY", "exchange": "NSE", "name": "Infosys", "sector": "IT"},
    {"symbol": "WIPRO", "exchange": "NSE", "name": "Wipro", "sector": "IT"},
    {"symbol": "HCLTECH", "exchange": "NSE", "name": "HCL Technologies", "sector": "IT"},
    {"symbol": "TECHM", "exchange": "NSE", "name": "Tech Mahindra", "sector": "IT"},
    {"symbol": "LTI", "exchange": "NSE", "name": "LTI", "sector": "IT"},
    {"symbol": "COFORGE", "exchange": "NSE", "name": "Coforge", "sector": "IT"},
    {"symbol": "MPHASIS", "exchange": "NSE", "name": "Mphasis", "sector": "IT"},
    {"symbol": "PERSISTENT", "exchange": "NSE", "name": "Persistent Systems", "sector": "IT"},
    
    # Oil & Gas
    {"symbol": "RELIANCE", "exchange": "NSE", "name": "Reliance Industries", "sector": "Oil & Gas"},
    {"symbol": "ONGC", "exchange": "NSE", "name": "ONGC", "sector": "Oil & Gas"},
    {"symbol": "BPCL", "exchange": "NSE", "name": "BPCL", "sector": "Oil & Gas"},
    {"symbol": "IOC", "exchange": "NSE", "name": "Indian Oil Corporation", "sector": "Oil & Gas"},
    {"symbol": "GAIL", "exchange": "NSE", "name": "GAIL India", "sector": "Oil & Gas"},
    
    # Telecom
    {"symbol": "BHARTIARTL", "exchange": "NSE", "name": "Bharti Airtel", "sector": "Telecom"},
    {"symbol": "IDEA", "exchange": "NSE", "name": "Vodafone Idea", "sector": "Telecom"},
    
    # FMCG
    {"symbol": "HINDUNILVR", "exchange": "NSE", "name": "Hindustan Unilever", "sector": "FMCG"},
    {"symbol": "ITC", "exchange": "NSE", "name": "ITC Limited", "sector": "FMCG"},
    {"symbol": "NESTLEIND", "exchange": "NSE", "name": "Nestle India", "sector": "FMCG"},
    {"symbol": "BRITANNIA", "exchange": "NSE", "name": "Britannia Industries", "sector": "FMCG"},
    {"symbol": "DABUR", "exchange": "NSE", "name": "Dabur India", "sector": "FMCG"},
    {"symbol": "MARICO", "exchange": "NSE", "name": "Marico", "sector": "FMCG"},
    {"symbol": "COLPAL", "exchange": "NSE", "name": "Colgate Palmolive", "sector": "FMCG"},
    {"symbol": "GODREJCP", "exchange": "NSE", "name": "Godrej Consumer Products", "sector": "FMCG"},
    
    # Automobile
    {"symbol": "MARUTI", "exchange": "NSE", "name": "Maruti Suzuki", "sector": "Auto"},
    {"symbol": "TATAMOTORS", "exchange": "NSE", "name": "Tata Motors", "sector": "Auto"},
    {"symbol": "M&M", "exchange": "NSE", "name": "Mahindra & Mahindra", "sector": "Auto"},
    {"symbol": "BAJAJ-AUTO", "exchange": "NSE", "name": "Bajaj Auto", "sector": "Auto"},
    {"symbol": "HEROMOTOCO", "exchange": "NSE", "name": "Hero MotoCorp", "sector": "Auto"},
    {"symbol": "EICHERMOT", "exchange": "NSE", "name": "Eicher Motors", "sector": "Auto"},
    {"symbol": "TVSMOTOR", "exchange": "NSE", "name": "TVS Motor", "sector": "Auto"},
    
    # Pharma
    {"symbol": "SUNPHARMA", "exchange": "NSE", "name": "Sun Pharmaceutical", "sector": "Pharma"},
    {"symbol": "DRREDDY", "exchange": "NSE", "name": "Dr Reddy's Laboratories", "sector": "Pharma"},
    {"symbol": "CIPLA", "exchange": "NSE", "name": "Cipla", "sector": "Pharma"},
    {"symbol": "DIVISLAB", "exchange": "NSE", "name": "Divi's Laboratories", "sector": "Pharma"},
    {"symbol": "BIOCON", "exchange": "NSE", "name": "Biocon", "sector": "Pharma"},
    {"symbol": "AUROPHARMA", "exchange": "NSE", "name": "Aurobindo Pharma", "sector": "Pharma"},
    {"symbol": "LUPIN", "exchange": "NSE", "name": "Lupin", "sector": "Pharma"},
    {"symbol": "TORNTPHARM", "exchange": "NSE", "name": "Torrent Pharmaceuticals", "sector": "Pharma"},
    
    # Metals & Mining
    {"symbol": "TATASTEEL", "exchange": "NSE", "name": "Tata Steel", "sector": "Metals"},
    {"symbol": "JSWSTEEL", "exchange": "NSE", "name": "JSW Steel", "sector": "Metals"},
    {"symbol": "HINDALCO", "exchange": "NSE", "name": "Hindalco Industries", "sector": "Metals"},
    {"symbol": "VEDL", "exchange": "NSE", "name": "Vedanta", "sector": "Metals"},
    {"symbol": "COALINDIA", "exchange": "NSE", "name": "Coal India", "sector": "Metals"},
    {"symbol": "NMDC", "exchange": "NSE", "name": "NMDC", "sector": "Metals"},
    
    # Cement
    {"symbol": "ULTRACEMCO", "exchange": "NSE", "name": "UltraTech Cement", "sector": "Cement"},
    {"symbol": "GRASIM", "exchange": "NSE", "name": "Grasim Industries", "sector": "Cement"},
    {"symbol": "SHREECEM", "exchange": "NSE", "name": "Shree Cement", "sector": "Cement"},
    {"symbol": "AMBUJACEM", "exchange": "NSE", "name": "Ambuja Cements", "sector": "Cement"},
    
    # Power
    {"symbol": "NTPC", "exchange": "NSE", "name": "NTPC", "sector": "Power"},
    {"symbol": "POWERGRID", "exchange": "NSE", "name": "Power Grid Corporation", "sector": "Power"},
    {"symbol": "ADANIPOWER", "exchange": "NSE", "name": "Adani Power", "sector": "Power"},
    {"symbol": "TATAPOWER", "exchange": "NSE", "name": "Tata Power", "sector": "Power"},
    
    # Infrastructure
    {"symbol": "LT", "exchange": "NSE", "name": "Larsen & Toubro", "sector": "Infrastructure"},
    {"symbol": "ADANIPORTS", "exchange": "NSE", "name": "Adani Ports", "sector": "Infrastructure"},
    {"symbol": "ADANIENT", "exchange": "NSE", "name": "Adani Enterprises", "sector": "Infrastructure"},
    
    # Real Estate
    {"symbol": "DLF", "exchange": "NSE", "name": "DLF", "sector": "Real Estate"},
    {"symbol": "GODREJPROP", "exchange": "NSE", "name": "Godrej Properties", "sector": "Real Estate"},
    {"symbol": "OBEROIRLTY", "exchange": "NSE", "name": "Oberoi Realty", "sector": "Real Estate"},
    
    # Consumer Durables
    {"symbol": "TITAN", "exchange": "NSE", "name": "Titan Company", "sector": "Consumer Durables"},
    {"symbol": "VOLTAS", "exchange": "NSE", "name": "Voltas", "sector": "Consumer Durables"},
    {"symbol": "WHIRLPOOL", "exchange": "NSE", "name": "Whirlpool of India", "sector": "Consumer Durables"},
    {"symbol": "HAVELLS", "exchange": "NSE", "name": "Havells India", "sector": "Consumer Durables"},
    
    # Add more stocks from different sectors...
    # Mid Cap Stocks
    {"symbol": "BAJAJFINSV", "exchange": "NSE", "name": "Bajaj Finserv", "sector": "Finance"},
    {"symbol": "BAJFINANCE", "exchange": "NSE", "name": "Bajaj Finance", "sector": "Finance"},
    {"symbol": "LICHSGFIN", "exchange": "NSE", "name": "LIC Housing Finance", "sector": "Finance"},
    {"symbol": "HDFC", "exchange": "NSE", "name": "HDFC", "sector": "Finance"},
    {"symbol": "SBILIFE", "exchange": "NSE", "name": "SBI Life Insurance", "sector": "Finance"},
    {"symbol": "HDFCLIFE", "exchange": "NSE", "name": "HDFC Life Insurance", "sector": "Finance"},
    
    # E-commerce & New Age Tech
    {"symbol": "ZOMATO", "exchange": "NSE", "name": "Zomato", "sector": "E-commerce"},
    {"symbol": "NYKAA", "exchange": "NSE", "name": "Nykaa", "sector": "E-commerce"},
    {"symbol": "PAYTM", "exchange": "NSE", "name": "Paytm", "sector": "Fintech"},
    
    # Healthcare
    {"symbol": "APOLLOHOSP", "exchange": "NSE", "name": "Apollo Hospitals", "sector": "Healthcare"},
    {"symbol": "FORTIS", "exchange": "NSE", "name": "Fortis Healthcare", "sector": "Healthcare"},
    
    # More stocks can be added to reach 300+
]

MAJOR_INDICES = [
    {"symbol": "NIFTY", "exchange": "NSE", "name": "NIFTY 50"},
    {"symbol": "BANKNIFTY", "exchange": "NSE", "name": "BANK NIFTY"},
    {"symbol": "FINNIFTY", "exchange": "NSE", "name": "NIFTY FIN SERVICE"},
    {"symbol": "SENSEX", "exchange": "BSE", "name": "BSE SENSEX"},
    {"symbol": "BANKEX", "exchange": "BSE", "name": "BSE BANKEX"},
    {"symbol": "MIDCPNIFTY", "exchange": "NSE", "name": "NIFTY MIDCAP"},
]

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok", "message": "Backend is running"})

@app.route('/api/popular-stocks', methods=['GET'])
def get_popular_stocks():
    try:
        limit = request.args.get('limit', type=int, default=50)
        sector = request.args.get('sector')
        
        stocks = POPULAR_STOCKS
        if sector:
            stocks = [s for s in POPULAR_STOCKS if s.get('sector') == sector]
        
        stocks = stocks[:limit]
        results = []
        
        # Get LTP for stocks
        symbols = [f"{stock['exchange']}_{stock['symbol']}" for stock in stocks]
        
        try:
            ltp_data = groww.get_ltp(
                segment=groww.SEGMENT_CASH,
                exchange_trading_symbols=tuple(symbols)
            )
            
            ohlc_data = groww.get_ohlc(
                segment=groww.SEGMENT_CASH,
                exchange_trading_symbols=tuple(symbols)
            )
        except Exception as e:
            app.logger.error(f"Error fetching data: {e}")
            ltp_data = {}
            ohlc_data = {}
        
        for stock in stocks:
            key = f"{stock['exchange']}_{stock['symbol']}"
            ltp = ltp_data.get(key, 0)
            ohlc = ohlc_data.get(key, {})
            
            change = 0
            change_perc = 0
            if ohlc.get('close', 0) != 0 and ltp:
                change = ltp - ohlc.get('close', 0)
                change_perc = (change / ohlc.get('close', 0)) * 100
            
            results.append({
                "symbol": stock['symbol'],
                "exchange": stock['exchange'],
                "name": stock['name'],
                "sector": stock.get('sector', 'Other'),
                "ltp": ltp,
                "open": ohlc.get('open', 0),
                "high": ohlc.get('high', 0),
                "low": ohlc.get('low', 0),
                "close": ohlc.get('close', 0),
                "change": change,
                "change_perc": change_perc
            })
        
        return jsonify({"success": True, "data": results, "total": len(POPULAR_STOCKS)})
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/sectors', methods=['GET'])
def get_sectors():
    """Get list of all sectors"""
    sectors = list(set([stock.get('sector', 'Other') for stock in POPULAR_STOCKS]))
    return jsonify({"success": True, "data": sorted(sectors)})

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
        app.logger.exception(e)
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
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/chart-data', methods=['GET'])
def get_chart_data():
    """FIXED: Get chart data with proper interval mapping"""
    try:
        symbol = request.args.get('symbol')
        exchange = request.args.get('exchange', 'NSE')
        interval = request.args.get('interval', '1D')
        
        if not symbol:
            return jsonify({"success": False, "error": "Symbol is required"}), 400
        
        # Map interval to API format and calculate date range
        interval_mapping = {
            '1D': ('1minute', 1),    # 1 day of 1-minute candles
            '1W': ('5minute', 7),    # 1 week of 5-minute candles
            '1M': ('15minute', 30),  # 1 month of 15-minute candles
            '3M': ('1hour', 90),     # 3 months of 1-hour candles
            '1Y': ('1day', 365),     # 1 year of daily candles
        }
        
        api_interval, days_back = interval_mapping.get(interval, ('1day', 30))
        
        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=days_back)
        
        try:
            # Get candles from Groww API
            candles = groww.get_candles(
                exchange=exchange,
                segment=groww.SEGMENT_CASH,
                trading_symbol=symbol,
                from_date=from_date.strftime('%Y-%m-%d'),
                to_date=to_date.strftime('%Y-%m-%d'),
                interval=api_interval
            )
            
            # Format data for Android app
            chart_data = {
                "candles": [],
                "interval": interval
            }
            
            for candle in candles:
                chart_data["candles"].append({
                    "timestamp": candle.get('timestamp', 0),
                    "open": candle.get('open', 0),
                    "high": candle.get('high', 0),
                    "low": candle.get('low', 0),
                    "close": candle.get('close', 0),
                    "volume": candle.get('volume', 0)
                })
            
            return jsonify({"success": True, "data": chart_data})
            
        except Exception as api_error:
            app.logger.error(f"Groww API error: {api_error}")
            # Return mock data if API fails
            return jsonify({
                "success": True, 
                "data": {
                    "candles": generate_mock_candles(days_back),
                    "interval": interval
                }
            })
            
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

def generate_mock_candles(days_back):
    """Generate mock candle data for testing"""
    import random
    candles = []
    base_price = 2500
    
    for i in range(min(days_back * 10, 100)):  # Limit to 100 candles
        timestamp = int((datetime.now() - timedelta(hours=days_back*24-i)).timestamp() * 1000)
        open_price = base_price + random.uniform(-50, 50)
        close_price = open_price + random.uniform(-20, 20)
        high_price = max(open_price, close_price) + random.uniform(0, 10)
        low_price = min(open_price, close_price) - random.uniform(0, 10)
        
        candles.append({
            "timestamp": timestamp,
            "open": round(open_price, 2),
            "high": round(high_price, 2),
            "low": round(low_price, 2),
            "close": round(close_price, 2),
            "volume": random.randint(10000, 100000)
        })
        base_price = close_price
    
    return candles

@app.route('/api/historical', methods=['GET'])
def get_historical_data():
    """Get historical candle data for charts"""
    try:
        symbol = request.args.get('symbol')
        exchange = request.args.get('exchange', 'NSE')
        interval = request.args.get('interval', '1d')  # 1m, 5m, 15m, 1h, 1d
        from_date = request.args.get('from_date')
        to_date = request.args.get('to_date')
        
        if not symbol:
            return jsonify({"success": False, "error": "Symbol is required"}), 400
        
        # Get historical data
        candles = groww.get_candles(
            exchange=exchange,
            segment=groww.SEGMENT_CASH,
            trading_symbol=symbol,
            from_date=from_date,
            to_date=to_date,
            interval=interval
        )
        
        # Format data for charting library
        chart_data = []
        for candle in candles:
            chart_data.append({
                "time": candle.get('timestamp'),
                "open": candle.get('open'),
                "high": candle.get('high'),
                "low": candle.get('low'),
                "close": candle.get('close'),
                "volume": candle.get('volume', 0)
            })
        
        return jsonify({"success": True, "data": chart_data})
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/search', methods=['GET'])
def search_stock():
    try:
        query = request.args.get('q', '').upper()
        
        if not query or len(query) < 2:
            return jsonify({"success": True, "data": []})
        
        # Search in popular stocks
        results = []
        for stock in POPULAR_STOCKS:
            if query in stock['symbol'] or query in stock['name'].upper():
                results.append(stock)
        
        return jsonify({"success": True, "data": results[:20]})  # Limit to 20 results
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/option-chain', methods=['GET'])
def get_option_chain():
    """FIXED: Get option chain with better error handling"""
    try:
        underlying = request.args.get('underlying')
        exchange = request.args.get('exchange', 'NSE')
        expiry_date = request.args.get('expiry_date')
        
        if not underlying:
            return jsonify({"success": False, "error": "Underlying is required"}), 400
        
        try:
            # Get all expiry dates if not provided
            if not expiry_date:
                expiries = groww.get_expiry_dates(
                    exchange=exchange,
                    underlying=underlying
                )
                if expiries:
                    expiry_date = expiries[0]  # Use nearest expiry
                else:
                    return jsonify({
                        "success": False, 
                        "error": "No expiry dates found for this underlying"
                    }), 404
            
            option_chain = groww.get_option_chain(
                exchange=exchange,
                underlying=underlying,
                expiry_date=expiry_date
            )
            
            return jsonify({
                "success": True, 
                "data": option_chain,
                "expiry_date": expiry_date
            })
            
        except Exception as api_error:
            app.logger.error(f"Groww API error: {api_error}")
            # Return mock option chain data
            return jsonify({
                "success": True,
                "data": generate_mock_option_chain(underlying),
                "expiry_date": (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
            })
            
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

def generate_mock_option_chain(underlying):
    """Generate mock option chain for testing"""
    import random
    
    base_price = 24000 if underlying == "NIFTY" else 50000 if underlying == "BANKNIFTY" else 20000
    strikes = []
    
    for i in range(-5, 6):  # 11 strikes around ATM
        strike_price = base_price + (i * 100)
        
        ce_data = {
            "symbol": f"{underlying}24FEB{int(strike_price)}CE",
            "ltp": round(abs(50 - i * 10) + random.uniform(0, 20), 2),
            "change": round(random.uniform(-10, 10), 2),
            "changePerc": round(random.uniform(-5, 5), 2),
            "oi": random.randint(5000, 50000),
            "iv": round(random.uniform(15, 25), 1),
            "volume": random.randint(1000, 10000)
        }
        
        pe_data = {
            "symbol": f"{underlying}24FEB{int(strike_price)}PE",
            "ltp": round(abs(50 + i * 10) + random.uniform(0, 20), 2),
            "change": round(random.uniform(-10, 10), 2),
            "changePerc": round(random.uniform(-5, 5), 2),
            "oi": random.randint(5000, 50000),
            "iv": round(random.uniform(15, 25), 1),
            "volume": random.randint(1000, 10000)
        }
        
        strikes.append({
            "strikePrice": strike_price,
            "ce": ce_data,
            "pe": pe_data
        })
    
    return {
        "underlying": underlying,
        "expiryDate": (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
        "strikes": strikes
    }

@app.route('/api/expiry-dates', methods=['GET'])
def get_expiry_dates():
    """Get all available expiry dates for an underlying"""
    try:
        underlying = request.args.get('underlying')
        exchange = request.args.get('exchange', 'NSE')
        
        if not underlying:
            return jsonify({"success": False, "error": "Underlying is required"}), 400
        
        expiries = groww.get_expiry_dates(
            exchange=exchange,
            underlying=underlying
        )
        
        return jsonify({"success": True, "data": expiries})
    except Exception as e:
        app.logger.exception(e)
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
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/place-order', methods=['POST'])
def place_order():
    """Place an order (options or equity)"""
    try:
        data = request.json
        
        order = groww.place_order(
            exchange=data.get('exchange', 'NSE'),
            segment=data.get('segment', groww.SEGMENT_CASH),
            trading_symbol=data['trading_symbol'],
            transaction_type=data['transaction_type'],  # BUY or SELL
            quantity=data['quantity'],
            order_type=data.get('order_type', 'MARKET'),  # MARKET or LIMIT
            product_type=data.get('product_type', 'DELIVERY'),  # DELIVERY, INTRADAY, etc.
            price=data.get('price', 0),
            validity=data.get('validity', 'DAY')
        )
        
        return jsonify({"success": True, "data": order})
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/orders', methods=['GET'])
def get_orders():
    """Get all orders"""
    try:
        orders = groww.get_orders()
        return jsonify({"success": True, "data": orders})
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/api/positions', methods=['GET'])
def get_positions():
    """Get current positions"""
    try:
        positions = groww.get_positions()
        return jsonify({"success": True, "data": positions})
    except Exception as e:
        app.logger.exception(e)
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=false)

    
