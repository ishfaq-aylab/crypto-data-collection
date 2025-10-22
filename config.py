#!/usr/bin/env python3
"""Configuration class that reads from environment variables with defaults."""

import os
from typing import Dict, List, Any

class Config:
    """Configuration class that reads from environment variables with defaults."""
    
    # Database Configuration
    MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
    MONGODB_DATABASE = os.getenv('MONGODB_DATABASE', 'model-collections')
    MONGODB_TIMEOUT = int(os.getenv('MONGODB_TIMEOUT', '3000'))
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379')
    POSTGRES_URL = os.getenv('POSTGRES_URL', 'postgresql://user:pass@localhost:5432/crypto_trading')
    
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
    COLLECTION_BATCH_SIZE = int(os.getenv('COLLECTION_BATCH_SIZE', '1000'))
    COLLECTION_FLUSH_INTERVAL = int(os.getenv('COLLECTION_FLUSH_INTERVAL', '5'))
    
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
    
    # Exchange API Keys (optional for public data)
    BINANCE_API_KEY = os.getenv('BINANCE_API_KEY', '')
    BINANCE_SECRET_KEY = os.getenv('BINANCE_SECRET_KEY', '')
    BYBIT_API_KEY = os.getenv('BYBIT_API_KEY', '')
    BYBIT_SECRET_KEY = os.getenv('BYBIT_SECRET_KEY', '')
    KRAKEN_API_KEY = os.getenv('KRAKEN_API_KEY', '')
    KRAKEN_SECRET_KEY = os.getenv('KRAKEN_SECRET_KEY', '')
    GATE_API_KEY = os.getenv('GATE_API_KEY', '')
    GATE_SECRET_KEY = os.getenv('GATE_SECRET_KEY', '')
    OKX_API_KEY = os.getenv('OKX_API_KEY', '')
    OKX_SECRET_KEY = os.getenv('OKX_SECRET_KEY', '')
    
    # Monitoring Configuration
    MONITORING_ENABLED = os.getenv('MONITORING_ENABLED', 'true').lower() == 'true'
    METRICS_INTERVAL = int(os.getenv('METRICS_INTERVAL', '300'))  # 5 minutes
    LOG_STATS_INTERVAL = int(os.getenv('LOG_STATS_INTERVAL', '600'))  # 10 minutes
    MAX_MEMORY_USAGE_MB = int(os.getenv('MAX_MEMORY_USAGE_MB', '1000'))
    MAX_CPU_USAGE_PERCENT = int(os.getenv('MAX_CPU_USAGE_PERCENT', '80'))
    
    # Error Handling Configuration
    MAX_RETRIES = int(os.getenv('MAX_RETRIES', '3'))
    RETRY_DELAY = int(os.getenv('RETRY_DELAY', '5'))
    CONNECTION_TIMEOUT = int(os.getenv('CONNECTION_TIMEOUT', '30'))
    MAX_CONSECUTIVE_FAILURES = int(os.getenv('MAX_CONSECUTIVE_FAILURES', '10'))
    ALERT_ON_FAILURE = os.getenv('ALERT_ON_FAILURE', 'true').lower() == 'true'
    
    @classmethod
    def get_exchange_config(cls, exchange: str) -> Dict[str, Any]:
        """Get configuration for a specific exchange."""
        configs = {
            'binance': {
                'api_url': cls.BINANCE_API_URL,
                'ws_url': cls.BINANCE_WS_URL,
                'symbols': cls.BINANCE_SYMBOLS,
                'api_key': cls.BINANCE_API_KEY,
                'secret_key': cls.BINANCE_SECRET_KEY,
            },
            'bybit': {
                'api_url': cls.BYBIT_API_URL,
                'ws_url': cls.BYBIT_WS_URL,
                'symbols': cls.BYBIT_SYMBOLS,
                'api_key': cls.BYBIT_API_KEY,
                'secret_key': cls.BYBIT_SECRET_KEY,
            },
            'kraken': {
                'api_url': cls.KRAKEN_API_URL,
                'ws_url': cls.KRAKEN_WS_URL,
                'symbols': cls.KRAKEN_SYMBOLS,
                'api_key': cls.KRAKEN_API_KEY,
                'secret_key': cls.KRAKEN_SECRET_KEY,
            },
            'gate': {
                'api_url': cls.GATE_API_URL,
                'ws_url': cls.GATE_WS_URL,
                'symbols': cls.GATE_SYMBOLS,
                'api_key': cls.GATE_API_KEY,
                'secret_key': cls.GATE_SECRET_KEY,
            },
            'okx': {
                'api_url': cls.OKX_API_URL,
                'ws_url': cls.OKX_WS_URL,
                'symbols': cls.OKX_SYMBOLS,
                'api_key': cls.OKX_API_KEY,
                'secret_key': cls.OKX_SECRET_KEY,
            },
        }
        return configs.get(exchange, {})
    
    @classmethod
    def get_database_config(cls) -> Dict[str, Any]:
        """Get database configuration."""
        return {
            'mongodb_url': cls.MONGODB_URL,
            'mongodb_database': cls.MONGODB_DATABASE,
            'mongodb_timeout': cls.MONGODB_TIMEOUT,
            'redis_url': cls.REDIS_URL,
            'postgres_url': cls.POSTGRES_URL,
        }
    
    @classmethod
    def get_api_config(cls) -> Dict[str, Any]:
        """Get API server configuration."""
        return {
            'host': cls.API_HOST,
            'port': cls.API_PORT,
            'debug': cls.API_DEBUG,
            'log_level': cls.API_LOG_LEVEL,
        }
    
    @classmethod
    def get_collection_config(cls) -> Dict[str, Any]:
        """Get collection configuration."""
        return {
            'duration': cls.COLLECTION_DURATION,
            'poll_interval': cls.COLLECTION_POLL_INTERVAL,
            'log_level': cls.COLLECTION_LOG_LEVEL,
            'shutdown_timeout': cls.COLLECTION_SHUTDOWN_TIMEOUT,
            'batch_size': cls.COLLECTION_BATCH_SIZE,
            'flush_interval': cls.COLLECTION_FLUSH_INTERVAL,
        }
    
    @classmethod
    def get_websocket_config(cls) -> Dict[str, Any]:
        """Get WebSocket configuration."""
        return {
            'ping_interval': cls.WS_PING_INTERVAL,
            'ping_timeout': cls.WS_PING_TIMEOUT,
            'reconnect_delay': cls.WS_RECONNECT_DELAY,
            'max_reconnect_attempts': cls.WS_MAX_RECONNECT_ATTEMPTS,
        }
    
    @classmethod
    def get_monitoring_config(cls) -> Dict[str, Any]:
        """Get monitoring configuration."""
        return {
            'enabled': cls.MONITORING_ENABLED,
            'metrics_interval': cls.METRICS_INTERVAL,
            'log_stats_interval': cls.LOG_STATS_INTERVAL,
            'max_memory_usage_mb': cls.MAX_MEMORY_USAGE_MB,
            'max_cpu_usage_percent': cls.MAX_CPU_USAGE_PERCENT,
        }
    
    @classmethod
    def get_error_config(cls) -> Dict[str, Any]:
        """Get error handling configuration."""
        return {
            'max_retries': cls.MAX_RETRIES,
            'retry_delay': cls.RETRY_DELAY,
            'connection_timeout': cls.CONNECTION_TIMEOUT,
            'max_consecutive_failures': cls.MAX_CONSECUTIVE_FAILURES,
            'alert_on_failure': cls.ALERT_ON_FAILURE,
        }
    
    @classmethod
    def print_config(cls):
        """Print current configuration (without sensitive data)."""
        print("🔧 Current Configuration:")
        print("=" * 50)
        print(f"📊 Database: {cls.MONGODB_DATABASE} @ {cls.MONGODB_URL}")
        print(f"🌐 API Server: {cls.API_HOST}:{cls.API_PORT} (debug={cls.API_DEBUG})")
        print(f"📡 Collection: {cls.COLLECTION_DURATION}s duration, {cls.COLLECTION_POLL_INTERVAL}s interval")
        print(f"🔄 WebSocket: {cls.WS_PING_INTERVAL}s ping, {cls.WS_PING_TIMEOUT}s timeout")
        print(f"📈 Monitoring: {'Enabled' if cls.MONITORING_ENABLED else 'Disabled'}")
        print(f"🛡️ Error Handling: {cls.MAX_RETRIES} retries, {cls.RETRY_DELAY}s delay")
        print("=" * 50)
