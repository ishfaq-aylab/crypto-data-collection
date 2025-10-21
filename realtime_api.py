#!/usr/bin/env python3
"""
Real-time Data API Server
Provides endpoints to return real-time data from MongoDB collections.
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
from config import Config
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime, timedelta
import json
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

# Custom JSON encoder for MongoDB ObjectId
class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

app = Flask(__name__)
CORS(app)
app.json_encoder = JSONEncoder

# Connect to MongoDB
try:
    client = MongoClient(Config.MONGODB_URL, serverSelectionTimeoutMS=Config.MONGODB_TIMEOUT)
    db = client["crypto_trading_data"]
    # Test connection
    client.admin.command('ping')
    logger.info("✅ MongoDB connected successfully")
    mongo_connected = True
except Exception as e:
    logger.error(f"❌ MongoDB connection failed: {e}")
    client = None
    db = None
    mongo_connected = False

def convert_objectid(obj):
    """Convert ObjectId to string recursively."""
    if isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    elif isinstance(obj, ObjectId):
        return str(obj)
    elif isinstance(obj, datetime):
        return obj.isoformat()
    return obj

@app.route('/')
def home():
    """API home endpoint."""
    return jsonify({
        "message": "Real-time Crypto Data API",
        "status": "running",
        "mongodb": "connected" if mongo_connected else "disconnected",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "realtime_all": "/realtime",
            "realtime_exchange": "/realtime/<exchange>",
            "realtime_symbol": "/realtime/<exchange>/<symbol>",
            "market_data": "/market-data",
            "order_book": "/order-book",
            "trades": "/trades",
            "ohlcv": "/ohlcv",
            "funding_rates": "/funding-rates",
            "open_interest": "/open-interest",
            "volume_liquidity": "/volume-liquidity"
        }
    })

@app.route('/health')
def health():
    """Health check endpoint."""
    if not mongo_connected:
        return jsonify({
            "status": "error",
            "message": "MongoDB not connected",
            "timestamp": datetime.now().isoformat()
        }), 500
    
    try:
        # Get collection counts
        collections = {
            "market_data": db.market_data.count_documents({}),
            "order_book_data": db.order_book_data.count_documents({}),
            "tick_prices": db.tick_prices.count_documents({}),
            "historical_data": db.historical_data.count_documents({}),
            "volume_liquidity": db.volume_liquidity.count_documents({}),
            "funding_rates": db.funding_rates.count_documents({}),
            "open_interest": db.open_interest.count_documents({})
        }
        
        return jsonify({
            "status": "healthy",
            "mongodb": "connected",
            "collections": collections,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/health/detailed')
def detailed_health():
    """Detailed health check for monitoring"""
    try:
        # Check database connection
        db_status = "connected" if mongo_connected else "disconnected"
        
        # Get system metrics
        import psutil
        cpu_usage = psutil.cpu_percent()
        memory_usage = psutil.virtual_memory().percent
        disk_usage = psutil.disk_usage('/').percent
        
        # Check recent data availability
        recent_data = {}
        try:
            for exchange in ['binance', 'bybit', 'kraken', 'gate', 'okx']:
                count = db['market_data'].count_documents({
                    'exchange': exchange,
                    'timestamp': {'$gte': datetime.now() - timedelta(minutes=5)}
                })
                recent_data[exchange] = count
        except:
            recent_data = {'error': 'Unable to check recent data'}
        
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'services': {
                'api_server': 'running',
                'database': db_status,
                'data_collection': 'running'
            },
            'metrics': {
                'cpu_usage': f"{cpu_usage}%",
                'memory_usage': f"{memory_usage}%",
                'disk_usage': f"{disk_usage}%"
            },
            'recent_data': recent_data
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/realtime')
def get_realtime_all():
    """Get real-time data from all exchanges and symbols."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        # Get latest data from each collection
        result = {
            "timestamp": datetime.now().isoformat(),
            "data": {
                "market_data": [],
                "order_book_data": [],
                "trades": [],
                "ohlcv": [],
                "funding_rates": [],
                "open_interest": [],
                "volume_liquidity": []
            }
        }
        
        # Market data (latest 100 records)
        market_data = list(db.market_data.find().sort("timestamp", -1).limit(100))
        result["data"]["market_data"] = convert_objectid(market_data)
        
        # Order book data (latest 50 records)
        order_book_data = list(db.order_book_data.find().sort("timestamp", -1).limit(50))
        result["data"]["order_book_data"] = convert_objectid(order_book_data)
        
        # Trades (latest 200 records)
        trades = list(db.tick_prices.find().sort("timestamp", -1).limit(200))
        result["data"]["trades"] = convert_objectid(trades)
        
        # OHLCV (latest 100 records)
        ohlcv = list(db.historical_data.find().sort("timestamp", -1).limit(100))
        result["data"]["ohlcv"] = convert_objectid(ohlcv)
        
        # Funding rates (latest 50 records)
        funding_rates = list(db.funding_rates.find().sort("timestamp", -1).limit(50))
        result["data"]["funding_rates"] = convert_objectid(funding_rates)
        
        # Open interest (latest 50 records)
        open_interest = list(db.open_interest.find().sort("timestamp", -1).limit(50))
        result["data"]["open_interest"] = convert_objectid(open_interest)
        
        # Volume/Liquidity (latest 50 records)
        volume_liquidity = list(db.volume_liquidity.find().sort("timestamp", -1).limit(50))
        result["data"]["volume_liquidity"] = convert_objectid(volume_liquidity)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting real-time data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/realtime/<exchange>')
