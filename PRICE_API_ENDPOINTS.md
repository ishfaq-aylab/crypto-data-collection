# Price API Endpoints Documentation

This document describes all the price API endpoints available in the crypto data API service.

## Overview

The API provides real-time price data from 5 major cryptocurrency exchanges:
- **Binance** (Spot & Futures)
- **Kraken** (Spot & Futures) 
- **Bybit** (Spot & Futures)
- **Gate.io** (Spot & Futures)
- **OKX** (Spot & Futures)

## Base URL

```
http://crypto-alb-dubai-1902974409.me-central-1.elb.amazonaws.com
```

## Individual Exchange Endpoints

### Binance

#### Spot Price
```http
GET /price/binance/spot
```

**Response:**
```json
{
  "exchange": "binance",
  "type": "spot",
  "symbol": "BTCUSDT",
  "price": 109826.7,
  "timestamp": "2025-10-23T17:00:00.000000",
  "raw_response": {
    "symbol": "BTCUSDT",
    "price": "109826.70000000"
  }
}
```

#### Futures Price
```http
GET /price/binance/futures
```

### Kraken

#### Spot Price
```http
GET /price/kraken/spot
```

**Response:**
```json
{
  "exchange": "kraken",
  "type": "spot",
  "symbol": "XBTUSDT",
  "price": 109850.2,
  "timestamp": "2025-10-23T17:00:00.000000",
  "raw_response": {
    "result": {
      "XBTUSDT": {
        "c": ["109850.2", "0.1"]
      }
    }
  }
}
```

#### Futures Price
```http
GET /price/kraken/futures
```

### Bybit

#### Spot Price
```http
GET /price/bybit/spot
```

**Response:**
```json
{
  "exchange": "bybit",
  "type": "spot",
  "symbol": "BTCUSDT",
  "price": 109840.5,
  "timestamp": "2025-10-23T17:00:00.000000",
  "raw_response": {
    "symbol": "BTCUSDT",
    "lastPrice": "109840.50",
    "price24hPcnt": "0.0123"
  }
}
```

#### Futures Price
```http
GET /price/bybit/futures
```

### Gate.io

#### Spot Price
```http
GET /price/gate/spot
```

**Response:**
```json
{
  "exchange": "gate",
  "type": "spot",
  "symbol": "BTC_USDT",
  "price": 109835.8,
  "timestamp": "2025-10-23T17:00:00.000000",
  "raw_response": {
    "currency_pair": "BTC_USDT",
    "last": "109835.8",
    "lowest_ask": "109836.2"
  }
}
```

#### Futures Price
```http
GET /price/gate/futures
```

### OKX

#### Spot Price
```http
GET /price/okx/spot
```

**Response:**
```json
{
  "exchange": "okx",
  "type": "spot",
  "symbol": "BTC-USDT",
  "price": 109830.1,
  "timestamp": "2025-10-23T17:00:00.000000",
  "raw_response": {
    "instId": "BTC-USDT",
    "last": "109830.1",
    "lastSz": "0.001"
  }
}
```

#### Futures Price
```http
GET /price/okx/futures
```

## Bulk Endpoints

### All Exchange Prices
```http
GET /price/all
```

**Response:**
```json
{
  "timestamp": "2025-10-23T17:00:00.000000",
  "prices": [
    {
      "exchange": "binance",
      "type": "spot",
      "symbol": "BTCUSDT",
      "price": 109826.7,
      "raw_response": {...}
    },
    {
      "exchange": "binance",
      "type": "futures",
      "symbol": "BTCUSDT",
      "price": 109828.3,
      "raw_response": {...}
    },
    {
      "exchange": "kraken",
      "type": "spot",
      "symbol": "XBTUSDT",
      "price": 109850.2,
      "raw_response": {...}
    },
    {
      "exchange": "kraken",
      "type": "futures",
      "symbol": "PF_XBTUSD",
      "price": 109845.7,
      "raw_response": {...}
    },
    {
      "exchange": "bybit",
      "type": "spot",
      "symbol": "BTCUSDT",
      "price": 109840.5,
      "raw_response": {...}
    },
    {
      "exchange": "bybit",
      "type": "futures",
      "symbol": "BTCUSDT",
      "price": 109842.1,
      "raw_response": {...}
    },
    {
      "exchange": "gate",
      "type": "spot",
      "symbol": "BTC_USDT",
      "price": 109835.8,
      "raw_response": {...}
    },
    {
      "exchange": "gate",
      "type": "futures",
      "symbol": "BTC_USDT",
      "price": 109837.4,
      "raw_response": {...}
    },
    {
      "exchange": "okx",
      "type": "spot",
      "symbol": "BTC-USDT",
      "price": 109830.1,
      "raw_response": {...}
    },
    {
      "exchange": "okx",
      "type": "futures",
      "symbol": "BTC-USDT-SWAP",
      "price": 109832.7,
      "raw_response": {...}
    }
  ]
}
```

