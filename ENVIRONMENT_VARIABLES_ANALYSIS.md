# 🔧 Environment Variables Analysis - Crypto Data Collection System

## 📊 **Current Hardcoded Values Found**

Based on the analysis of your codebase, here are the hardcoded values that can be moved to environment variables:

---

## 🗄️ **Database Configuration**

### **Current Hardcoded Values:**
```python
# In realtime_api.py
client = MongoClient("mongodb://localhost:27017", serverSelectionTimeoutMS=3000)

# In simple_mongodb_collector.py
def __init__(self, mongodb_url: str = "mongodb://localhost:27017", database_name: str = "model-collections"):
```

### **Environment Variables to Add:**
```bash
# Database Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=model-collections
MONGODB_TIMEOUT=3000
REDIS_URL=redis://localhost:6379
POSTGRES_URL=postgresql://user:pass@localhost:5432/crypto_trading
```

---

## 🌐 **API Server Configuration**

### **Current Hardcoded Values:**
```python
# In realtime_api.py
app.run(host='0.0.0.0', port=5001, debug=False)
print("🚀 Starting Real-time Crypto Data API Server on port 5001...")
```

### **Environment Variables to Add:**
```bash
# API Server Configuration
API_HOST=0.0.0.0
API_PORT=5001
API_DEBUG=false
API_LOG_LEVEL=INFO
```

---

## 📡 **Exchange API Endpoints**

### **Current Hardcoded Values:**
```python
# Binance
"https://api.binance.com/api/v3/klines"
"https://api.binance.com/api/v3/aggTrades"

# Bybit
"https://api.bybit.com/v5/market/kline"
"https://api.bybit.com/v5/market/recent-trade"

# Kraken
"https://api.kraken.com/0/public/OHLC"
"https://api.kraken.com/0/public/Trades"

# Gate.io
"https://api.gateio.ws/api/v4/spot/candlesticks"
"https://api.gateio.ws/api/v4/spot/trades"

# OKX
"https://www.okx.com/api/v5"
"wss://ws.okx.com:8443/ws/v5/public"
```

### **Environment Variables to Add:**
```bash
# Exchange API Endpoints
BINANCE_API_URL=https://api.binance.com/api/v3
BINANCE_WS_URL=wss://stream.binance.com:9443/ws

BYBIT_API_URL=https://api.bybit.com/v5
BYBIT_WS_URL=wss://stream.bybit.com/v5/public/linear

KRAKEN_API_URL=https://api.kraken.com/0/public
KRAKEN_WS_URL=wss://ws.kraken.com

GATE_API_URL=https://api.gateio.ws/api/v4
GATE_WS_URL=wss://api.gateio.ws/ws/v4

OKX_API_URL=https://www.okx.com/api/v5
OKX_WS_URL=wss://ws.okx.com:8443/ws/v5/public
```

---

## ⚙️ **Collection Configuration**

### **Current Hardcoded Values:**
```python
# In collector_config.py
COLLECTION_CONFIG = {
    "default_duration_seconds": 3600,  # 1 hour
    "default_poll_interval": 30,       # 30 seconds
    "log_level": "INFO",
    "graceful_shutdown_timeout": 30,   # 30 seconds
}
```

### **Environment Variables to Add:**
```bash
# Collection Configuration
COLLECTION_DURATION=3600
COLLECTION_POLL_INTERVAL=30
COLLECTION_LOG_LEVEL=INFO
COLLECTION_SHUTDOWN_TIMEOUT=30
COLLECTION_BATCH_SIZE=1000
COLLECTION_FLUSH_INTERVAL=5
```

---

## 🔄 **WebSocket Configuration**

### **Current Hardcoded Values:**
```python
# WebSocket ping intervals and timeouts
"websocket_ping_interval": 20,
"websocket_ping_timeout": 10,
```

### **Environment Variables to Add:**
```bash
# WebSocket Configuration
WS_PING_INTERVAL=20
WS_PING_TIMEOUT=10
WS_RECONNECT_DELAY=5
WS_MAX_RECONNECT_ATTEMPTS=10
```

---

## 📊 **Exchange Symbols**

### **Current Hardcoded Values:**
```python
# In collector_config.py
"symbols": ["BTCUSDT", "BTCUSDC"],
"symbols": ["BTCUSDT"],
"symbols": ["XBT/USD"],
"symbols": ["BTC_USDT"],
```

### **Environment Variables to Add:**
```bash
# Exchange Symbols (comma-separated)
BINANCE_SYMBOLS=BTCUSDT,BTCUSDC,BTCBUSD
BYBIT_SYMBOLS=BTCUSDT,BTCUSDC
KRAKEN_SYMBOLS=XBT/USD,XBT/USDC,XBT/USDT,XXBTZUSD
GATE_SYMBOLS=BTC_USDT,BTC_USDC
OKX_SYMBOLS=BTC-USDT,BTC-USDC
```

---

