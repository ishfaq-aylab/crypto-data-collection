# 🚀 Crypto Data Collection & API Startup Guide

This guide shows you how to start both the data collection system and the real-time API server, plus how to access real-time data using curl commands.

## 📋 Prerequisites

Make sure you have:
- ✅ Python 3.12+ installed
- ✅ MongoDB running on localhost:27017
- ✅ Virtual environment activated
- ✅ All dependencies installed

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies (if not already done)
pip install -r requirements.txt
```

## 🚀 Starting the System

### Option 1: Start Everything at Once (Recommended)

Create a startup script to run both services:

```bash
#!/bin/bash
# start_services.sh

echo "🚀 Starting Crypto Data Collection & API Services..."

# Start MongoDB (if not running)
echo "📊 Starting MongoDB..."
sudo systemctl start mongod

# Wait for MongoDB to be ready
sleep 3

# Start Real-time Data Collection (WebSocket + REST)
echo "📡 Starting real-time data collection..."
nohup python3 run_data_collection.py > data_collection.log 2>&1 &
DATA_PID=$!

# Wait for data collection to initialize
sleep 5

# Start Real-time API Server
echo "🌐 Starting real-time API server..."
nohup python3 realtime_api.py > api_server.log 2>&1 &
API_PID=$!

# Wait for API server to start
sleep 3

# Save PIDs for later reference
echo $DATA_PID > data_collection.pid
echo $API_PID > api_server.pid

echo "✅ Services started successfully!"
echo "📊 Data Collection PID: $DATA_PID"
echo "🌐 API Server PID: $API_PID"
echo ""
echo "📋 Service URLs:"
echo "  API Server: http://localhost:5001"
echo "  Health Check: http://localhost:5001/health"
echo ""
echo "📝 Logs:"
echo "  Data Collection: tail -f data_collection.log"
echo "  API Server: tail -f api_server.log"
echo ""
echo "🛑 To stop services:"
echo "  kill \$(cat data_collection.pid)"
echo "  kill \$(cat api_server.pid)"
```

Make it executable and run:
```bash
chmod +x start_services.sh
./start_services.sh
```

### Option 2: Start Services Manually

#### Step 1: Start Real-time Data Collection
```bash
# Start data collection in background
nohup python3 run_data_collection.py > data_collection.log 2>&1 &

# Check if it's running
ps aux | grep run_data_collection
```

#### Step 2: Start Real-time API Server
```bash
# Start API server in background
nohup python3 realtime_api.py > api_server.log 2>&1 &

# Check if it's running
ps aux | grep realtime_api
```

#### Step 3: Verify Services
```bash
# Check API health
curl http://localhost:5001/health

# Check data collection logs
tail -f data_collection.log
```

## 📊 Real-time Data Access with cURL

### 🔍 Health & Status Checks

```bash
# Check API health
curl http://localhost:5001/health | jq .

# Get API information
curl http://localhost:5001/ | jq .

# List available exchanges
curl http://localhost:5001/exchanges | jq .

# List available symbols
curl http://localhost:5001/symbols | jq .
```

### 📈 Market Data

```bash
# Get latest market data (all exchanges)
curl "http://localhost:5001/market-data?limit=10" | jq .

# Get Binance market data only
curl "http://localhost:5001/market-data?exchange=binance&limit=5" | jq .

# Get BTCUSDT market data
curl "http://localhost:5001/market-data?symbol=BTCUSDT&limit=5" | jq .

# Get specific exchange + symbol
curl "http://localhost:5001/market-data?exchange=binance&symbol=BTCUSDT&limit=3" | jq .
```

### 💹 Trade Data

```bash
# Get latest trades (all exchanges)
curl "http://localhost:5001/trades?limit=20" | jq .

# Get Binance trades only
curl "http://localhost:5001/trades?exchange=binance&limit=10" | jq .

# Get BTCUSDT trades
curl "http://localhost:5001/trades?symbol=BTCUSDT&limit=10" | jq .

# Get recent trades with specific exchange + symbol
curl "http://localhost:5001/trades?exchange=binance&symbol=BTCUSDT&limit=5" | jq .
```

### 📊 OHLCV Data (Candles)

```bash
# Get latest OHLCV data (all timeframes)
curl "http://localhost:5001/ohlcv?limit=10" | jq .

# Get 1-hour candles only
curl "http://localhost:5001/ohlcv?timeframe=1h&limit=10" | jq .

# Get 1-minute candles only
curl "http://localhost:5001/ohlcv?timeframe=1m&limit=10" | jq .

# Get Binance OHLCV data
curl "http://localhost:5001/ohlcv?exchange=binance&limit=10" | jq .

# Get BTCUSDT 1-hour candles
curl "http://localhost:5001/ohlcv?exchange=binance&symbol=BTCUSDT&timeframe=1h&limit=5" | jq .
```

### 📚 Order Book Data

```bash
# Get latest order book data
curl "http://localhost:5001/order-book?limit=10" | jq .

# Get Binance order book
curl "http://localhost:5001/order-book?exchange=binance&limit=5" | jq .

# Get BTCUSDT order book
curl "http://localhost:5001/order-book?exchange=binance&symbol=BTCUSDT&limit=3" | jq .
```

### 💰 Funding Rates

```bash
# Get latest funding rates
curl "http://localhost:5001/funding-rates?limit=10" | jq .

# Get Binance funding rates
curl "http://localhost:5001/funding-rates?exchange=binance&limit=5" | jq .

# Get BTCUSDT funding rates
curl "http://localhost:5001/funding-rates?exchange=binance&symbol=BTCUSDT&limit=3" | jq .
```

### 📊 Open Interest

```bash
# Get latest open interest
curl "http://localhost:5001/open-interest?limit=10" | jq .

