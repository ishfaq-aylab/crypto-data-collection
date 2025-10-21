# 🚀 Production Crypto Trading Data Collection System

A high-performance, production-ready system for collecting real-time cryptocurrency market data from multiple exchanges for trading agent backtesting.

## 📊 Data Types Collected

- **Market Data**: Real-time price updates, 24hr statistics
- **Order Book Data**: Real-time order book depth and updates
- **Tick Prices (Trades)**: Live trade executions and prices
- **Volume/Liquidity**: Trading volume and liquidity metrics
- **Funding Rates**: Perpetual futures funding rates
- **Open Interest**: Open interest data for derivatives

## 🏗️ Architecture

### Multi-Tier Storage
- **Hot Storage (Redis)**: Real-time data for immediate trading decisions
- **Warm Storage (MongoDB)**: Recent data for backtesting and analysis
- **Cold Storage (PostgreSQL)**: Historical data for long-term backtesting

### Supported Exchanges
- ✅ Binance
- ✅ Bybit
- ✅ Kraken
- ✅ OKX
- ✅ Gate.io

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- MongoDB 7.0+
- Redis 7.0+
- PostgreSQL 15+ (optional)

### Installation

1. **Clone and setup**:
```bash
git clone <your-repo>
cd exchanges-websockets
pip install -r requirements_production.txt
```

2. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your database URLs and API keys
```

3. **Run database optimization**:
```bash
python database_schema.py
```

4. **Start data collection**:
```bash
python production_deployment.py
```

### Docker Deployment

1. **Start all services**:
```bash
docker-compose up -d
```

2. **Check status**:
```bash
docker-compose ps
docker-compose logs -f data_collector
```

## 📁 File Structure

```
exchanges-websockets/
├── production_data_collector.py    # Main data collection system
├── database_schema.py              # Database optimization
├── monitoring_system.py            # Monitoring and alerting
├── production_deployment.py        # Deployment manager
├── requirements_production.txt     # Production dependencies
├── Dockerfile                      # Docker configuration
├── docker-compose.yml             # Multi-service deployment
├── production_config.yaml         # Configuration file
└── PRODUCTION_README.md           # This file
```

## ⚙️ Configuration

### Environment Variables

```bash
# Database URLs
MONGODB_URL=mongodb://localhost:27017
REDIS_URL=redis://localhost:6379
POSTGRES_URL=postgresql://user:pass@localhost:5432/crypto_trading

# Exchange API Keys (optional for public data)
BINANCE_API_KEY=your_binance_key
BINANCE_SECRET_KEY=your_binance_secret
# ... other exchanges

# Monitoring
LOG_LEVEL=INFO
MONITORING_ENABLED=true
EMAIL_ALERTS_ENABLED=false
WEBHOOK_ALERTS_ENABLED=false
```

### Configuration File (production_config.yaml)

```yaml
database:
  mongodb_url: 'mongodb://localhost:27017'
  redis_url: 'redis://localhost:6379'
  postgres_url: 'postgresql://user:pass@localhost:5432/crypto_trading'

exchanges:
  binance:
    enabled: true
    symbols: ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
  bybit:
    enabled: true
    symbols: ['BTCUSDT', 'ETHUSDT', 'ADAUSDT']
  # ... other exchanges

data_collection:
  enabled_data_types:
    - market_data
    - order_book_data
    - tick_prices
    - volume_liquidity
    - funding_rates
    - open_interest
  batch_size: 1000
  flush_interval: 5
  retention_days: 30

monitoring:
  enabled: true
  interval_seconds: 30
  email_alerts:
    enabled: false
    smtp_server: 'smtp.gmail.com'
    # ... email config
```

## 📈 Performance Features

### Data Quality
- **Real-time validation**: All incoming data is validated before storage
- **Quality metrics**: Track data freshness, latency, and success rates
- **Error handling**: Robust error handling with automatic recovery

### Performance Optimization
- **Compound indexes**: Optimized database indexes for fast queries
- **Batch processing**: Efficient batch storage for high-frequency data
- **Memory management**: Automatic cleanup of old data
- **Connection pooling**: Optimized database connections

### Monitoring
- **Real-time metrics**: Track system performance and data quality
- **Alerting**: Email and webhook alerts for system issues
- **Health checks**: Automated health monitoring
- **Performance dashboards**: Grafana dashboards for visualization

## 🔧 Usage Examples

### Basic Data Collection

```python
from production_data_collector import ProductionDataCollector, ProductionDataFeeder

# Initialize collector
collector = ProductionDataCollector()

