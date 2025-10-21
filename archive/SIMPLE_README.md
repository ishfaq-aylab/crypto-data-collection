# 🚀 Simple MongoDB Crypto Data Collection

A simplified, production-ready system for collecting real-time cryptocurrency market data from 5 major exchanges and storing it in MongoDB.

## 📊 Data Types Collected

- ✅ **Market Data**: Real-time price updates, 24hr statistics
- ✅ **Order Book Data**: Real-time order book depth and updates  
- ✅ **Tick Prices (Trades)**: Live trade executions and prices
- ✅ **Volume/Liquidity**: Trading volume and liquidity metrics
- ✅ **Funding Rates**: Perpetual futures funding rates
- ✅ **Open Interest**: Open interest data for derivatives

## 🏗️ Supported Exchanges

- ✅ Binance
- ✅ Bybit  
- ✅ Kraken
- ✅ OKX
- ✅ Gate.io

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- MongoDB 7.0+ running on localhost:27017

### Installation

1. **Install dependencies**:
```bash
pip install -r requirements_simple.txt
```

2. **Start MongoDB** (if not running):
```bash
# Using Docker
docker run -d -p 27017:27017 --name mongodb mongo:7.0

# Or install MongoDB locally
# https://docs.mongodb.com/manual/installation/
```

3. **Start data collection**:
```bash
# Collect data indefinitely
python start_collection.py

# Collect data for specific duration (e.g., 10 minutes)
python start_collection.py --duration 10

# Test mode (2 minutes)
python start_collection.py --test

# Custom symbols
python start_collection.py --symbols BTCUSDT ETHUSDT ADAUSDT
```

## 📁 File Structure

```
exchanges-websockets/
├── simple_mongodb_collector.py    # Main data collection system
├── start_collection.py            # Simple startup script
├── test_data_collection.py        # Test script to verify data collection
├── requirements_simple.txt        # Simple dependencies
├── SIMPLE_README.md              # This file
└── exchanges/                     # Exchange WebSocket clients
    ├── binance_client.py
    ├── bybit_client.py
    ├── kraken_client.py
    ├── okx_client.py
    └── gate_client.py
```

## 🗄️ MongoDB Collections

The system creates 6 collections in the `crypto_trading_data` database:

- `market_data` - Real-time market data
- `order_book_data` - Order book snapshots
- `tick_prices` - Trade executions
- `volume_liquidity` - Volume and liquidity data
- `funding_rates` - Funding rate updates
- `open_interest` - Open interest data

### Document Structure

Each document contains:
```json
{
  "timestamp": "2024-01-20T10:30:00.000Z",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "data_type": "market_data",
  "data": {
    "symbol": "BTCUSDT",
    "price": 42000.50,
    "volume": 1234.56,
    "bid": 41999.00,
    "ask": 42001.00,
    "high_24h": 42500.00,
    "low_24h": 41500.00,
    "change_24h": 0.02
  },
  "raw_message": {...},
  "created_at": "2024-01-20T10:30:00.000Z"
}
```

## 🔧 Usage Examples

### Basic Data Collection

```python
from simple_mongodb_collector import SimpleMongoDBCollector, SimpleDataFeeder

# Initialize collector
collector = SimpleMongoDBCollector()

# Connect to MongoDB
await collector.connect()

# Initialize feeder
feeder = SimpleDataFeeder(collector)
await feeder.initialize_clients(['BTCUSDT', 'ETHUSDT'])

# Start collecting data
await feeder.start_feeding()
```

### Querying Data

```python
from pymongo import MongoClient
from datetime import datetime, timedelta

client = MongoClient("mongodb://localhost:27017")
db = client["crypto_trading_data"]

# Get latest market data for BTCUSDT
latest_data = db.market_data.find_one(
    {"symbol": "BTCUSDT"},
    sort=[("timestamp", -1)]
)

# Get all data from last hour
one_hour_ago = datetime.now() - timedelta(hours=1)
recent_data = list(db.market_data.find({
    "timestamp": {"$gte": one_hour_ago}
}))

# Get data by exchange
binance_data = list(db.market_data.find({
    "exchange": "binance"
}))
```

### Testing Data Collection

```bash
# Run test to verify all data types are collected
python test_data_collection.py
```

## 📈 Performance Features

### Database Optimization
- **Compound indexes** for fast queries by exchange, symbol, and timestamp
- **TTL indexes** for automatic cleanup (30 days retention)
- **Efficient serialization** of Pydantic models

### Data Quality
- **Real-time validation** of incoming data
- **Error handling** with automatic recovery
- **Statistics tracking** for monitoring

### Monitoring
- **Performance statistics** (messages per second, success rate)
- **Collection summaries** (document counts, unique symbols)
- **Real-time logging** with Loguru

## 🚨 Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**:
   ```bash
   # Check if MongoDB is running
   docker ps | grep mongo
   
   # Or check MongoDB status
   systemctl status mongod
   ```

2. **No Data Being Collected**:
   ```bash
   # Check logs for connection errors
   tail -f logs/data_collection.log
   
   # Test individual exchange connections
   python test_data_collection.py
   ```

3. **High Memory Usage**:
   ```bash
   # Check MongoDB memory usage
   docker stats mongodb
   
   # Or check system memory
   free -h
   ```

### Debug Commands

```bash
# Check MongoDB collections
mongo crypto_trading_data --eval "db.getCollectionNames()"

# Check document counts
mongo crypto_trading_data --eval "db.market_data.countDocuments()"

# Check recent data
mongo crypto_trading_data --eval "db.market_data.findOne({}, {sort: {timestamp: -1}})"
```

## 📊 Monitoring

### Real-time Statistics
The system provides real-time statistics:
- Total messages collected
- Success rate
- Messages per second
- Data by exchange and type

### Collection Health
- Document counts per collection
- Unique symbols and exchanges
- Latest and oldest timestamps
- Recent activity (last hour)

## 🔄 Scaling

### Horizontal Scaling
- Run multiple instances with different symbol sets
- Use MongoDB sharding for large datasets
- Implement load balancing

### Vertical Scaling
- Increase server resources
- Optimize MongoDB configuration
- Use faster storage (SSD)

## 📚 API Reference

### SimpleMongoDBCollector
- `connect()` - Connect to MongoDB
- `store_message(message)` - Store WebSocket message
- `get_data_stats()` - Get collection statistics
- `get_collection_summary()` - Get detailed collection info
- `disconnect()` - Disconnect from MongoDB

### SimpleDataFeeder
- `initialize_clients(symbols)` - Initialize WebSocket clients
- `start_feeding()` - Start data collection
- `stop_feeding()` - Stop data collection

## 🛠️ Development

### Adding New Exchanges
1. Create new client in `exchanges/` directory
2. Inherit from `BaseWebSocketClient`
3. Implement required methods
4. Add to `SimpleDataFeeder.initialize_clients()`

### Adding New Data Types
1. Add new `DataType` enum value
2. Create Pydantic model in `models.py`
3. Add collection in `SimpleMongoDBCollector`
4. Update exchange clients to parse new data type

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review logs for error messages
3. Run test script to verify setup
4. Create GitHub issue if needed

---

**⚠️ Note**: This is a simplified version focused on MongoDB storage. For production use with high-frequency trading, consider implementing the full production system with Redis caching and PostgreSQL for historical data.