# Get Binance open interest
curl "http://localhost:5001/open-interest?exchange=binance&limit=5" | jq .

# Get BTCUSDT open interest
curl "http://localhost:5001/open-interest?exchange=binance&symbol=BTCUSDT&limit=3" | jq .
```

### 📈 Volume & Liquidity

```bash
# Get latest volume/liquidity data
curl "http://localhost:5001/volume-liquidity?limit=10" | jq .

# Get Binance volume/liquidity
curl "http://localhost:5001/volume-liquidity?exchange=binance&limit=5" | jq .

# Get BTCUSDT volume/liquidity
curl "http://localhost:5001/volume-liquidity?exchange=binance&symbol=BTCUSDT&limit=3" | jq .
```

### 🎯 Comprehensive Real-time Data

```bash
# Get ALL real-time data (all exchanges, all symbols)
curl "http://localhost:5001/realtime" | jq .

# Get Binance real-time data only
curl "http://localhost:5001/realtime/binance" | jq .

# Get BTCUSDT real-time data only
curl "http://localhost:5001/realtime/binance/BTCUSDT" | jq .

# Get Kraken real-time data
curl "http://localhost:5001/realtime/kraken" | jq .

# Get Bybit BTCUSDT data
curl "http://localhost:5001/realtime/bybit/BTCUSDT" | jq .
```

## 🔄 Historical Data Collection

### Start 4-Year Historical Collection

```bash
# Start historical data collection (1m and 1h candles)
python3 manage_historical_collection.py start

# Check progress
python3 manage_historical_collection.py progress

# Check data quality
python3 manage_historical_collection.py quality

# Generate report
python3 manage_historical_collection.py report
```

### Resume Historical Collection

```bash
# Resume if interrupted
python3 manage_historical_collection.py resume
```

## 📊 Data Analysis

### Quick Data Check

```bash
# Check current data in database
python3 quick_data_check.py

# Analyze Bitcoin data specifically
python3 analyze_bitcoin_data.py

# Test 1-minute candle collection
python3 test_1m_candles.py
```

## 🛑 Stopping Services

### Stop All Services

```bash
# Stop data collection
kill $(cat data_collection.pid) 2>/dev/null || pkill -f run_data_collection

# Stop API server
kill $(cat api_server.pid) 2>/dev/null || pkill -f realtime_api

# Clean up PID files
rm -f data_collection.pid api_server.pid

echo "🛑 All services stopped"
```

### Stop Individual Services

```bash
# Stop data collection only
pkill -f run_data_collection

# Stop API server only
pkill -f realtime_api
```

## 📝 Monitoring & Logs

### View Logs

```bash
# View data collection logs
tail -f data_collection.log

# View API server logs
tail -f api_server.log

# View both logs simultaneously
tail -f data_collection.log api_server.log
```

### Check Service Status

```bash
# Check if services are running
ps aux | grep -E "(run_data_collection|realtime_api)"

# Check API health
curl -s http://localhost:5001/health | jq .status

# Check data collection status
curl -s http://localhost:5001/exchanges | jq .exchanges
```

## 🔧 Troubleshooting

### Common Issues

1. **API Server won't start**
   ```bash
   # Check if port 5001 is in use
   lsof -i :5001
   
   # Kill process using port 5001
   sudo kill -9 $(lsof -t -i:5001)
   ```

2. **MongoDB connection issues**
   ```bash
   # Check if MongoDB is running
   sudo systemctl status mongod
   
   # Start MongoDB
   sudo systemctl start mongod
   ```

3. **Data collection not working**
   ```bash
   # Check logs for errors
   tail -f data_collection.log
   
   # Restart data collection
   pkill -f run_data_collection
   nohup python3 run_data_collection.py > data_collection.log 2>&1 &
   ```

### Reset Everything

```bash
# Stop all services
pkill -f run_data_collection
pkill -f realtime_api

# Clean up logs
rm -f *.log *.pid

# Restart MongoDB
sudo systemctl restart mongod

# Start fresh
./start_services.sh
```

## 📊 Example Data Responses

### Market Data Response
```json
{
  "_id": "68f729b47390856bb969b1bd",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "timestamp": "2025-10-21T11:35:32.107000",
  "price": 107945.52,
  "bid": 107945.51,
  "ask": 107945.52,
  "bid_size": 4.54488,
  "ask_size": 0.026,
  "volume": 19144.20799
}
```

### Trade Data Response
```json
{
  "_id": "68f7698e45a7c87788c0b5c8",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "timestamp": "2025-10-21T16:07:58.233000",
  "price": 107945.52,
  "volume": 0.00676,
  "side": "sell",
  "trade_id": "617668858"
}
```

### OHLCV Data Response
```json
{
  "_id": "68f760ebfecb4eddd2d67437",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "timestamp": "2025-10-21T15:31:07.171000",
  "timeframe": "1h",
  "open": 107754.27,
  "high": 107904.55,
  "low": 107580.0,
  "close": 107708.39,
  "volume": 254.86195
}
```

## 🎯 Quick Start Commands

```bash
# 1. Start everything
./start_services.sh

# 2. Check health
curl http://localhost:5001/health

# 3. Get real-time data
curl http://localhost:5001/realtime

# 4. Get BTCUSDT data
curl http://localhost:5001/realtime/binance/BTCUSDT

# 5. Monitor logs
tail -f data_collection.log api_server.log
```

## 📞 Support

If you encounter any issues:
1. Check the logs: `tail -f *.log`
2. Verify MongoDB is running: `sudo systemctl status mongod`
3. Check API health: `curl http://localhost:5001/health`
4. Restart services if needed: `./start_services.sh`

---

**🎉 Your crypto data collection and API system is now ready to use!**