def get_realtime_exchange(exchange):
    """Get real-time data for a specific exchange."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        result = {
            "exchange": exchange,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "market_data": [],
                "order_book_data": [],
                "trades": [],
                "ohlcv": [],
                "funding_rates": [],
                "open_interest": [],
                "volume_liquidity": []
            }
        }
        
        # Filter by exchange
        exchange_filter = {"exchange": exchange}
        
        # Market data
        market_data = list(db.market_data.find(exchange_filter).sort("timestamp", -1).limit(50))
        result["data"]["market_data"] = convert_objectid(market_data)
        
        # Order book data
        order_book_data = list(db.order_book_data.find(exchange_filter).sort("timestamp", -1).limit(25))
        result["data"]["order_book_data"] = convert_objectid(order_book_data)
        
        # Trades
        trades = list(db.tick_prices.find(exchange_filter).sort("timestamp", -1).limit(100))
        result["data"]["trades"] = convert_objectid(trades)
        
        # OHLCV
        ohlcv = list(db.historical_data.find(exchange_filter).sort("timestamp", -1).limit(50))
        result["data"]["ohlcv"] = convert_objectid(ohlcv)
        
        # Funding rates
        funding_rates = list(db.funding_rates.find(exchange_filter).sort("timestamp", -1).limit(25))
        result["data"]["funding_rates"] = convert_objectid(funding_rates)
        
        # Open interest
        open_interest = list(db.open_interest.find(exchange_filter).sort("timestamp", -1).limit(25))
        result["data"]["open_interest"] = convert_objectid(open_interest)
        
        # Volume/Liquidity
        volume_liquidity = list(db.volume_liquidity.find(exchange_filter).sort("timestamp", -1).limit(25))
        result["data"]["volume_liquidity"] = convert_objectid(volume_liquidity)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting real-time data for {exchange}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/realtime/<exchange>/<symbol>')
def get_realtime_symbol(exchange, symbol):
    """Get real-time data for a specific exchange and symbol."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        result = {
            "exchange": exchange,
            "symbol": symbol,
            "timestamp": datetime.now().isoformat(),
            "data": {
                "market_data": [],
                "order_book_data": [],
                "trades": [],
                "ohlcv": [],
                "funding_rates": [],
                "open_interest": [],
                "volume_liquidity": []
            }
        }
        
        # Filter by exchange and symbol
        filter_query = {"exchange": exchange, "symbol": symbol}
        
        # Market data
        market_data = list(db.market_data.find(filter_query).sort("timestamp", -1).limit(25))
        result["data"]["market_data"] = convert_objectid(market_data)
        
        # Order book data
        order_book_data = list(db.order_book_data.find(filter_query).sort("timestamp", -1).limit(10))
        result["data"]["order_book_data"] = convert_objectid(order_book_data)
        
        # Trades
        trades = list(db.tick_prices.find(filter_query).sort("timestamp", -1).limit(50))
        result["data"]["trades"] = convert_objectid(trades)
        
        # OHLCV
        ohlcv = list(db.historical_data.find(filter_query).sort("timestamp", -1).limit(25))
        result["data"]["ohlcv"] = convert_objectid(ohlcv)
        
        # Funding rates
        funding_rates = list(db.funding_rates.find(filter_query).sort("timestamp", -1).limit(10))
        result["data"]["funding_rates"] = convert_objectid(funding_rates)
        
        # Open interest
        open_interest = list(db.open_interest.find(filter_query).sort("timestamp", -1).limit(10))
        result["data"]["open_interest"] = convert_objectid(open_interest)
        
        # Volume/Liquidity
        volume_liquidity = list(db.volume_liquidity.find(filter_query).sort("timestamp", -1).limit(10))
        result["data"]["volume_liquidity"] = convert_objectid(volume_liquidity)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting real-time data for {exchange}/{symbol}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/market-data')
