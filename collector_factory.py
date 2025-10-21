#!/usr/bin/env python3
"""Factory for creating data collectors with plugin support."""

from typing import Dict, List, Optional, Type
from loguru import logger

from interfaces import ICollectorFactory, IDataCollector, CollectorType, DataType
from collector_config import get_enabled_exchanges, get_exchange_config
from collector_adapter import create_collector_adapter


class CollectorFactory(ICollectorFactory):
    """Factory for creating data collectors."""
    
    def __init__(self):
        self._collector_registry: Dict[str, Dict[CollectorType, Type[IDataCollector]]] = {}
        self._register_builtin_collectors()
    
    def _register_builtin_collectors(self):
        """Register all built-in collectors."""
        # Import collectors here to avoid circular imports
        from binance_realtime_collector import BinanceRealtimeCollector
        from binance_funding_rates_collector import BinanceFundingRatesCollector
        from binance_open_interest_collector import BinanceOpenInterestCollector
        
        from bybit_realtime_collector import BybitRealtimeCollector
        from bybit_funding_rates_collector import BybitFundingRatesCollector
        from bybit_open_interest_collector import BybitOpenInterestCollector
        
        from robust_kraken_collector import RobustKrakenCollector
        from kraken_futures_collector import KrakenFuturesCollector
        
        from gate_realtime_collector import GateRealtimeCollector
        from gate_futures_collector import GateFuturesCollector
        
        from okx_realtime_collector import OKXRealtimeCollector
        from okx_futures_websocket_collector import OKXFuturesWebSocketCollector
        
        # Register Binance collectors
        self._register_exchange_collectors("binance", {
            CollectorType.REALTIME: BinanceRealtimeCollector,
            CollectorType.FUTURES: BinanceFundingRatesCollector,  # Funding rates
        })
        
        # Register Bybit collectors
        self._register_exchange_collectors("bybit", {
            CollectorType.REALTIME: BybitRealtimeCollector,
            CollectorType.FUTURES: BybitFundingRatesCollector,  # Funding rates
        })
        
        # Register Kraken collectors
        self._register_exchange_collectors("kraken", {
            CollectorType.REALTIME: RobustKrakenCollector,
            CollectorType.FUTURES: KrakenFuturesCollector,
        })
        
        # Register Gate.io collectors
        self._register_exchange_collectors("gate", {
            CollectorType.REALTIME: GateRealtimeCollector,
            CollectorType.FUTURES: GateFuturesCollector,
        })
        
        # Register OKX collectors
        self._register_exchange_collectors("okx", {
            CollectorType.REALTIME: OKXRealtimeCollector,
            CollectorType.FUTURES: OKXFuturesWebSocketCollector,
        })
        
        logger.info(f"✅ Registered collectors for {len(self._collector_registry)} exchanges")
    
    def _register_exchange_collectors(self, exchange: str, collectors: Dict[CollectorType, Type[IDataCollector]]):
        """Register collectors for an exchange."""
        if exchange not in self._collector_registry:
            self._collector_registry[exchange] = {}
        
        self._collector_registry[exchange].update(collectors)
        logger.debug(f"📝 Registered {len(collectors)} collectors for {exchange}")
    
    def register_collector(self, exchange: str, collector_type: CollectorType, 
                          collector_class: Type[IDataCollector]) -> None:
        """Register a new collector class."""
        if exchange not in self._collector_registry:
            self._collector_registry[exchange] = {}
        
        self._collector_registry[exchange][collector_type] = collector_class
        logger.info(f"📝 Registered {collector_class.__name__} for {exchange}.{collector_type.value}")
    
    def create_collector(self, exchange: str, collector_type: CollectorType, 
                        **kwargs) -> Optional[IDataCollector]:
        """Create a collector instance."""
        try:
            # Check if exchange is enabled
            if not self._is_exchange_enabled(exchange):
                logger.warning(f"⚠️  Exchange {exchange} is not enabled")
                return None
            
            # Get collector class
            if exchange not in self._collector_registry:
                logger.error(f"❌ No collectors registered for exchange: {exchange}")
                return None
            
            if collector_type not in self._collector_registry[exchange]:
                logger.error(f"❌ No {collector_type.value} collector for exchange: {exchange}")
                return None
            
            collector_class = self._collector_registry[exchange][collector_type]
            
            # Create instance
            existing_collector = collector_class(**kwargs)
            
            # Create adapter to make it compatible with new interface
            data_types = self._get_data_types_for_collector(exchange, collector_type)
            symbols = kwargs.get('symbols', [])
            
            collector = create_collector_adapter(
                existing_collector=existing_collector,
                exchange=exchange,
                collector_type=collector_type,
                data_types=data_types,
                symbols=symbols
            )
            
            logger.debug(f"✅ Created {collector.name}")
            return collector
            
        except Exception as e:
            logger.error(f"❌ Error creating collector {exchange}.{collector_type.value}: {e}")
            return None
    
    def get_supported_exchanges(self) -> List[str]:
        """Get list of supported exchanges."""
        return list(self._collector_registry.keys())
    
    def get_supported_collector_types(self, exchange: str) -> List[CollectorType]:
        """Get supported collector types for an exchange."""
        if exchange not in self._collector_registry:
            return []
        
        return list(self._collector_registry[exchange].keys())
    
    def get_all_collector_configs(self) -> List[Dict[str, str]]:
        """Get all possible collector configurations."""
        configs = []
        
        for exchange in self.get_supported_exchanges():
            if not self._is_exchange_enabled(exchange):
                continue
                
            for collector_type in self.get_supported_collector_types(exchange):
                configs.append({
                    "exchange": exchange,
                    "collector_type": collector_type.value,
                    "name": f"{exchange}_{collector_type.value}"
                })
        
        return configs
    
    def _is_exchange_enabled(self, exchange: str) -> bool:
        """Check if exchange is enabled in configuration."""
        try:
            from collector_config import is_exchange_enabled
            return is_exchange_enabled(exchange)
        except ImportError:
            return True  # Default to enabled if config not available
    
    def _get_data_types_for_collector(self, exchange: str, collector_type: CollectorType) -> List[DataType]:
        """Get data types for a collector."""
        if collector_type == CollectorType.REALTIME:
            return [DataType.MARKET_DATA, DataType.TICK_PRICES, DataType.ORDER_BOOK_DATA, DataType.VOLUME_LIQUIDITY]
        elif collector_type == CollectorType.FUTURES:
            return [DataType.FUNDING_RATES, DataType.OPEN_INTEREST]
        else:
            return []


# Global factory instance
collector_factory = CollectorFactory()


def get_collector_factory() -> CollectorFactory:
    """Get the global collector factory instance."""
    return collector_factory