**Note:** This endpoint returns **10 prices** from all 5 exchanges (Binance, Kraken, Bybit, Gate.io, OKX) with both spot and futures data for each.

## Error Handling

All endpoints return appropriate HTTP status codes:

- **200 OK**: Successful response
- **500 Internal Server Error**: API error or exchange unavailable

**Error Response Format:**
```json
{
  "error": "Error message describing what went wrong"
}
```

## Rate Limits

- **Individual endpoints**: 10 requests per second
- **Bulk endpoints**: 5 requests per second
- **Timeout**: 10 seconds per request

## Authentication

All price endpoints are **public** and do not require authentication.

## Data Sources

| Exchange | Spot API | Futures API |
|----------|----------|-------------|
| Binance | `https://api.binance.com/api/v3/ticker/price` | `https://fapi.binance.com/fapi/v1/ticker/price` |
| Kraken | `https://api.kraken.com/0/public/Ticker` | `https://futures.kraken.com/derivatives/api/v3/tickers` |
| Bybit | `https://api.bybit.com/v5/market/tickers` | `https://api.bybit.com/v5/market/tickers` |
| Gate.io | `https://api.gateio.ws/api/v4/spot/tickers` | `https://api.gateio.ws/api/v4/futures/usdt/tickers` |
| OKX | `https://www.okx.com/api/v5/market/ticker` | `https://www.okx.com/api/v5/market/ticker` |

## Usage Examples

### cURL Examples

```bash
# Get Binance spot price
curl "http://crypto-alb-dubai-1902974409.me-central-1.elb.amazonaws.com/price/binance/spot"

# Get all exchange prices
curl "http://crypto-alb-dubai-1902974409.me-central-1.elb.amazonaws.com/price/all"

# Get Bybit futures price
curl "http://crypto-alb-dubai-1902974409.me-central-1.elb.amazonaws.com/price/bybit/futures"
```

### Python Examples

```python
import requests

# Get single price
response = requests.get("http://crypto-alb-dubai-1902974409.me-central-1.elb.amazonaws.com/price/binance/spot")
data = response.json()
print(f"Binance BTC Price: ${data['price']}")

# Get all prices
response = requests.get("http://crypto-alb-dubai-1902974409.me-central-1.elb.amazonaws.com/price/all")
data = response.json()
for price in data['prices']:
    print(f"{price['exchange']} {price['type']}: ${price['price']}")
```

### JavaScript Examples

```javascript
// Get single price
fetch('http://crypto-alb-dubai-1902974409.me-central-1.elb.amazonaws.com/price/binance/spot')
  .then(response => response.json())
  .then(data => console.log(`Binance BTC Price: $${data.price}`));

// Get all prices
fetch('http://crypto-alb-dubai-1902974409.me-central-1.elb.amazonaws.com/price/all')
  .then(response => response.json())
  .then(data => {
    data.prices.forEach(price => {
      console.log(`${price.exchange} ${price.type}: $${price.price}`);
    });
  });
```

## Notes

- All prices are returned in USD
- Timestamps are in ISO 8601 format
- Raw responses include the complete API response from each exchange
- Concurrent fetching is used for bulk endpoints for optimal performance
- Error handling includes timeout protection and graceful degradation
