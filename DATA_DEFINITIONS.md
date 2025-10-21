# Crypto Data Collector - Data Definitions

This document defines all data structures collected and stored by the crypto data collector system.

## Table of Contents
1. [Real-time Data (WebSocket)](#real-time-data-websocket)
2. [Historical Data (REST API)](#historical-data-rest-api)
3. [Market Metrics](#market-metrics)
4. [Database Collections](#database-collections)
5. [Data Quality Metrics](#data-quality-metrics)
6. [Technical Indicators](#technical-indicators)

---

## Real-time Data (WebSocket)

### 1. Market Data (Ticker)
**Collection**: Real-time via WebSocket  
**Storage**: `market_data` collection  
**Frequency**: Continuous updates

```python
{
    "_id": ObjectId,                    # MongoDB document ID
    "exchange": str,                    # Exchange name (binance, kraken, bybit, etc.)
    "symbol": str,                      # Trading pair (BTCUSDT, ETHUSDT, etc.)
    "timestamp": datetime,              # When data was collected (UTC)
    "price": float,                     # Current/last traded price
    "volume": float,                    # 24h trading volume
    "bid": float,                       # Best bid price
    "ask": float,                       # Best ask price
    "bid_size": float,                  # Bid quantity
    "ask_size": float,                  # Ask quantity
    "data_type": str,                   # 'ticker', 'orderbook', 'trade'
    "created_at": datetime,             # When stored in database (UTC)
    "is_outlier": bool                  # Flag for outlier detection (optional)
}
```

**Example**:
```json
{
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "timestamp": "2024-01-15T10:30:45.123Z",
    "price": 42500.50,
    "volume": 1234.567,
    "bid": 42499.00,
    "ask": 42501.00,
    "bid_size": 0.5,
    "ask_size": 0.3,
    "data_type": "ticker",
    "created_at": "2024-01-15T10:30:45.200Z",
    "is_outlier": false
}
```

### 2. Order Book Data (Depth)
**Collection**: Real-time via WebSocket  
**Storage**: `order_book_data` collection  
**Frequency**: Continuous updates

```python
{
    "_id": ObjectId,                    # MongoDB document ID
    "exchange": str,                    # Exchange name
    "symbol": str,                      # Trading pair
    "timestamp": datetime,              # When data was collected (UTC)
    "level": int,                       # Depth level (1, 2, 3, etc.)
    "bids": List[List[float]],          # [[price, size], [price, size], ...]
    "asks": List[List[float]],          # [[price, size], [price, size], ...]
    "created_at": datetime              # When stored in database (UTC)
}
```

**Example**:
```json
{
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "timestamp": "2024-01-15T10:30:45.123Z",
    "level": 20,
    "bids": [
        [42499.00, 0.5],
        [42498.50, 1.2],
        [42498.00, 0.8]
    ],
    "asks": [
        [42501.00, 0.3],
        [42501.50, 0.7],
        [42502.00, 1.1]
    ],
    "created_at": "2024-01-15T10:30:45.200Z"
}
```

### 3. Trade Executions
**Collection**: Real-time via WebSocket  
**Storage**: `tick_prices` collection  
**Frequency**: Every trade execution

```python
{
    "_id": ObjectId,                    # MongoDB document ID
    "exchange": str,                    # Exchange name
    "symbol": str,                      # Trading pair
    "timestamp": datetime,              # When trade occurred (UTC)
    "price": float,                     # Trade execution price
    "volume": float,                    # Trade quantity
    "side": str,                        # 'buy' or 'sell' (if available)
    "trade_id": str,                    # Unique trade identifier (if available)
    "created_at": datetime              # When stored in database (UTC)
}
```

**Example**:
```json
{
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "timestamp": "2024-01-15T10:30:45.123Z",
    "price": 42500.25,
    "volume": 0.1,
    "side": "buy",
    "trade_id": "123456789",
    "created_at": "2024-01-15T10:30:45.200Z"
}
```

### 4. Funding Rates (Derivatives)
**Collection**: REST API  
**Storage**: `funding_rates` collection  
**Frequency**: Every 8 hours (funding periods)

```python
{
    "_id": ObjectId,                    # MongoDB document ID
    "exchange": str,                    # Exchange name
    "symbol": str,                      # Trading pair
    "timestamp": datetime,              # When data was collected (UTC)
    "funding_rate": float,              # Current funding rate (e.g., 0.0001 = 0.01%)
    "funding_time": datetime,           # When funding was last paid
    "next_funding_time": datetime,      # When next funding will be paid
    "funding_interval": int,            # Hours between funding (usually 8)
    "predicted_funding_rate": float,    # Predicted next funding rate
    "created_at": datetime              # When stored in database (UTC)
}
```

**Example**:
```json
{
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "timestamp": "2024-01-15T10:30:00.000Z",
    "funding_rate": 0.0001,
    "funding_time": "2024-01-15T08:00:00.000Z",
    "next_funding_time": "2024-01-15T16:00:00.000Z",
    "funding_interval": 8,
    "predicted_funding_rate": 0.0002,
    "created_at": "2024-01-15T10:30:00.200Z"
}
```

### 5. Open Interest (Derivatives)
**Collection**: REST API  
**Storage**: `open_interest` collection  
**Frequency**: Every 5-15 minutes

```python
{
    "_id": ObjectId,                    # MongoDB document ID
    "exchange": str,                    # Exchange name
    "symbol": str,                      # Trading pair
    "timestamp": datetime,              # When data was collected (UTC)
    "open_interest": float,             # Total open interest
    "long_short_ratio": float,          # Long/Short ratio (if available)
    "long_interest": float,             # Long positions (if available)
    "short_interest": float,            # Short positions (if available)
    "interest_value": float,            # Open interest value in USD
    "top_trader_long_short_ratio": float, # Top trader long/short ratio
    "retail_long_short_ratio": float,   # Retail long/short ratio
    "created_at": datetime              # When stored in database (UTC)
}
```

**Example**:
```json
{
    "exchange": "bybit",
    "symbol": "BTCUSDT",
    "timestamp": "2024-01-15T10:30:00.000Z",
    "open_interest": 1234567.89,
    "long_short_ratio": 1.25,
    "long_interest": 685185.49,
    "short_interest": 548382.40,
    "interest_value": 52345678901.23,
    "top_trader_long_short_ratio": 1.15,
    "retail_long_short_ratio": 1.35,
    "created_at": "2024-01-15T10:30:00.200Z"
}
```

---

## Historical Data (REST API)

### 1. OHLCV Candles
**Collection**: Historical via REST API  
**Storage**: `historical_data` collection  
**Frequency**: Based on timeframe

```python
{
    "_id": ObjectId,                    # MongoDB document ID
    "exchange": str,                    # Exchange name
    "symbol": str,                      # Trading pair
    "timeframe": str,                   # '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'
    "timestamp": datetime,              # Candle start time (UTC)
    "open": float,                      # Opening price
    "high": float,                      # Highest price in period
    "low": float,                       # Lowest price in period
    "close": float,                     # Closing price
    "volume": float,                    # Volume traded in period
    "created_at": datetime              # When stored in database (UTC)
}
```

**Example**:
```json
{
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "timeframe": "1h",
    "timestamp": "2024-01-15T10:00:00.000Z",
    "open": 42450.00,
    "high": 42550.00,
    "low": 42400.00,
    "close": 42500.50,
    "volume": 123.456,
    "created_at": "2024-01-15T11:00:00.200Z"
}
```

### 2. Historical Trades
**Collection**: Historical via REST API  
**Storage**: `tick_prices` collection  
**Frequency**: Batch collection

```python
{
    "_id": ObjectId,                    # MongoDB document ID
    "exchange": str,                    # Exchange name
    "symbol": str,                      # Trading pair
    "timestamp": datetime,              # When trade occurred (UTC)
    "price": float,                     # Trade price
    "volume": float,                    # Trade quantity
    "side": str,                        # 'buy' or 'sell'
    "trade_id": str,                    # Unique trade identifier
    "created_at": datetime              # When stored in database (UTC)
}
```

---

## Market Metrics

### 1. Volume & Liquidity Metrics
**Collection**: Calculated from market data  
**Storage**: `volume_liquidity` collection  
**Frequency**: Periodic updates

```python
{
    "_id": ObjectId,                    # MongoDB document ID
    "exchange": str,                    # Exchange name
    "symbol": str,                      # Trading pair
    "timestamp": datetime,              # When metrics calculated (UTC)
    "volume_24h": float,                # 24-hour trading volume
    "volume_1h": float,                 # 1-hour trading volume
    "liquidity_score": float,           # Calculated liquidity metric (0-100)
    "spread_bps": float,                # Bid-ask spread in basis points
    "avg_trade_size": float,            # Average trade size
    "trade_count_24h": int,             # Number of trades in 24h
    "created_at": datetime              # When stored in database (UTC)
}
```

**Example**:
```json
{
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "timestamp": "2024-01-15T10:30:00.000Z",
    "volume_24h": 1234.567,
    "volume_1h": 45.123,
    "liquidity_score": 85.5,
    "spread_bps": 2.5,
    "avg_trade_size": 0.05,
    "trade_count_24h": 15000,
    "created_at": "2024-01-15T10:30:00.200Z"
}
```

### 2. Arbitrage Opportunities
**Collection**: Calculated from cross-exchange data  
**Storage**: Calculated on-demand  
**Frequency**: Real-time calculation

```python
{
    "exchange1": str,                   # First exchange
    "exchange2": str,                   # Second exchange
    "symbol": str,                      # Trading pair
    "price1": float,                    # Price on exchange1
    "price2": float,                    # Price on exchange2
    "spread": float,                    # Absolute price difference
    "spread_percentage": float,         # Percentage spread
    "timestamp": datetime,              # When calculated (UTC)
    "opportunity_score": float          # Calculated opportunity score (0-100)
}
```

**Example**:
```json
{
    "exchange1": "binance",
    "exchange2": "kraken",
    "symbol": "BTCUSDT",
    "price1": 42500.50,
    "price2": 42480.25,
    "spread": 20.25,
    "spread_percentage": 0.0476,
    "timestamp": "2024-01-15T10:30:45.123Z",
    "opportunity_score": 75.5
}
```

---

## Database Collections

### MongoDB Collections Overview

| Collection | Purpose | Indexes |
|------------|---------|---------|
| `market_data` | Real-time market data | (exchange, symbol), (timestamp), (exchange, timestamp) |
| `order_book_data` | Order book depth data | (exchange, symbol), (timestamp) |
| `historical_data` | OHLCV candles | (exchange, symbol), (timestamp), (exchange, symbol, timeframe) |
| `tick_prices` | Individual trades | (exchange, symbol), (timestamp) |
| `volume_liquidity` | Volume & liquidity metrics | (exchange, symbol), (timestamp) |
| `funding_rates` | Derivatives funding rates | (exchange, symbol), (timestamp), (funding_time) |
| `open_interest` | Derivatives open interest | (exchange, symbol), (timestamp) |

### Index Strategy
```javascript
// Market data indexes
db.market_data.createIndex({ "exchange": 1, "symbol": 1 })
db.market_data.createIndex({ "timestamp": -1 })
db.market_data.createIndex({ "exchange": 1, "timestamp": -1 })

// Order book data indexes
db.order_book_data.createIndex({ "exchange": 1, "symbol": 1 })
db.order_book_data.createIndex({ "timestamp": -1 })

// Historical data indexes
db.historical_data.createIndex({ "exchange": 1, "symbol": 1 })
db.historical_data.createIndex({ "timestamp": -1 })
db.historical_data.createIndex({ "exchange": 1, "symbol": 1, "timeframe": 1 })

// Tick prices indexes
db.tick_prices.createIndex({ "exchange": 1, "symbol": 1 })
db.tick_prices.createIndex({ "timestamp": -1 })

// Volume liquidity indexes
db.volume_liquidity.createIndex({ "exchange": 1, "symbol": 1 })
db.volume_liquidity.createIndex({ "timestamp": -1 })
```

---

## Data Quality Metrics

### Data Quality Assessment
```python
{
    "total_records": int,               # Total records processed
    "valid_records": int,               # Records that passed validation
    "invalid_records": int,             # Records that failed validation
    "missing_fields": int,              # Records with missing required fields
    "duplicate_records": int,           # Duplicate records found
    "outliers": int,                    # Outlier records detected
    "quality_score": float              # Overall quality score (0-100)
}
```

### Validation Rules
```python
{
    "price": {
        "min": 0,
        "max": 1000000,
        "required": True
    },
    "volume": {
        "min": 0,
        "max": 1000000000,
        "required": True
    },
    "timestamp": {
        "required": True,
        "format": "datetime"
    },
    "exchange": {
        "required": True,
        "type": "string"
    },
    "symbol": {
        "required": True,
        "type": "string"
    }
}
```

---

## Technical Indicators

### Available Indicators
```python
{
    "sma_20": float,                    # 20-period Simple Moving Average
    "sma_50": float,                    # 50-period Simple Moving Average
    "rsi": float,                       # 14-period RSI (0-100)
    "bb_upper": float,                  # Bollinger Bands upper band
    "bb_lower": float,                  # Bollinger Bands lower band
    "volatility": float,                # 20-period rolling volatility
    "price_change": float,              # Price change from previous period
    "price_change_pct": float,          # Price change percentage
    "volume_change": float,             # Volume change from previous period
    "volume_change_pct": float          # Volume change percentage
}
```

### Example with Technical Indicators
```json
{
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "timestamp": "2024-01-15T10:30:00.000Z",
    "price": 42500.50,
    "volume": 123.456,
    "sma_20": 42450.25,
    "sma_50": 42300.75,
    "rsi": 65.5,
    "bb_upper": 42600.00,
    "bb_lower": 42300.00,
    "volatility": 0.025,
    "price_change": 50.25,
    "price_change_pct": 0.118,
    "volume_change": 10.5,
    "volume_change_pct": 9.3
}
```

---

## Data Collection Frequencies

### Real-time Data (WebSocket)
- **Market Data**: Continuous (every price update)
- **Order Book**: Continuous (every depth change)
- **Trades**: Every trade execution
- **Volume Updates**: Every 1-5 seconds

### Historical Data (REST API)
- **1m Candles**: Every minute
- **5m Candles**: Every 5 minutes
- **15m Candles**: Every 15 minutes
- **30m Candles**: Every 30 minutes
- **1h Candles**: Every hour
- **4h Candles**: Every 4 hours
- **1d Candles**: Every day
- **1w Candles**: Every week

### Market Metrics
- **Volume & Liquidity**: Every 5-15 minutes
- **Arbitrage Opportunities**: Continuous calculation
- **Technical Indicators**: Updated with new data

---

## Data Retention Policy

### Default Retention
- **Real-time Data**: 365 days
- **Historical Data**: 2 years
- **Market Metrics**: 1 year
- **Technical Indicators**: 1 year

### Cleanup Process
- Automatic cleanup of old data based on retention policy
- Configurable retention periods per data type
- Data export before cleanup for backup purposes

---

## Exchange Support

### Supported Exchanges
1. **Binance** - Spot and futures data
2. **Kraken** - Spot data
3. **Bybit** - Spot and derivatives
4. **OKX** - Spot and futures
5. **Coinbase** - Spot data
6. **Gate.io** - Spot data
7. **Deribit** - Options and futures

### Exchange-Specific Notes
- **Symbol Format**: Normalized to standard format (BTCUSDT)
- **Timezone**: All timestamps converted to UTC
- **Data Types**: Unified across all exchanges
- **Rate Limits**: Respected per exchange requirements

---

## Usage Examples

### Query Market Data
```python
# Get latest BTCUSDT data from Binance
data = await storage_manager.get_data(
    data_type='market_data',
    exchange='binance',
    symbol='BTCUSDT',
    limit=100
)
```

### Query Historical Data
```python
# Get 1-hour candles for last 24 hours
data = await storage_manager.get_data(
    data_type='historical_data',
    exchange='binance',
    symbol='BTCUSDT',
    timeframe='1h',
    start_time=datetime.now() - timedelta(days=1),
    limit=1000
)
```

### Query Order Book Data
```python
# Get latest order book depth
data = await storage_manager.get_data(
    data_type='order_book_data',
    exchange='binance',
    symbol='BTCUSDT',
    limit=10
)
```

---

This data definition provides a comprehensive overview of all data structures collected and stored by the crypto data collector system. Use this as a reference for understanding the available data and building applications on top of the collected data.
