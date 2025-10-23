# API Testing Guide

## Current Status

✅ **API Server is WORKING!** The system is fully operational and accessible through the load balancer.

**Load Balancer URL**: `http://crypto-alb-dubai-1902974409.me-central-1.elb.amazonaws.com`

**Note**: The API is only accessible through the load balancer, not directly via task IP addresses, due to security group configurations.

## Available Endpoints

Once the API server is running correctly, here are all the available endpoints:

### 1. Health Check Endpoints

```bash
# Basic health check
curl "http://<API_IP>:5001/health"

# Detailed health check (shows MongoDB status and collection counts)
curl "http://<API_IP>:5001/health/detailed"
```

### 2. Real-time Data Endpoints

```bash
# Get latest data from all exchanges
curl "http://<API_IP>:5001/realtime"

# Get latest data from a specific exchange
curl "http://<API_IP>:5001/realtime/binance"
curl "http://<API_IP>:5001/realtime/bybit"
curl "http://<API_IP>:5001/realtime/okx"
curl "http://<API_IP>:5001/realtime/gate"
curl "http://<API_IP>:5001/realtime/kraken"

# Get latest data for a specific symbol from an exchange
curl "http://<API_IP>:5001/realtime/binance/BTCUSDT"
```

### 3. Market Data Endpoints

```bash
# Get market data (with optional filters)
curl "http://<API_IP>:5001/market-data"
curl "http://<API_IP>:5001/market-data?exchange=binance&symbol=BTCUSDT&limit=10"
```

### 4. Order Book Data

```bash
# Get order book snapshots
curl "http://<API_IP>:5001/order-book"
curl "http://<API_IP>:5001/order-book?exchange=binance&symbol=BTCUSDT&limit=5"
```

### 5. Trade Data (Tick Prices)

```bash
# Get recent trades
curl "http://<API_IP>:5001/trades"
curl "http://<API_IP>:5001/trades?exchange=okx&symbol=BTC-USDT&limit=20"
```

### 6. OHLCV Data

```bash
# Get OHLCV (candlestick) data
curl "http://<API_IP>:5001/ohlcv"
curl "http://<API_IP>:5001/ohlcv?exchange=binance&symbol=BTCUSDT&interval=1h&limit=24"
```

### 7. Funding Rates (Futures)

```bash
# Get funding rates
curl "http://<API_IP>:5001/funding-rates"
curl "http://<API_IP>:5001/funding-rates?exchange=binance&symbol=BTCUSDT&limit=10"
```

### 8. Open Interest (Futures)

```bash
# Get open interest data
curl "http://<API_IP>:5001/open-interest"
curl "http://<API_IP>:5001/open-interest?exchange=okx&symbol=BTC-USDT-SWAP&limit=10"
```

### 9. Volume & Liquidity

```bash
# Get volume and liquidity data
curl "http://<API_IP>:5001/volume-liquidity"
curl "http://<API_IP>:5001/volume-liquidity?exchange=binance&limit=10"
```

### 10. Metadata Endpoints

```bash
# Get list of available exchanges
curl "http://<API_IP>:5001/exchanges"

# Get list of available symbols
curl "http://<API_IP>:5001/symbols"
curl "http://<API_IP>:5001/symbols?exchange=binance"
```

### 11. Latest Data Aggregation

```bash
# Get latest data across all data types
curl "http://<API_IP>:5001/latest"

# Get latest data for a specific exchange
curl "http://<API_IP>:5001/latest/binance"

# Get latest data for a specific data type
curl "http://<API_IP>:5001/latest/binance/funding_rates"
curl "http://<API_IP>:5001/latest/okx/open_interest"
```

## Query Parameters

Most endpoints support the following query parameters:

- `exchange` - Filter by exchange (binance, bybit, okx, gate, kraken)
- `symbol` - Filter by trading pair symbol
- `limit` - Number of results to return (default: 100, max: 1000)
- `start_time` - Filter by start timestamp (ISO format)
- `end_time` - Filter by end timestamp (ISO format)

## Example Testing Session

```bash
# Set the ALB URL
ALB_URL="http://crypto-alb-dubai-1902974409.me-central-1.elb.amazonaws.com"

# 1. Check if API is running
curl -s "$ALB_URL/health" | jq .

# 2. Get detailed health status
curl -s "$ALB_URL/health/detailed" | jq .

# 3. View available exchanges
curl -s "$ALB_URL/exchanges" | jq .

# 4. Get latest Binance data
curl -s "$ALB_URL/latest/binance" | jq .

# 5. Get recent trades for BTC
curl -s "$ALB_URL/trades?symbol=BTCUSDT&limit=5" | jq .

# 6. Get funding rates
curl -s "$ALB_URL/funding-rates?limit=5" | jq .

# 7. Get open interest
curl -s "$ALB_URL/open-interest?limit=5" | jq .
```

## Live Test Results

✅ **All endpoints are working!** Here are some live examples:

### Health Check
```json
{
  "collections": {
    "funding_rates": 10398,
    "historical_data": 0,
    "market_data": 40803,
    "open_interest": 16866,
    "order_book_data": 159540,
    "tick_prices": 74759,
    "volume_liquidity": 46
  },
  "mongodb": "connected",
  "status": "healthy",
  "timestamp": "2025-10-23T13:02:53.344918"
}
```

### Available Exchanges
```json
{
  "exchanges": ["binance", "bybit", "gate", "kraken", "okx"]
}
```

### Real-time Data Collection Stats
- 📊 **Market Data**: 40,803+ documents
- 📖 **Order Book Data**: 159,540+ documents
- 💱 **Tick Prices**: 74,759+ trades
- 📈 **Open Interest**: 16,866+ records
- 💰 **Funding Rates**: 10,398+ records
- 💧 **Volume & Liquidity**: 46+ records

## System Architecture

The system consists of:

1. **AWS ECS Fargate Tasks** - Running two containers:
   - `api-server`: Flask API (Gunicorn) serving REST endpoints
   - `data-collection`: Python script collecting real-time data

2. **Application Load Balancer (ALB)** - Routes traffic to the API server container

3. **AWS DocumentDB** - MongoDB-compatible database storing all data

4. **Security Groups** - ECS tasks only accept traffic from ALB (not direct internet access)

## Task Definition Used

- **Family**: `crypto-api-task-dubai-v2`
- **Revision**: 1
- **Region**: `me-central-1` (Dubai/UAE)
- **Network Mode**: `awsvpc` (Fargate)
- **CPU**: 1024 (1 vCPU)
- **Memory**: 2048 MB (2 GB)

## All Systems Operational! ✅

The crypto data collection and API system is now fully operational in the Dubai region with:
- ✅ Real-time data collection from 5 exchanges
- ✅ REST API serving all data types
- ✅ DocumentDB storage with proper schemas
- ✅ Load balancer for high availability
- ✅ No geographic restrictions for Binance

