# Cryptocurrency Exchange WebSocket Data Collector

A streamlined Python application for collecting real-time market data from 5 major cryptocurrency exchanges via WebSocket connections.

## 🚀 Features

- **5 Exchange Support**: Binance, Bybit, Kraken, OKX, and Gate.io
- **Real-Time Data**: Stream live market data, order book updates, and trade data
- **6 Data Types**: Market data, order book data, tick prices, volume/liquidity, funding rates, open interest
- **Symbol Mapping**: Automatic conversion between exchange-specific symbol formats
- **Flexible Configuration**: Easy configuration via environment variables
- **Data Export**: Export collected data to JSON format
- **Robust Error Handling**: Automatic reconnection and error recovery
- **Type Safety**: Built with Pydantic for data validation

## 📊 Supported Exchanges & Data Types

| Exchange | Market Data | Order Book | Tick Prices | Volume/Liquidity | Funding Rates | Open Interest |
|----------|-------------|------------|-------------|------------------|---------------|---------------|
| **Binance** | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ |
| **Bybit** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Kraken** | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **OKX** | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| **Gate.io** | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |

*Status as of latest test - some data types may need additional implementation*

## 🛠️ Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd exchanges-websockets
```

2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## 🚀 Quick Start

### Test All Exchanges
```bash
python test_exchanges.py
```

### Run Main Application
```bash
python main.py --exchanges binance bybit okx gate --symbols BTCUSDT ETHUSDT
```

### Programmatic Usage
```python
import asyncio
from exchanges.binance_client import BinanceWebSocketClient
from data_handler import DataHandler

async def collect_data():
    client = BinanceWebSocketClient(['BTCUSDT', 'ETHUSDT'])
    handler = DataHandler()
    
    client.add_data_handler(DataType.MARKET_DATA, handler.handle_market_data)
    
    await client.connect()
    await client.listen()

asyncio.run(collect_data())
```

## 📁 Project Structure

```
exchanges-websockets/
├── exchanges/                 # Exchange-specific clients
│   ├── binance_client.py     # Binance WebSocket client
│   ├── bybit_client.py       # Bybit WebSocket client
│   ├── kraken_client.py      # Kraken WebSocket client
│   ├── okx_client.py         # OKX WebSocket client
│   └── gate_client.py        # Gate.io WebSocket client
├── base_client.py            # Base WebSocket client class
├── models.py                 # Pydantic data models
├── data_handler.py           # Data processing and export
├── symbol_mapping.py         # Exchange symbol conversion
├── config.py                 # Configuration management
├── main.py                   # Main application entry point
├── test_exchanges.py         # Simple test script
└── requirements.txt          # Python dependencies
```

## 🔧 Configuration

### Environment Variables (Optional)
Create a `.env` file for API keys (not required for public data):

```env
# Exchange API Keys (for private data)
BINANCE_API_KEY=your_binance_api_key
BINANCE_SECRET_KEY=your_binance_secret_key
KRAKEN_API_KEY=your_kraken_api_key
KRAKEN_SECRET_KEY=your_kraken_secret_key
BYBIT_API_KEY=your_bybit_api_key
BYBIT_SECRET_KEY=your_bybit_secret_key
OKX_API_KEY=your_okx_api_key
OKX_SECRET_KEY=your_okx_secret_key
GATE_API_KEY=your_gate_api_key
GATE_SECRET_KEY=your_gate_secret_key

# WebSocket Configuration
WS_RECONNECT_INTERVAL=5
WS_TIMEOUT=30
MAX_RECONNECT_ATTEMPTS=10
LOG_LEVEL=INFO
```

## 📊 Data Types

- **Market Data**: Price, volume, bid/ask, 24h high/low, price change
- **Order Book Data**: Bid/ask levels with quantities
- **Tick Prices**: Individual trade data
- **Volume/Liquidity**: Trading volume and liquidity metrics
- **Funding Rates**: Perpetual futures funding rates
- **Open Interest**: Futures open interest data

## 🧪 Testing

Run the test script to verify all exchanges:
```bash
python test_exchanges.py
```

This will test all 5 exchanges for 15 seconds and show which data types are working.

## 📈 Usage Examples

### Custom Data Handler
```python
from models import WebSocketMessage, DataType

class MyDataHandler:
    def handle_market_data(self, message: WebSocketMessage):
        print(f"📈 {message.data.symbol}: ${message.data.price}")
    
    def handle_order_book(self, message: WebSocketMessage):
        print(f"📊 Order book update: {message.data.symbol}")

# Use with any client
client.add_data_handler(DataType.MARKET_DATA, MyDataHandler().handle_market_data)
```

### MongoDB Integration
```python
from mongodb_handler import MongoDBHandler

async def save_to_mongodb():
    mongo = MongoDBHandler()
    await mongo.connect()
    
    # Save market data
    await mongo.insert_data("market_data", [message.data.dict()])
```

## 🔍 Troubleshooting

### Common Issues

1. **Connection Timeouts**: Check internet connection and exchange availability
2. **No Data Received**: Some exchanges may have low activity for certain symbols
3. **Symbol Format Errors**: The symbol mapping system handles most conversions automatically

### Debug Mode
Set `LOG_LEVEL=DEBUG` in your environment to see detailed logs.

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📞 Support

For support and questions, please open an issue on GitHub.