#!/usr/bin/env python3
"""Configuration for data collection orchestrator."""

from typing import Dict, List, Any
from config import Config

# Collection configuration
COLLECTION_CONFIG = {
    "default_duration_seconds": 3600,  # 1 hour
    "default_poll_interval": 30,       # 30 seconds for REST API polling
    "log_level": "INFO",
    "graceful_shutdown_timeout": 30,   # 30 seconds
}

# Exchange-specific configurations
EXCHANGE_CONFIGS = {
    "binance": {
        "enabled": True,
        "realtime_enabled": True,
        "futures_enabled": True,
        "symbols": ["BTCUSDT", "BTCUSDC"],
        "websocket_ping_interval": 20,
        "websocket_ping_timeout": 10,
    },
    "bybit": {
        "enabled": True,
        "realtime_enabled": True,
        "futures_enabled": True,
        "symbols": ["BTCUSDT"],  # BTCUSDC not available on Bybit
        "websocket_ping_interval": 20,
        "websocket_ping_timeout": 10,
    },
    "kraken": {
        "enabled": True,
        "realtime_enabled": True,
        "futures_enabled": True,
        "symbols": ["XBT/USD"],  # Kraken format
        "websocket_ping_interval": 20,
        "websocket_ping_timeout": 10,
    },
    "gate": {
        "enabled": True,
        "realtime_enabled": True,
        "futures_enabled": True,
        "symbols": ["BTC_USDT"],  # Gate.io format
        "websocket_ping_interval": 20,
        "websocket_ping_timeout": 10,
    },
    "okx": {
        "enabled": True,
        "realtime_enabled": True,
        "futures_enabled": True,
        "symbols": ["BTC-USDT-SWAP", "BTC-USDC-SWAP"],  # OKX format
        "websocket_ping_interval": 20,
        "websocket_ping_timeout": 10,
    }
}

# Data type configurations
DATA_TYPE_CONFIGS = {
    "market_data": {
        "enabled": True,
        "collection_method": "websocket",
        "frequency": "realtime",
        "retention_days": 365,
    },
    "tick_prices": {
        "enabled": True,
        "collection_method": "websocket",
        "frequency": "realtime",
        "retention_days": 365,
    },
    "order_book_data": {
        "enabled": True,
        "collection_method": "websocket",
        "frequency": "realtime",
        "retention_days": 365,
    },
    "volume_liquidity": {
        "enabled": True,
        "collection_method": "websocket",
        "frequency": "realtime",
        "retention_days": 365,
    },
    "funding_rates": {
        "enabled": True,
        "collection_method": "websocket_rest",
        "frequency": "8_hours",
        "retention_days": 365,
    },
    "open_interest": {
        "enabled": True,
        "collection_method": "websocket_rest",
        "frequency": "5_15_minutes",
        "retention_days": 365,
    }
}

# MongoDB configuration
MONGODB_CONFIG = {
    "host": Config.MONGODB_URL.split("://")[1].split(":")[0],
    "port": int(Config.MONGODB_URL.split(":")[-1]),
    "database": Config.MONGODB_DATABASE,
    "collections": {
        "market_data": "market_data",
        "tick_prices": "tick_prices", 
        "order_book_data": "order_book_data",
        "volume_liquidity": "volume_liquidity",
        "funding_rates": "funding_rates",
        "open_interest": "open_interest"
    },
    "indexes": {
        "market_data": [
            {"exchange": 1, "symbol": 1},
            {"timestamp": -1},
            {"exchange": 1, "timestamp": -1}
        ],
        "tick_prices": [
            {"exchange": 1, "symbol": 1},
            {"timestamp": -1},
            {"exchange": 1, "timestamp": -1}
        ],
        "order_book_data": [
            {"exchange": 1, "symbol": 1},
            {"timestamp": -1},
            {"exchange": 1, "timestamp": -1}
        ],
        "volume_liquidity": [
            {"exchange": 1, "symbol": 1},
            {"timestamp": -1},
            {"exchange": 1, "timestamp": -1}
        ],
        "funding_rates": [
            {"exchange": 1, "symbol": 1},
            {"timestamp": -1},
            {"funding_time": -1}
        ],
        "open_interest": [
            {"exchange": 1, "symbol": 1},
            {"timestamp": -1}
        ]
    }
}

# Error handling configuration
ERROR_CONFIG = {
    "max_retries": 3,
    "retry_delay": 5,  # seconds
    "connection_timeout": 30,  # seconds
    "max_consecutive_failures": 10,
    "alert_on_failure": True,
}

# Performance monitoring
PERFORMANCE_CONFIG = {
    "enable_metrics": True,
    "metrics_interval": 300,  # 5 minutes
    "log_stats_interval": 600,  # 10 minutes
    "max_memory_usage_mb": 1000,
    "max_cpu_usage_percent": 80,
}

def get_exchange_config(exchange: str) -> Dict[str, Any]:
    """Get configuration for a specific exchange."""
    return EXCHANGE_CONFIGS.get(exchange, {})

def get_data_type_config(data_type: str) -> Dict[str, Any]:
    """Get configuration for a specific data type."""
    return DATA_TYPE_CONFIGS.get(data_type, {})

def is_exchange_enabled(exchange: str) -> bool:
    """Check if an exchange is enabled."""
    config = get_exchange_config(exchange)
    return config.get("enabled", False)

def is_data_type_enabled(data_type: str) -> bool:
    """Check if a data type is enabled."""
    config = get_data_type_config(data_type)
    return config.get("enabled", False)

def get_enabled_exchanges() -> List[str]:
    """Get list of enabled exchanges."""
    return [exchange for exchange, config in EXCHANGE_CONFIGS.items() 
            if config.get("enabled", False)]

def get_enabled_data_types() -> List[str]:
    """Get list of enabled data types."""
    return [data_type for data_type, config in DATA_TYPE_CONFIGS.items() 
            if config.get("enabled", False)]