def get_market_data():
    """Get latest market data."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        limit = request.args.get('limit', 100, type=int)
        exchange = request.args.get('exchange')
        symbol = request.args.get('symbol')
        
        filter_query = {}
        if exchange:
            filter_query["exchange"] = exchange
        if symbol:
            filter_query["symbol"] = symbol
        
        market_data = list(db.market_data.find(filter_query).sort("timestamp", -1).limit(limit))
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "count": len(market_data),
            "data": convert_objectid(market_data)
        })
        
    except Exception as e:
        logger.error(f"Error getting market data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/order-book')
def get_order_book():
    """Get latest order book data."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        limit = request.args.get('limit', 50, type=int)
        exchange = request.args.get('exchange')
        symbol = request.args.get('symbol')
        
        filter_query = {}
        if exchange:
            filter_query["exchange"] = exchange
        if symbol:
            filter_query["symbol"] = symbol
        
        order_book = list(db.order_book_data.find(filter_query).sort("timestamp", -1).limit(limit))
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "count": len(order_book),
            "data": convert_objectid(order_book)
        })
        
    except Exception as e:
        logger.error(f"Error getting order book data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/trades')
def get_trades():
    """Get latest trade data."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        limit = request.args.get('limit', 200, type=int)
        exchange = request.args.get('exchange')
        symbol = request.args.get('symbol')
        
        filter_query = {}
        if exchange:
            filter_query["exchange"] = exchange
        if symbol:
            filter_query["symbol"] = symbol
        
        trades = list(db.tick_prices.find(filter_query).sort("timestamp", -1).limit(limit))
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "count": len(trades),
            "data": convert_objectid(trades)
        })
        
    except Exception as e:
        logger.error(f"Error getting trade data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/ohlcv')
def get_ohlcv():
    """Get latest OHLCV data."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        limit = request.args.get('limit', 100, type=int)
        exchange = request.args.get('exchange')
        symbol = request.args.get('symbol')
        timeframe = request.args.get('timeframe')
        
        filter_query = {}
        if exchange:
            filter_query["exchange"] = exchange
        if symbol:
            filter_query["symbol"] = symbol
        if timeframe:
            filter_query["timeframe"] = timeframe
        
        ohlcv = list(db.historical_data.find(filter_query).sort("timestamp", -1).limit(limit))
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "count": len(ohlcv),
            "data": convert_objectid(ohlcv)
        })
        
    except Exception as e:
        logger.error(f"Error getting OHLCV data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/funding-rates')
def get_funding_rates():
    """Get latest funding rates."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        limit = request.args.get('limit', 50, type=int)
        exchange = request.args.get('exchange')
        symbol = request.args.get('symbol')
        
        filter_query = {}
        if exchange:
            filter_query["exchange"] = exchange
        if symbol:
            filter_query["symbol"] = symbol
        
        funding_rates = list(db.funding_rates.find(filter_query).sort("timestamp", -1).limit(limit))
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "count": len(funding_rates),
            "data": convert_objectid(funding_rates)
        })
        
    except Exception as e:
        logger.error(f"Error getting funding rates: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/open-interest')
def get_open_interest():
    """Get latest open interest data."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        limit = request.args.get('limit', 50, type=int)
        exchange = request.args.get('exchange')
        symbol = request.args.get('symbol')
        
        filter_query = {}
        if exchange:
            filter_query["exchange"] = exchange
        if symbol:
            filter_query["symbol"] = symbol
        
        open_interest = list(db.open_interest.find(filter_query).sort("timestamp", -1).limit(limit))
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "count": len(open_interest),
            "data": convert_objectid(open_interest)
        })
        
    except Exception as e:
        logger.error(f"Error getting open interest: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/volume-liquidity')
def get_volume_liquidity():
    """Get latest volume/liquidity data."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        limit = request.args.get('limit', 50, type=int)
        exchange = request.args.get('exchange')
        symbol = request.args.get('symbol')
        
        filter_query = {}
        if exchange:
            filter_query["exchange"] = exchange
        if symbol:
            filter_query["symbol"] = symbol
        
        volume_liquidity = list(db.volume_liquidity.find(filter_query).sort("timestamp", -1).limit(limit))
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "count": len(volume_liquidity),
            "data": convert_objectid(volume_liquidity)
        })
        
    except Exception as e:
        logger.error(f"Error getting volume/liquidity data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/exchanges')
def get_exchanges():
    """Get list of available exchanges."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        exchanges = set()
        
        # Get exchanges from all collections
        for collection_name in ["market_data", "order_book_data", "tick_prices", "historical_data", "volume_liquidity", "funding_rates", "open_interest"]:
            collection = db[collection_name]
            exchange_list = collection.distinct("exchange")
            exchanges.update(exchange_list)
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "exchanges": sorted(list(exchanges))
        })
        
    except Exception as e:
        logger.error(f"Error getting exchanges: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/symbols')
def get_symbols():
    """Get list of available symbols."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        exchange = request.args.get('exchange')
        
        symbols = set()
        
        # Get symbols from all collections
        for collection_name in ["market_data", "order_book_data", "tick_prices", "historical_data", "volume_liquidity", "funding_rates", "open_interest"]:
            collection = db[collection_name]
            filter_query = {}
            if exchange:
                filter_query["exchange"] = exchange
            
            symbol_list = collection.distinct("symbol", filter_query)
            symbols.update(symbol_list)
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "exchange": exchange or "all",
            "symbols": sorted(list(symbols))
        })
        
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"🚀 Starting Real-time Crypto Data API Server on port {Config.API_PORT}...")
    print("📊 Available endpoints:")
    print("  GET / - API information")
    print("  GET /health - Health check")
    print("  GET /realtime - All real-time data")
    print("  GET /realtime/<exchange> - Exchange-specific data")
    print("  GET /realtime/<exchange>/<symbol> - Symbol-specific data")
    print("  GET /market-data - Market data only")
    print("  GET /order-book - Order book data only")
    print("  GET /trades - Trade data only")
    print("  GET /ohlcv - OHLCV data only")
    print("  GET /funding-rates - Funding rates only")
    print("  GET /open-interest - Open interest only")
    print("  GET /volume-liquidity - Volume/liquidity only")
    print("  GET /exchanges - List exchanges")
    print("  GET /symbols - List symbols")
    print("\n💡 Query parameters:")
    print("  ?limit=N - Limit number of records")
    print("  ?exchange=NAME - Filter by exchange")
    print("  ?symbol=SYMBOL - Filter by symbol")
    print("  ?timeframe=TIME - Filter by timeframe (for OHLCV)")
    
    app.run(host=Config.API_HOST, port=Config.API_PORT, debug=Config.API_DEBUG)
