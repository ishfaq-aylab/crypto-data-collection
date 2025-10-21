#!/usr/bin/env python3
"""Base interfaces and abstract classes for the data collection system."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum


class CollectorType(Enum):
    """Types of data collectors."""
    REALTIME = "realtime"
    FUTURES = "futures"
    REST = "rest"
    WEBSOCKET = "websocket"


class DataType(Enum):
    """Types of data being collected."""
    MARKET_DATA = "market_data"
    TICK_PRICES = "tick_prices"
    ORDER_BOOK_DATA = "order_book_data"
    VOLUME_LIQUIDITY = "volume_liquidity"
    FUNDING_RATES = "funding_rates"
    OPEN_INTEREST = "open_interest"


class CollectorStatus(Enum):
    """Status of a collector."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    COMPLETED = "completed"


class IDataCollector(ABC):
    """Base interface for all data collectors."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Get collector name."""
        pass
    
    @property
    @abstractmethod
    def exchange(self) -> str:
        """Get exchange name."""
        pass
    
    @property
    @abstractmethod
    def collector_type(self) -> CollectorType:
        """Get collector type."""
        pass
    
    @property
    @abstractmethod
    def data_types(self) -> List[DataType]:
        """Get supported data types."""
        pass
    
    @property
    @abstractmethod
    def status(self) -> CollectorStatus:
        """Get current status."""
        pass
    
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the collector."""
        pass
    
    @abstractmethod
    async def start(self, duration_seconds: int = 0, **kwargs) -> None:
        """Start data collection."""
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop data collection."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        pass
    
    @abstractmethod
    def is_healthy(self) -> bool:
        """Check if collector is healthy."""
        pass


class ICollectorFactory(ABC):
    """Factory interface for creating collectors."""
    
    @abstractmethod
    def create_collector(self, exchange: str, collector_type: CollectorType) -> Optional[IDataCollector]:
        """Create a collector instance."""
        pass
    
    @abstractmethod
    def get_supported_exchanges(self) -> List[str]:
        """Get list of supported exchanges."""
        pass
    
    @abstractmethod
    def get_supported_collector_types(self, exchange: str) -> List[CollectorType]:
        """Get supported collector types for an exchange."""
        pass


class IConfigurationManager(ABC):
    """Configuration management interface."""
    
    @abstractmethod
    def get_exchange_config(self, exchange: str) -> Dict[str, Any]:
        """Get exchange configuration."""
        pass
    
    @abstractmethod
    def get_data_type_config(self, data_type: str) -> Dict[str, Any]:
        """Get data type configuration."""
        pass
    
    @abstractmethod
    def is_exchange_enabled(self, exchange: str) -> bool:
        """Check if exchange is enabled."""
        pass
    
    @abstractmethod
    def is_data_type_enabled(self, data_type: str) -> bool:
        """Check if data type is enabled."""
        pass
    
    @abstractmethod
    def validate_config(self) -> List[str]:
        """Validate configuration and return errors."""
        pass


class IMonitoringService(ABC):
    """Monitoring service interface."""
    
    @abstractmethod
    def record_metric(self, name: str, value: float, tags: Dict[str, str] = None) -> None:
        """Record a metric."""
        pass
    
    @abstractmethod
    def record_event(self, event: str, data: Dict[str, Any] = None) -> None:
        """Record an event."""
        pass
    
    @abstractmethod
    def get_health_status(self) -> Dict[str, Any]:
        """Get overall health status."""
        pass
    
    @abstractmethod
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        pass


class IErrorHandler(ABC):
    """Error handling interface."""
    
    @abstractmethod
    async def handle_error(self, error: Exception, context: Dict[str, Any]) -> bool:
        """Handle an error and return True if recovered."""
        pass
    
    @abstractmethod
    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Check if operation should be retried."""
        pass
    
    @abstractmethod
    def get_retry_delay(self, error: Exception, attempt: int) -> float:
        """Get retry delay in seconds."""
        pass


class IDataStorage(ABC):
    """Data storage interface."""
    
    @abstractmethod
    async def store_message(self, message: Any) -> bool:
        """Store a message."""
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        """Connect to storage."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from storage."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics."""
        pass


class IOrchestrator(ABC):
    """Orchestrator interface."""
    
    @abstractmethod
    async def start_collection(self, duration_seconds: int = 0, **kwargs) -> None:
        """Start data collection."""
        pass
    
    @abstractmethod
    async def stop_collection(self) -> None:
        """Stop data collection."""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        pass
    
    @abstractmethod
    def get_collector_status(self, collector_name: str) -> Optional[Dict[str, Any]]:
        """Get specific collector status."""
        pass
    
    @abstractmethod
    async def restart_collector(self, collector_name: str) -> bool:
        """Restart a specific collector."""
        pass