# Initialize feeder
feeder = ProductionDataFeeder(collector)
await feeder.initialize_clients(['BTCUSDT', 'ETHUSDT'])

# Start collecting data
await feeder.start_feeding()
```

### Querying Data

```python
# Get latest market data
latest_data = await collector.get_latest_data(
    data_type=DataType.MARKET_DATA,
    symbol='BTCUSDT',
    exchange='binance',
    limit=100
)

# Get historical data
historical_data = await collector.get_historical_data(
    data_type=DataType.ORDER_BOOK_DATA,
    symbol='BTCUSDT',
    start_time=datetime.now() - timedelta(hours=1),
    end_time=datetime.now(),
    limit=1000
)
```

### Monitoring System Health

```python
from monitoring_system import MonitoringSystem

monitor = MonitoringSystem()
health = await monitor.get_system_health()
print(f"System status: {health['status']}")
print(f"Success rate: {health['avg_success_rate']:.2%}")
```

## 📊 Database Schema

### MongoDB Collections
- `market_data`: Real-time market data
- `order_book_data`: Order book snapshots
- `tick_prices`: Trade executions
- `volume_liquidity`: Volume and liquidity data
- `funding_rates`: Funding rate updates
- `open_interest`: Open interest data
- `system_metrics`: Performance metrics
- `alerts`: System alerts

### Redis Keys
- `{exchange}:{data_type}:{symbol}`: Latest data
- `timeline:{exchange}:{data_type}`: Time-ordered data
- `metrics:{exchange}:{data_type}:*`: Performance metrics
- `active_symbols`: Currently tracked symbols

## 🚨 Monitoring and Alerting

### Alert Rules
- **Low Success Rate**: < 95% data collection success
- **High Latency**: > 1000ms average latency
- **No Data Received**: No data for 5 minutes
- **High Error Rate**: > 100 errors in 5 minutes
- **High Memory Usage**: > 1GB memory usage
- **High CPU Usage**: > 80% CPU usage

### Alert Channels
- **Email**: SMTP email notifications
- **Webhook**: HTTP webhook notifications (Slack, Discord, etc.)
- **Logs**: Structured logging with Loguru

## 🔒 Security

### API Key Management
- Store API keys in environment variables
- Use read-only permissions for data collection
- Implement IP whitelisting where possible
- Rotate keys regularly

### Data Security
- Encrypt sensitive data at rest
- Use secure connections (TLS/SSL)
- Implement access controls
- Regular security audits

## 📈 Scaling

### Horizontal Scaling
- Run multiple collector instances
- Use load balancers for database connections
- Implement data sharding
- Use message queues for high throughput

### Vertical Scaling
- Increase server resources
- Optimize database configurations
- Use faster storage (SSD)
- Implement caching layers

## 🛠️ Troubleshooting

### Common Issues

1. **Connection Failures**:
   - Check network connectivity
   - Verify API keys and permissions
   - Check rate limits

2. **Data Quality Issues**:
   - Monitor data validation logs
   - Check exchange API status
   - Verify symbol mappings

3. **Performance Issues**:
   - Check database indexes
   - Monitor memory usage
   - Optimize query patterns

### Debug Commands

```bash
# Check system status
python -c "from production_deployment import ProductionDeployment; import asyncio; print(asyncio.run(ProductionDeployment().get_system_status()))"

# Check database health
python -c "from database_schema import DatabaseSchemaOptimizer; DatabaseSchemaOptimizer().run_full_optimization()"

# Test data collection
python -c "from production_data_collector import main; import asyncio; asyncio.run(main())"
```

## 📚 API Reference

### ProductionDataCollector
- `store_message(message)`: Store WebSocket message
- `get_latest_data(data_type, symbol, exchange, limit)`: Get latest data
- `get_historical_data(data_type, symbol, start_time, end_time, limit)`: Get historical data
- `get_performance_stats()`: Get performance statistics
- `cleanup_old_data(days_to_keep)`: Clean up old data

### MonitoringSystem
- `start_monitoring(interval_seconds)`: Start monitoring
- `get_system_health()`: Get system health status
- `get_alert_history(hours)`: Get alert history

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review the logs for error messages

## 🔄 Updates

### Version 1.0.0
- Initial production release
- Support for 5 major exchanges
- Multi-tier storage architecture
- Comprehensive monitoring system
- Docker deployment support

---

**⚠️ Important**: This system is designed for production use. Always test thoroughly in a staging environment before deploying to production. Monitor system resources and implement proper backup strategies.
