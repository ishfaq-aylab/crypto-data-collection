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
    db = client[Config.MONGODB_DATABASE]
    # Test connection
    client.admin.command('ping')
    logger.info(f"✅ MongoDB connected successfully to database: {Config.MONGODB_DATABASE}")
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
        # Debug: List all collections in the database
        available_collections = db.list_collection_names()
        logger.info(f"📋 Available collections: {available_collections}")
        
        # Get collection counts
        collections = {}
        for collection_name in ["market_data", "order_book_data", "tick_prices", "historical_data", "volume_liquidity", "funding_rates", "open_interest"]:
            if collection_name in available_collections:
                count = db[collection_name].count_documents({})
                collections[collection_name] = count
                logger.info(f"📄 {collection_name}: {count:,} documents")
            else:
                collections[collection_name] = 0
                logger.warning(f"⚠️ Collection '{collection_name}' not found")
        
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

# ===== LATEST DATA ENDPOINTS (Single Documents) =====

@app.route('/latest')
def get_latest_all():
    """Get the latest single document from each collection across all exchanges."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        result = {
            "timestamp": datetime.now().isoformat(),
            "data": {}
        }
        
        # Latest market data
        latest_market = db.market_data.find_one(sort=[("timestamp", -1)])
        result["data"]["market_data"] = convert_objectid(latest_market) if latest_market else None
        
        # Latest order book data
        latest_order_book = db.order_book_data.find_one(sort=[("timestamp", -1)])
        result["data"]["order_book_data"] = convert_objectid(latest_order_book) if latest_order_book else None
        
        # Latest trade
        latest_trade = db.tick_prices.find_one(sort=[("timestamp", -1)])
        result["data"]["trades"] = convert_objectid(latest_trade) if latest_trade else None
        
        # Latest OHLCV
        latest_ohlcv = db.historical_data.find_one(sort=[("timestamp", -1)])
        result["data"]["ohlcv"] = convert_objectid(latest_ohlcv) if latest_ohlcv else None
        
        # Latest funding rate
        latest_funding = db.funding_rates.find_one(sort=[("timestamp", -1)])
        result["data"]["funding_rates"] = convert_objectid(latest_funding) if latest_funding else None
        
        # Latest open interest
        latest_open_interest = db.open_interest.find_one(sort=[("timestamp", -1)])
        result["data"]["open_interest"] = convert_objectid(latest_open_interest) if latest_open_interest else None
        
        # Latest volume/liquidity
        latest_volume = db.volume_liquidity.find_one(sort=[("timestamp", -1)])
        result["data"]["volume_liquidity"] = convert_objectid(latest_volume) if latest_volume else None
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting latest data: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/latest/<exchange>')
def get_latest_exchange(exchange):
    """Get the latest single document from each collection for a specific exchange."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        result = {
            "exchange": exchange,
            "timestamp": datetime.now().isoformat(),
            "data": {}
        }
        
        # Filter by exchange
        exchange_filter = {"exchange": exchange}
        
        # Latest market data for exchange
        latest_market = db.market_data.find_one(exchange_filter, sort=[("timestamp", -1)])
        result["data"]["market_data"] = convert_objectid(latest_market) if latest_market else None
        
        # Latest order book data for exchange
        latest_order_book = db.order_book_data.find_one(exchange_filter, sort=[("timestamp", -1)])
        result["data"]["order_book_data"] = convert_objectid(latest_order_book) if latest_order_book else None
        
        # Latest trade for exchange
        latest_trade = db.tick_prices.find_one(exchange_filter, sort=[("timestamp", -1)])
        result["data"]["trades"] = convert_objectid(latest_trade) if latest_trade else None
        
        # Latest OHLCV for exchange
        latest_ohlcv = db.historical_data.find_one(exchange_filter, sort=[("timestamp", -1)])
        result["data"]["ohlcv"] = convert_objectid(latest_ohlcv) if latest_ohlcv else None
        
        # Latest funding rate for exchange
        latest_funding = db.funding_rates.find_one(exchange_filter, sort=[("timestamp", -1)])
        result["data"]["funding_rates"] = convert_objectid(latest_funding) if latest_funding else None
        
        # Latest open interest for exchange
        latest_open_interest = db.open_interest.find_one(exchange_filter, sort=[("timestamp", -1)])
        result["data"]["open_interest"] = convert_objectid(latest_open_interest) if latest_open_interest else None
        
        # Latest volume/liquidity for exchange
        latest_volume = db.volume_liquidity.find_one(exchange_filter, sort=[("timestamp", -1)])
        result["data"]["volume_liquidity"] = convert_objectid(latest_volume) if latest_volume else None
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error getting latest data for {exchange}: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/latest/<exchange>/<data_type>')
def get_latest_specific(exchange, data_type):
    """Get the latest single document for a specific exchange and data type."""
    if not mongo_connected:
        return jsonify({"error": "MongoDB not connected"}), 500
    
    try:
        # Map data types to collection names
        collection_map = {
            "market": "market_data",
            "orderbook": "order_book_data", 
            "trades": "tick_prices",
            "ohlcv": "historical_data",
            "funding": "funding_rates",
            "openinterest": "open_interest",
            "volume": "volume_liquidity"
        }
        
        if data_type not in collection_map:
            return jsonify({"error": f"Invalid data type. Available: {list(collection_map.keys())}"}), 400
        
        collection_name = collection_map[data_type]
        exchange_filter = {"exchange": exchange}
        
        # Get latest document
        latest_doc = db[collection_name].find_one(exchange_filter, sort=[("timestamp", -1)])
        
        if not latest_doc:
            return jsonify({
                "exchange": exchange,
                "data_type": data_type,
                "message": "No data found",
                "data": None
            })
        
        return jsonify({
            "exchange": exchange,
            "data_type": data_type,
            "timestamp": datetime.now().isoformat(),
            "data": convert_objectid(latest_doc)
        })
        
    except Exception as e:
        logger.error(f"Error getting latest {data_type} for {exchange}: {e}")
        return jsonify({"error": str(e)}), 500

