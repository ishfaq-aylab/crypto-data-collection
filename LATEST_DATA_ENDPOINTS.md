# 🔥 Latest Data Endpoints - Single Documents

## Overview
These endpoints return the **latest single document** from each collection, perfect for getting the most recent data without pagination.

## Available Endpoints

### 1. Get Latest from All Collections
```bash
GET /latest
```
**Response:** Latest single document from each collection across all exchanges
```json
{
  "timestamp": "2025-10-22T12:30:00.000Z",
  "data": {
    "market_data": { /* latest market data */ },
    "order_book_data": { /* latest order book */ },
    "trades": { /* latest trade */ },
    "ohlcv": { /* latest OHLCV */ },
    "funding_rates": { /* latest funding rate */ },
    "open_interest": { /* latest open interest */ },
    "volume_liquidity": { /* latest volume/liquidity */ }
  }
}
```

### 2. Get Latest for Specific Exchange
```bash
GET /latest/<exchange>
```
**Examples:**
- `GET /latest/kraken`
- `GET /latest/binance`
- `GET /latest/bybit`
- `GET /latest/okx`
- `GET /latest/gateio`

**Response:** Latest single document from each collection for the specified exchange
```json
{
  "exchange": "kraken",
  "timestamp": "2025-10-22T12:30:00.000Z",
  "data": {
    "market_data": { /* latest Kraken market data */ },
    "order_book_data": { /* latest Kraken order book */ },
    "trades": { /* latest Kraken trade */ },
    "ohlcv": { /* latest Kraken OHLCV */ },
    "funding_rates": { /* latest Kraken funding rate */ },
    "open_interest": { /* latest Kraken open interest */ },
    "volume_liquidity": { /* latest Kraken volume/liquidity */ }
  }
}
```

### 3. Get Latest Specific Data Type
```bash
GET /latest/<exchange>/<data_type>
```

**Available Data Types:**
- `market` - Market data (price, bid, ask, volume)
- `orderbook` - Order book data (bids, asks)
- `trades` - Trade data (tick prices)
- `ohlcv` - OHLCV data (candles)
- `funding` - Funding rates
- `openinterest` - Open interest
- `volume` - Volume/liquidity data

**Examples:**
- `GET /latest/kraken/market` - Latest Kraken market data
- `GET /latest/binance/trades` - Latest Binance trade
- `GET /latest/bybit/funding` - Latest Bybit funding rate
- `GET /latest/okx/ohlcv` - Latest OKX OHLCV

**Response:** Latest single document for the specified exchange and data type
```json
{
  "exchange": "kraken",
  "data_type": "market",
  "timestamp": "2025-10-22T12:30:00.000Z",
  "data": {
    "_id": "ObjectId(...)",
    "exchange": "kraken",
    "symbol": "BTCUSDT",
    "price": 45000.0,
    "bid": 44999.0,
    "ask": 45001.0,
    "bid_size": 1.5,
    "ask_size": 2.0,
    "volume": 100.0,
    "timestamp": "2025-10-22T12:29:45.000Z"
  }
}
```

## Usage Examples

### Get Latest Market Data for All Exchanges
```bash
curl "http://3.86.197.160:5001/latest" | jq '.data.market_data'
```

### Get Latest Kraken Data
```bash
curl "http://3.86.197.160:5001/latest/kraken" | jq '.data'
```

### Get Latest Binance Trade
```bash
curl "http://3.86.197.160:5001/latest/binance/trades" | jq '.data'
```

### Get Latest Funding Rate from Any Exchange
```bash
curl "http://3.86.197.160:5001/latest" | jq '.data.funding_rates'
```

## Key Benefits

1. **Single Document:** Returns only the most recent record, not arrays
2. **Fast Response:** No pagination or large data sets
3. **Real-time:** Always gets the latest timestamp
4. **Flexible:** Can filter by exchange and/or data type
5. **Efficient:** Perfect for dashboards, monitoring, and real-time displays

## Error Handling

- **No Data Found:** Returns `null` for missing data types
- **Invalid Exchange:** Returns empty data object
- **Invalid Data Type:** Returns 400 error with available types
- **MongoDB Disconnected:** Returns 500 error

## Comparison with Other Endpoints

| Endpoint | Returns | Use Case |
|----------|---------|----------|
| `/realtime` | Arrays of documents | Historical analysis, bulk data |
| `/latest` | Single latest document | Real-time monitoring, dashboards |
| `/latest/<exchange>` | Single latest per type | Exchange-specific monitoring |
| `/latest/<exchange>/<type>` | Single latest specific | Targeted data retrieval |

## API Server Information

- **Base URL:** `http://3.86.197.160:5001`
- **Status:** ✅ Active and Running
- **Database:** MongoDB (model-collections)
- **Data Collection:** ✅ Active (Kraken Futures, Gate.io Futures working)