## 🚀 **Implementation Plan**

### **Step 1: Create Environment Configuration**

Create a new file `config.py`:

```python
import os
from typing import Dict, List, Any

class Config:
    """Configuration class that reads from environment variables with defaults."""
    
    # Database Configuration
    MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
    MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'model-collections')
    MONGODB_TIMEOUT = int(os.getenv('MONGODB_TIMEOUT', '3000'))
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    
    # API Server Configuration
    API_HOST = os.getenv('API_HOST', '0.0.0.0')
    API_PORT = int(os.getenv('API_PORT', '5001'))
    API_DEBUG = os.getenv('API_DEBUG', 'false').lower() == 'true'
    API_LOG_LEVEL = os.getenv('API_LOG_LEVEL', 'INFO')
    
    # Collection Configuration
    COLLECTION_DURATION = int(os.getenv('COLLECTION_DURATION', '3600'))
    COLLECTION_POLL_INTERVAL = int(os.getenv('COLLECTION_POLL_INTERVAL', '30'))
    COLLECTION_LOG_LEVEL = os.getenv('COLLECTION_LOG_LEVEL', 'INFO')
    COLLECTION_SHUTDOWN_TIMEOUT = int(os.getenv('COLLECTION_SHUTDOWN_TIMEOUT', '30'))
    
    # WebSocket Configuration
    WS_PING_INTERVAL = int(os.getenv('WS_PING_INTERVAL', '20'))
    WS_PING_TIMEOUT = int(os.getenv('WS_PING_TIMEOUT', '10'))
    WS_RECONNECT_DELAY = int(os.getenv('WS_RECONNECT_DELAY', '5'))
    WS_MAX_RECONNECT_ATTEMPTS = int(os.getenv('WS_MAX_RECONNECT_ATTEMPTS', '10'))
    
    # Exchange API URLs
    BINANCE_API_URL = os.getenv('BINANCE_API_URL', 'https://api.binance.com/api/v3')
    BYBIT_API_URL = os.getenv('BYBIT_API_URL', 'https://api.bybit.com/v5')
    KRAKEN_API_URL = os.getenv('KRAKEN_API_URL', 'https://api.kraken.com/0/public')
    GATE_API_URL = os.getenv('GATE_API_URL', 'https://api.gateio.ws/api/v4')
    OKX_API_URL = os.getenv('OKX_API_URL', 'https://www.okx.com/api/v5')
    
    # Exchange WebSocket URLs
    BINANCE_WS_URL = os.getenv('BINANCE_WS_URL', 'wss://stream.binance.com:9443/ws')
    BYBIT_WS_URL = os.getenv('BYBIT_WS_URL', 'wss://stream.bybit.com/v5/public/linear')
    KRAKEN_WS_URL = os.getenv('KRAKEN_WS_URL', 'wss://ws.kraken.com')
    GATE_WS_URL = os.getenv('GATE_WS_URL', 'wss://api.gateio.ws/ws/v4')
    OKX_WS_URL = os.getenv('OKX_WS_URL', 'wss://ws.okx.com:8443/ws/v5/public')
    
    # Exchange Symbols
    BINANCE_SYMBOLS = os.getenv('BINANCE_SYMBOLS', 'BTCUSDT,BTCUSDC,BTCBUSD').split(',')
    BYBIT_SYMBOLS = os.getenv('BYBIT_SYMBOLS', 'BTCUSDT,BTCUSDC').split(',')
    KRAKEN_SYMBOLS = os.getenv('KRAKEN_SYMBOLS', 'XBT/USD,XBT/USDC,XBT/USDT,XXBTZUSD').split(',')
    GATE_SYMBOLS = os.getenv('GATE_SYMBOLS', 'BTC_USDT,BTC_USDC').split(',')
    OKX_SYMBOLS = os.getenv('OKX_SYMBOLS', 'BTC-USDT,BTC-USDC').split(',')
    
    @classmethod
    def get_exchange_config(cls, exchange: str) -> Dict[str, Any]:
        """Get configuration for a specific exchange."""
        configs = {
            'binance': {
                'api_url': cls.BINANCE_API_URL,
                'ws_url': cls.BINANCE_WS_URL,
                'symbols': cls.BINANCE_SYMBOLS,
            },
            'bybit': {
                'api_url': cls.BYBIT_API_URL,
                'ws_url': cls.BYBIT_WS_URL,
                'symbols': cls.BYBIT_SYMBOLS,
            },
            'kraken': {
                'api_url': cls.KRAKEN_API_URL,
                'ws_url': cls.KRAKEN_WS_URL,
                'symbols': cls.KRAKEN_SYMBOLS,
            },
            'gate': {
                'api_url': cls.GATE_API_URL,
                'ws_url': cls.GATE_WS_URL,
                'symbols': cls.GATE_SYMBOLS,
            },
            'okx': {
                'api_url': cls.OKX_API_URL,
                'ws_url': cls.OKX_WS_URL,
                'symbols': cls.OKX_SYMBOLS,
            },
        }
        return configs.get(exchange, {})
```