# Price API Endpoints
@app.route('/price/binance/spot')
def get_binance_spot_price():
    """Get Binance spot price for BTCUSDT."""
    try:
        import requests
        
        url = "https://api.binance.com/api/v3/ticker/price"
        params = {"symbol": "BTCUSDT"}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                "exchange": "binance",
                "type": "spot",
                "symbol": "BTCUSDT",
                "price": float(data['price']),
                "timestamp": datetime.now().isoformat(),
                "raw_response": data
            })
        else:
            return jsonify({"error": f"Binance API error: {response.status_code}"}), 500
            
    except Exception as e:
        logger.error(f"Error fetching Binance spot price: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/price/binance/futures')
def get_binance_futures_price():
    """Get Binance futures price for BTCUSDT."""
    try:
        import requests
        
        url = "https://fapi.binance.com/fapi/v1/ticker/price"
        params = {"symbol": "BTCUSDT"}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return jsonify({
                "exchange": "binance",
                "type": "futures",
                "symbol": "BTCUSDT",
                "price": float(data['price']),
                "timestamp": datetime.now().isoformat(),
                "raw_response": data
            })
        else:
            return jsonify({"error": f"Binance Futures API error: {response.status_code}"}), 500
            
    except Exception as e:
        logger.error(f"Error fetching Binance futures price: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/price/kraken/spot')
def get_kraken_spot_price():
    """Get Kraken spot price for XBTUSDT."""
    try:
        import requests
        
        url = "https://api.kraken.com/0/public/Ticker"
        params = {"pair": "XBTUSDT"}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'XBTUSDT' in data['result']:
                price = float(data['result']['XBTUSDT']['c'][0])
                return jsonify({
                    "exchange": "kraken",
                    "type": "spot",
                    "symbol": "XBTUSDT",
                    "price": price,
                    "timestamp": datetime.now().isoformat(),
                    "raw_response": data
                })
            else:
                return jsonify({"error": "XBTUSDT not found in Kraken response"}), 500
        else:
            return jsonify({"error": f"Kraken API error: {response.status_code}"}), 500
            
    except Exception as e:
        logger.error(f"Error fetching Kraken spot price: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/price/kraken/futures')
def get_kraken_futures_price():
    """Get Kraken futures price for XBTUSD."""
    try:
        import requests
        
        url = "https://futures.kraken.com/derivatives/api/v3/tickers"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'tickers' in data:
                for ticker in data['tickers']:
                    symbol = ticker.get('symbol', '')
                    if symbol in ['PF_XBTUSD', 'PI_XBTUSD'] and ticker.get('last'):
                        price = float(ticker['last'])
                        return jsonify({
                            "exchange": "kraken",
                            "type": "futures",
                            "symbol": symbol,
                            "price": price,
                            "timestamp": datetime.now().isoformat(),
                            "raw_response": ticker
                        })
                return jsonify({"error": "XBTUSD futures not found in Kraken response"}), 500
            else:
                return jsonify({"error": "No tickers in Kraken response"}), 500
        else:
            return jsonify({"error": f"Kraken Futures API error: {response.status_code}"}), 500
            
    except Exception as e:
        logger.error(f"Error fetching Kraken futures price: {e}")
        return jsonify({"error": str(e)}), 500


# Additional Exchange Price Endpoints
@app.route('/price/bybit/spot')
def get_bybit_spot_price():
    """Get Bybit spot price for BTCUSDT."""
    try:
        import requests
        
        url = "https://api.bybit.com/v5/market/tickers"
        params = {"category": "spot", "symbol": "BTCUSDT"}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'list' in data['result'] and len(data['result']['list']) > 0:
                ticker = data['result']['list'][0]
                return jsonify({
                    "exchange": "bybit",
                    "type": "spot",
                    "symbol": "BTCUSDT",
                    "price": float(ticker['lastPrice']),
                    "timestamp": datetime.now().isoformat(),
                    "raw_response": ticker
                })
            else:
                return jsonify({"error": "BTCUSDT not found in Bybit response"}), 500
        else:
            return jsonify({"error": f"Bybit API error: {response.status_code}"}), 500
            
    except Exception as e:
        logger.error(f"Error fetching Bybit spot price: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/price/bybit/futures')
def get_bybit_futures_price():
    """Get Bybit futures price for BTCUSDT."""
    try:
        import requests
        
        url = "https://api.bybit.com/v5/market/tickers"
        params = {"category": "linear", "symbol": "BTCUSDT"}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'result' in data and 'list' in data['result'] and len(data['result']['list']) > 0:
                ticker = data['result']['list'][0]
                return jsonify({
                    "exchange": "bybit",
                    "type": "futures",
                    "symbol": "BTCUSDT",
                    "price": float(ticker['lastPrice']),
                    "timestamp": datetime.now().isoformat(),
                    "raw_response": ticker
                })
            else:
                return jsonify({"error": "BTCUSDT futures not found in Bybit response"}), 500
        else:
            return jsonify({"error": f"Bybit Futures API error: {response.status_code}"}), 500
            
    except Exception as e:
        logger.error(f"Error fetching Bybit futures price: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/price/gate/spot')
def get_gate_spot_price():
    """Get Gate.io spot price for BTC_USDT."""
    try:
        import requests
        
        url = "https://api.gateio.ws/api/v4/spot/tickers"
        params = {"currency_pair": "BTC_USDT"}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                ticker = data[0]
                return jsonify({
                    "exchange": "gate",
                    "type": "spot",
                    "symbol": "BTC_USDT",
                    "price": float(ticker['last']),
                    "timestamp": datetime.now().isoformat(),
                    "raw_response": ticker
                })
            else:
                return jsonify({"error": "BTC_USDT not found in Gate.io response"}), 500
        else:
            return jsonify({"error": f"Gate.io API error: {response.status_code}"}), 500
            
    except Exception as e:
        logger.error(f"Error fetching Gate.io spot price: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/price/gate/futures')
def get_gate_futures_price():
    """Get Gate.io futures price for BTC_USDT."""
    try:
        import requests
        
        url = "https://api.gateio.ws/api/v4/futures/usdt/tickers"
        params = {"contract": "BTC_USDT"}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if len(data) > 0:
                ticker = data[0]
                return jsonify({
                    "exchange": "gate",
                    "type": "futures",
                    "symbol": "BTC_USDT",
                    "price": float(ticker['last']),
                    "timestamp": datetime.now().isoformat(),
                    "raw_response": ticker
                })
            else:
                return jsonify({"error": "BTC_USDT futures not found in Gate.io response"}), 500
        else:
            return jsonify({"error": f"Gate.io Futures API error: {response.status_code}"}), 500
            
    except Exception as e:
        logger.error(f"Error fetching Gate.io futures price: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/price/okx/spot')
def get_okx_spot_price():
    """Get OKX spot price for BTC-USDT."""
    try:
        import requests
        
        url = "https://www.okx.com/api/v5/market/ticker"
        params = {"instId": "BTC-USDT"}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                ticker = data['data'][0]
                return jsonify({
                    "exchange": "okx",
                    "type": "spot",
                    "symbol": "BTC-USDT",
                    "price": float(ticker['last']),
                    "timestamp": datetime.now().isoformat(),
                    "raw_response": ticker
                })
            else:
                return jsonify({"error": "BTC-USDT not found in OKX response"}), 500
        else:
            return jsonify({"error": f"OKX API error: {response.status_code}"}), 500
            
    except Exception as e:
        logger.error(f"Error fetching OKX spot price: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/price/okx/futures')
def get_okx_futures_price():
    """Get OKX futures price for BTC-USDT-SWAP."""
    try:
        import requests
        
        url = "https://www.okx.com/api/v5/market/ticker"
        params = {"instId": "BTC-USDT-SWAP"}
        
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                ticker = data['data'][0]
                return jsonify({
                    "exchange": "okx",
                    "type": "futures",
                    "symbol": "BTC-USDT-SWAP",
                    "price": float(ticker['last']),
                    "timestamp": datetime.now().isoformat(),
                    "raw_response": ticker
                })
            else:
                return jsonify({"error": "BTC-USDT-SWAP not found in OKX response"}), 500
        else:
            return jsonify({"error": f"OKX Futures API error: {response.status_code}"}), 500
            
    except Exception as e:
        logger.error(f"Error fetching OKX futures price: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/price/all')
def get_all_prices():
    """Get all exchange prices (Binance, Kraken, Bybit, Gate.io, OKX) in one call."""
    try:
        import requests
        import concurrent.futures
        
        def fetch_binance_spot():
            try:
                response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    return {"exchange": "binance", "type": "spot", "symbol": "BTCUSDT", "price": float(data['price']), "raw_response": data}
            except Exception as e:
                return {"exchange": "binance", "type": "spot", "error": str(e)}
            return {"exchange": "binance", "type": "spot", "error": "Failed to fetch"}
        
        def fetch_binance_futures():
            try:
                response = requests.get("https://fapi.binance.com/fapi/v1/ticker/price?symbol=BTCUSDT", timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    return {"exchange": "binance", "type": "futures", "symbol": "BTCUSDT", "price": float(data['price']), "raw_response": data}
            except Exception as e:
                return {"exchange": "binance", "type": "futures", "error": str(e)}
            return {"exchange": "binance", "type": "futures", "error": "Failed to fetch"}
        
        def fetch_kraken_spot():
            try:
                response = requests.get("https://api.kraken.com/0/public/Ticker?pair=XBTUSDT", timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    if 'result' in data and 'XBTUSDT' in data['result']:
                        return {"exchange": "kraken", "type": "spot", "symbol": "XBTUSDT", "price": float(data['result']['XBTUSDT']['c'][0]), "raw_response": data}
            except Exception as e:
                return {"exchange": "kraken", "type": "spot", "error": str(e)}
            return {"exchange": "kraken", "type": "spot", "error": "Failed to fetch"}
        
        def fetch_kraken_futures():
            try:
                response = requests.get("https://futures.kraken.com/derivatives/api/v3/tickers", timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    if 'tickers' in data:
                        for ticker in data['tickers']:
                            symbol = ticker.get('symbol', '')
                            if symbol in ['PF_XBTUSD', 'PI_XBTUSD'] and ticker.get('last'):
                                return {"exchange": "kraken", "type": "futures", "symbol": symbol, "price": float(ticker['last']), "raw_response": ticker}
            except Exception as e:
                return {"exchange": "kraken", "type": "futures", "error": str(e)}
            return {"exchange": "kraken", "type": "futures", "error": "Failed to fetch"}
        
        def fetch_bybit_spot():
            try:
                response = requests.get("https://api.bybit.com/v5/market/tickers?category=spot&symbol=BTCUSDT", timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    if 'result' in data and 'list' in data['result'] and len(data['result']['list']) > 0:
                        ticker = data['result']['list'][0]
                        return {"exchange": "bybit", "type": "spot", "symbol": "BTCUSDT", "price": float(ticker['lastPrice']), "raw_response": ticker}
            except Exception as e:
                return {"exchange": "bybit", "type": "spot", "error": str(e)}
            return {"exchange": "bybit", "type": "spot", "error": "Failed to fetch"}
        
        def fetch_bybit_futures():
            try:
                response = requests.get("https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT", timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    if 'result' in data and 'list' in data['result'] and len(data['result']['list']) > 0:
                        ticker = data['result']['list'][0]
                        return {"exchange": "bybit", "type": "futures", "symbol": "BTCUSDT", "price": float(ticker['lastPrice']), "raw_response": ticker}
            except Exception as e:
                return {"exchange": "bybit", "type": "futures", "error": str(e)}
            return {"exchange": "bybit", "type": "futures", "error": "Failed to fetch"}
        
        def fetch_gate_spot():
            try:
                response = requests.get("https://api.gateio.ws/api/v4/spot/tickers?currency_pair=BTC_USDT", timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    if len(data) > 0:
                        ticker = data[0]
                        return {"exchange": "gate", "type": "spot", "symbol": "BTC_USDT", "price": float(ticker['last']), "raw_response": ticker}
            except Exception as e:
                return {"exchange": "gate", "type": "spot", "error": str(e)}
            return {"exchange": "gate", "type": "spot", "error": "Failed to fetch"}
        
        def fetch_gate_futures():
            try:
                response = requests.get("https://api.gateio.ws/api/v4/futures/usdt/tickers?contract=BTC_USDT", timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    if len(data) > 0:
                        ticker = data[0]
                        return {"exchange": "gate", "type": "futures", "symbol": "BTC_USDT", "price": float(ticker['last']), "raw_response": ticker}
            except Exception as e:
                return {"exchange": "gate", "type": "futures", "error": str(e)}
            return {"exchange": "gate", "type": "futures", "error": "Failed to fetch"}
        
        def fetch_okx_spot():
            try:
                response = requests.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT", timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and len(data['data']) > 0:
                        ticker = data['data'][0]
                        return {"exchange": "okx", "type": "spot", "symbol": "BTC-USDT", "price": float(ticker['last']), "raw_response": ticker}
            except Exception as e:
                return {"exchange": "okx", "type": "spot", "error": str(e)}
            return {"exchange": "okx", "type": "spot", "error": "Failed to fetch"}
        
        def fetch_okx_futures():
            try:
                response = requests.get("https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP", timeout=8)
                if response.status_code == 200:
                    data = response.json()
                    if 'data' in data and len(data['data']) > 0:
                        ticker = data['data'][0]
                        return {"exchange": "okx", "type": "futures", "symbol": "BTC-USDT-SWAP", "price": float(ticker['last']), "raw_response": ticker}
            except Exception as e:
                return {"exchange": "okx", "type": "futures", "error": str(e)}
            return {"exchange": "okx", "type": "futures", "error": "Failed to fetch"}
        
        # Fetch all prices concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(fetch_binance_spot),
                executor.submit(fetch_binance_futures),
                executor.submit(fetch_kraken_spot),
                executor.submit(fetch_kraken_futures),
                executor.submit(fetch_bybit_spot),
                executor.submit(fetch_bybit_futures),
                executor.submit(fetch_gate_spot),
                executor.submit(fetch_gate_futures),
                executor.submit(fetch_okx_spot),
                executor.submit(fetch_okx_futures)
            ]
            
            results = [future.result() for future in futures]
        
        return jsonify({
            "timestamp": datetime.now().isoformat(),
            "prices": results
        })
        
    except Exception as e:
        logger.error(f"Error fetching all exchange prices: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"🚀 Starting Real-time Crypto Data API Server on port {Config.API_PORT}...")
    print("📊 Available endpoints:")
    print("  GET / - API information")
    print("  GET /health - Health check")
    print("  GET /realtime - All real-time data")
    print("  GET /price/binance/spot - Binance spot price")
    print("  GET /price/binance/futures - Binance futures price")
    print("  GET /price/kraken/spot - Kraken spot price")
    print("  GET /price/kraken/futures - Kraken futures price")
    print("  GET /price/bybit/spot - Bybit spot price")
    print("  GET /price/bybit/futures - Bybit futures price")
    print("  GET /price/gate/spot - Gate.io spot price")
    print("  GET /price/gate/futures - Gate.io futures price")
    print("  GET /price/okx/spot - OKX spot price")
    print("  GET /price/okx/futures - OKX futures price")
    print("  GET /price/all - All exchange prices (10 prices)")
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
    print("\n🔥 LATEST DATA ENDPOINTS (Single Documents):")
    print("  GET /latest - Latest single document from each collection")
    print("  GET /latest/<exchange> - Latest single document for exchange")
    print("  GET /latest/<exchange>/<data_type> - Latest specific data type")
    print("    Data types: market, orderbook, trades, ohlcv, funding, openinterest, volume")
    print("\n💡 Query parameters:")
    print("  ?limit=N - Limit number of records")
    print("  ?exchange=NAME - Filter by exchange")
    print("  ?symbol=SYMBOL - Filter by symbol")
    print("  ?timeframe=TIME - Filter by timeframe (for OHLCV)")
    
    app.run(host=Config.API_HOST, port=Config.API_PORT, debug=Config.API_DEBUG)
