# Real-time Crypto Data API Documentation

## Overview
This API provides real-time access to cryptocurrency market data collected from multiple exchanges and stored in MongoDB. The data includes market data, order books, trades, OHLCV candles, funding rates, open interest, and volume/liquidity information.

## Base URL
```
http://localhost:5001
```

## Authentication
No authentication required for public endpoints.

## Data Sources
- **Exchanges**: Binance, Bybit, Kraken, Gate.io, OKX
- **Symbols**: Bitcoin USD pairs (BTCUSDT, BTCUSDC, XXBTZUSD, etc.)
- **Timeframes**: 1-minute and 1-hour candles
- **Update Frequency**: Real-time (as data is collected)

## Endpoints

### 1. Health Check
```http
GET /health
```
**Description**: Check API and database status.

**Response**:
```json
{
  "status": "healthy",
  "mongodb": "connected",
  "collections": {
    "market_data": 1023,
    "order_book_data": 6478,
    "tick_prices": 176092,
    "historical_data": 50896,
    "volume_liquidity": 5517,
    "funding_rates": 305,
    "open_interest": 69
  },
  "timestamp": "2025-10-21T16:15:00.000Z"
}
```

### 2. API Information
```http
GET /
```
**Description**: Get API information and available endpoints.

### 3. All Real-time Data
```http
GET /realtime
```
**Description**: Get latest data from all exchanges and symbols.

**Response**:
```json
{
  "timestamp": "2025-10-21T16:15:00.000Z",
  "data": {
    "market_data": [...],
    "order_book_data": [...],
    "trades": [...],
    "ohlcv": [...],
    "funding_rates": [...],
    "open_interest": [...],
    "volume_liquidity": [...]
  }
}
```

### 4. Exchange-specific Data
```http
GET /realtime/{exchange}
```
**Description**: Get real-time data for a specific exchange.

**Parameters**:
- `exchange`: Exchange name (binance, bybit, kraken, gate, okx)

**Example**:
```http
GET /realtime/binance
```

### 5. Symbol-specific Data
```http
GET /realtime/{exchange}/{symbol}
```
**Description**: Get real-time data for a specific exchange and symbol.

**Parameters**:
- `exchange`: Exchange name
- `symbol`: Symbol name (e.g., BTCUSDT, XXBTZUSD)

**Example**:
```http
GET /realtime/binance/BTCUSDT
```

### 6. Individual Data Types

#### Market Data
```http
GET /market-data
```
**Query Parameters**:
- `limit`: Number of records (default: 100)
- `exchange`: Filter by exchange
- `symbol`: Filter by symbol

**Example**:
```http
GET /market-data?limit=50&exchange=binance&symbol=BTCUSDT
```

#### Order Book Data
```http
GET /order-book
```
**Query Parameters**:
- `limit`: Number of records (default: 50)
- `exchange`: Filter by exchange
- `symbol`: Filter by symbol

#### Trade Data
```http
GET /trades
```
**Query Parameters**:
- `limit`: Number of records (default: 200)
- `exchange`: Filter by exchange
- `symbol`: Filter by symbol

#### OHLCV Data
```http
GET /ohlcv
```
**Query Parameters**:
- `limit`: Number of records (default: 100)
- `exchange`: Filter by exchange
- `symbol`: Filter by symbol
- `timeframe`: Filter by timeframe (1m, 1h)

#### Funding Rates
```http
GET /funding-rates
```
**Query Parameters**:
- `limit`: Number of records (default: 50)
- `exchange`: Filter by exchange
- `symbol`: Filter by symbol

#### Open Interest
```http
GET /open-interest
```
**Query Parameters**:
- `limit`: Number of records (default: 50)
- `exchange`: Filter by exchange
- `symbol`: Filter by symbol

#### Volume/Liquidity
```http
GET /volume-liquidity
```
**Query Parameters**:
- `limit`: Number of records (default: 50)
- `exchange`: Filter by exchange
- `symbol`: Filter by symbol

### 7. Metadata Endpoints