### **Step 2: Create .env File**

Create a `.env` file with default values:

```bash
# Database Configuration
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=model-collections
MONGODB_TIMEOUT=3000
REDIS_URL=redis://localhost:6379

# API Server Configuration
API_HOST=0.0.0.0
API_PORT=5001
API_DEBUG=false
API_LOG_LEVEL=INFO

# Collection Configuration
COLLECTION_DURATION=3600
COLLECTION_POLL_INTERVAL=30
COLLECTION_LOG_LEVEL=INFO
COLLECTION_SHUTDOWN_TIMEOUT=30

# WebSocket Configuration
WS_PING_INTERVAL=20
WS_PING_TIMEOUT=10
WS_RECONNECT_DELAY=5
WS_MAX_RECONNECT_ATTEMPTS=10

# Exchange API URLs
BINANCE_API_URL=https://api.binance.com/api/v3
BYBIT_API_URL=https://api.bybit.com/v5
KRAKEN_API_URL=https://api.kraken.com/0/public
GATE_API_URL=https://api.gateio.ws/api/v4
OKX_API_URL=https://www.okx.com/api/v5

# Exchange WebSocket URLs
BINANCE_WS_URL=wss://stream.binance.com:9443/ws
BYBIT_WS_URL=wss://stream.bybit.com/v5/public/linear
KRAKEN_WS_URL=wss://ws.kraken.com
GATE_WS_URL=wss://api.gateio.ws/ws/v4
OKX_WS_URL=wss://ws.okx.com:8443/ws/v5/public

# Exchange Symbols
BINANCE_SYMBOLS=BTCUSDT,BTCUSDC,BTCBUSD
BYBIT_SYMBOLS=BTCUSDT,BTCUSDC
KRAKEN_SYMBOLS=XBT/USD,XBT/USDC,XBT/USDT,XXBTZUSD
GATE_SYMBOLS=BTC_USDT,BTC_USDC
OKX_SYMBOLS=BTC-USDT,BTC-USDC
```

### **Step 3: Update Files to Use Environment Variables**

#### **Update realtime_api.py:**
```python
from config import Config

# Replace hardcoded values
client = MongoClient(Config.MONGODB_URL, serverSelectionTimeoutMS=Config.MONGODB_TIMEOUT)
app.run(host=Config.API_HOST, port=Config.API_PORT, debug=Config.API_DEBUG)
```

#### **Update simple_mongodb_collector.py:**
```python
from config import Config

# Replace hardcoded values
def __init__(self, mongodb_url: str = Config.MONGODB_URL, database_name: str = Config.MONGODB_DATABASE):
```

#### **Update collector_config.py:**
```python
from config import Config

# Replace hardcoded values
COLLECTION_CONFIG = {
    "default_duration_seconds": Config.COLLECTION_DURATION,
    "default_poll_interval": Config.COLLECTION_POLL_INTERVAL,
    "log_level": Config.COLLECTION_LOG_LEVEL,
    "graceful_shutdown_timeout": Config.COLLECTION_SHUTDOWN_TIMEOUT,
}
```

---

## 🎯 **Benefits of Environment Variables**

### **1. Configuration Management**
- ✅ Easy to change settings without code changes
- ✅ Different configurations for dev/staging/production
- ✅ Secure handling of sensitive data

### **2. Deployment Flexibility**
- ✅ Docker container configuration
- ✅ Kubernetes config maps
- ✅ Cloud deployment settings

### **3. Security**
- ✅ No hardcoded credentials in code
- ✅ Environment-specific secrets
- ✅ Easy rotation of API keys

### **4. Maintenance**
- ✅ Centralized configuration
- ✅ Easy to update settings
- ✅ Better debugging and monitoring

---

## 🚀 **Implementation Priority**

### **High Priority (Immediate)**
1. **Database URLs** - MongoDB, Redis connections
2. **API Server** - Host, port, debug settings
3. **Collection Settings** - Duration, intervals, timeouts

### **Medium Priority (Next)**
1. **Exchange URLs** - API and WebSocket endpoints
2. **WebSocket Settings** - Ping intervals, timeouts
3. **Symbols** - Exchange-specific symbol lists

### **Low Priority (Future)**
1. **Advanced Settings** - Retry logic, batch sizes
2. **Monitoring** - Log levels, metrics intervals
3. **Performance** - Memory limits, CPU thresholds

---

## 📋 **Summary**

**Total Environment Variables Identified: 25**

- **Database**: 4 variables
- **API Server**: 4 variables  
- **Collection**: 4 variables
- **WebSocket**: 4 variables
- **Exchange URLs**: 10 variables
- **Exchange Symbols**: 5 variables

**Would you like me to implement these environment variables in your system?** This will make your system much more flexible and production-ready.