#### List Exchanges
```http
GET /exchanges
```
**Response**:
```json
{
  "timestamp": "2025-10-21T16:15:00.000Z",
  "exchanges": ["binance", "bybit", "kraken", "gate", "okx"]
}
```

#### List Symbols
```http
GET /symbols
```
**Query Parameters**:
- `exchange`: Filter by exchange

**Response**:
```json
{
  "timestamp": "2025-10-21T16:15:00.000Z",
  "exchange": "all",
  "symbols": ["BTCUSDT", "BTCUSDC", "XXBTZUSD", "XBT/USD", ...]
}
```

## Data Models

### Market Data
```json
{
  "_id": "ObjectId",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "timestamp": "2025-10-21T16:15:00.000Z",
  "data_type": "market_data",
  "created_at": "2025-10-21T16:15:00.000Z",
  "price": 65000.0,
  "volume": 1.5,
  "bid": 64995.0,
  "ask": 65005.0,
  "bid_size": 2.0,
  "ask_size": 1.5
}
```

### Order Book Data
```json
{
  "_id": "ObjectId",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "timestamp": "2025-10-21T16:15:00.000Z",
  "data_type": "order_book_data",
  "created_at": "2025-10-21T16:15:00.000Z",
  "bids": [[65000.0, 1.5], [64999.0, 2.0]],
  "asks": [[65001.0, 1.0], [65002.0, 1.5]]
}
```

### Trade Data
```json
{
  "_id": "ObjectId",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "timestamp": "2025-10-21T16:15:00.000Z",
  "data_type": "tick_prices",
  "created_at": "2025-10-21T16:15:00.000Z",
  "price": 65000.0,
  "volume": 0.1,
  "side": "buy",
  "trade_id": "123456789"
}
```

### OHLCV Data
```json
{
  "_id": "ObjectId",
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "timestamp": "2025-10-21T16:00:00.000Z",
  "data_type": "historical_data",
  "created_at": "2025-10-21T16:15:00.000Z",
  "timeframe": "1h",
  "open": 64800.0,
  "high": 65200.0,
  "low": 64700.0,
  "close": 65000.0,
  "volume": 150.5
}
```

## Usage Examples

### Python Example
```python
import requests

# Get all real-time data
response = requests.get("http://localhost:5001/realtime")
data = response.json()

# Get Binance BTCUSDT data
response = requests.get("http://localhost:5001/realtime/binance/BTCUSDT")
btc_data = response.json()

# Get latest trades with limit
response = requests.get("http://localhost:5001/trades?limit=10&exchange=binance")
trades = response.json()
```

### JavaScript Example
```javascript
// Get all real-time data
fetch('http://localhost:5001/realtime')
  .then(response => response.json())
  .then(data => console.log(data));

// Get specific exchange data
fetch('http://localhost:5001/realtime/binance')
  .then(response => response.json())
  .then(data => console.log(data));
```

### cURL Examples
```bash
# Health check
curl http://localhost:5001/health

# All real-time data
curl http://localhost:5001/realtime

# Binance data only
curl http://localhost:5001/realtime/binance

# BTCUSDT data only
curl http://localhost:5001/realtime/binance/BTCUSDT

# Latest 10 trades
curl "http://localhost:5001/trades?limit=10"

# OHLCV data for 1h timeframe
curl "http://localhost:5001/ohlcv?timeframe=1h&limit=50"
```

## Error Handling

### Common Error Responses
```json
{
  "error": "MongoDB not connected"
}
```

```json
{
  "error": "Exchange not found"
}
```

### HTTP Status Codes
- `200`: Success
- `400`: Bad Request
- `404`: Not Found
- `500`: Internal Server Error

## Rate Limiting
No rate limiting currently implemented. Consider implementing if needed for production use.

## Data Freshness
- Data is updated in real-time as it's collected from exchanges
- Latest data is always returned first (sorted by timestamp descending)
- Data includes both WebSocket and REST API sources

## Getting Started

1. **Start the API server**:
   ```bash
   python realtime_api.py
   ```

2. **Test the API**:
   ```bash
   python test_realtime_api.py
   ```

3. **Check health**:
   ```bash
   curl http://localhost:5001/health
   ```

## Support
For questions or issues, contact the development team.
