#!/usr/bin/env python3
"""Base collector implementation with common functionality."""

import asyncio
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from loguru import logger

from interfaces import IDataCollector, CollectorType, DataType, CollectorStatus
from simple_mongodb_collector import SimpleMongoDBCollector


class BaseCollector(IDataCollector):
    """Base implementation for all data collectors."""
    
    def __init__(self, exchange: str, collector_type: CollectorType, 
                 data_types: List[DataType], symbols: List[str] = None):
        self._exchange = exchange
        self._collector_type = collector_type
        self._data_types = data_types
        self._symbols = symbols or []
        self._status = CollectorStatus.STOPPED
        self._mongo = SimpleMongoDBCollector()
        self._stats = {
            "messages_received": 0,
            "messages_stored": 0,
            "errors": 0,
            "start_time": None,
            "last_activity": None,
            "consecutive_errors": 0
        }
        self._error_handlers: List[Callable] = []
        self._health_check_interval = 30  # seconds
        self._last_health_check = None
        self._is_healthy = True
    
    @property
    def name(self) -> str:
        """Get collector name."""
        return f"{self._exchange}_{self._collector_type.value}"
    
    @property
    def exchange(self) -> str:
        """Get exchange name."""
        return self._exchange
    
    @property
    def collector_type(self) -> CollectorType:
        """Get collector type."""
        return self._collector_type
    
    @property
    def data_types(self) -> List[DataType]:
        """Get supported data types."""
        return self._data_types
    
    @property
    def status(self) -> CollectorStatus:
        """Get current status."""
        return self._status
    
    async def initialize(self) -> bool:
        """Initialize the collector."""
        try:
            self._status = CollectorStatus.STARTING
            logger.info(f"🔧 Initializing {self.name}...")
            
            # Connect to MongoDB
            if not await self._mongo.connect():
                logger.error(f"❌ Failed to connect to MongoDB for {self.name}")
                return False
            
            # Initialize collector-specific resources
            success = await self._initialize_resources()
            
            if success:
                self._status = CollectorStatus.STOPPED
                logger.info(f"✅ Initialized {self.name}")
            else:
                self._status = CollectorStatus.ERROR
                logger.error(f"❌ Failed to initialize {self.name}")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error initializing {self.name}: {e}")
            self._status = CollectorStatus.ERROR
            return False
    
    async def start(self, duration_seconds: int = 0, **kwargs) -> None:
        """Start data collection."""
        try:
            self._status = CollectorStatus.STARTING
            self._stats["start_time"] = datetime.now()
            self._stats["last_activity"] = datetime.now()
            self._is_healthy = True
            
            logger.info(f"🚀 Starting {self.name}...")
            
            # Start collector-specific collection
            await self._start_collection(duration_seconds, **kwargs)
            
            self._status = CollectorStatus.RUNNING
            logger.info(f"✅ Started {self.name}")
            
        except Exception as e:
            logger.error(f"❌ Error starting {self.name}: {e}")
            self._status = CollectorStatus.ERROR
            self._stats["errors"] += 1
            self._stats["consecutive_errors"] += 1
    
    async def stop(self) -> None:
        """Stop data collection."""
        try:
            self._status = CollectorStatus.STOPPING
            logger.info(f"🛑 Stopping {self.name}...")
            
            # Stop collector-specific collection
            await self._stop_collection()
            
            self._status = CollectorStatus.STOPPED
            logger.info(f"✅ Stopped {self.name}")
            
        except Exception as e:
            logger.error(f"❌ Error stopping {self.name}: {e}")
            self._status = CollectorStatus.ERROR
    
    async def cleanup(self) -> None:
        """Cleanup resources."""
        try:
            logger.info(f"🧹 Cleaning up {self.name}...")
            
            # Stop if still running
            if self._status == CollectorStatus.RUNNING:
                await self.stop()
            
            # Cleanup collector-specific resources
            await self._cleanup_resources()
            
            # Disconnect from MongoDB
            await self._mongo.disconnect()
            
            logger.info(f"✅ Cleaned up {self.name}")
            
        except Exception as e:
            logger.error(f"❌ Error cleaning up {self.name}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        stats = self._stats.copy()
        
        if self._stats["start_time"]:
            uptime = (datetime.now() - self._stats["start_time"]).total_seconds()
            stats["uptime_seconds"] = uptime
            stats["messages_per_second"] = (
                self._stats["messages_stored"] / uptime if uptime > 0 else 0
            )
            stats["success_rate"] = (
                self._stats["messages_stored"] / self._stats["messages_received"] 
                if self._stats["messages_received"] > 0 else 0
            )
        
        stats["status"] = self._status.value
        stats["is_healthy"] = self.is_healthy()
        stats["last_health_check"] = self._last_health_check
        
        return stats
    
    def is_healthy(self) -> bool:
        """Check if collector is healthy."""
        now = datetime.now()
        
        # Check if health check is recent
        if (self._last_health_check and 
            (now - self._last_health_check).total_seconds() > self._health_check_interval * 2):
            self._is_healthy = False
        
        # Check consecutive errors
        if self._stats["consecutive_errors"] > 10:
            self._is_healthy = False
        
        # Check if last activity is recent (for realtime collectors)
        if (self._collector_type == CollectorType.REALTIME and 
            self._stats["last_activity"] and
            (now - self._stats["last_activity"]).total_seconds() > 300):  # 5 minutes
            self._is_healthy = False
        
        return self._is_healthy
    
    def record_message(self, stored: bool = True) -> None:
        """Record a message."""
        self._stats["messages_received"] += 1
        if stored:
            self._stats["messages_stored"] += 1
            self._stats["consecutive_errors"] = 0
        else:
            self._stats["errors"] += 1
            self._stats["consecutive_errors"] += 1
        
        self._stats["last_activity"] = datetime.now()
        self._last_health_check = datetime.now()
    
    def add_error_handler(self, handler: Callable) -> None:
        """Add an error handler."""
        self._error_handlers.append(handler)
    
    async def handle_error(self, error: Exception, context: Dict[str, Any] = None) -> bool:
        """Handle an error."""
        self._stats["errors"] += 1
        self._stats["consecutive_errors"] += 1
        
        logger.error(f"❌ Error in {self.name}: {error}")
        
        # Call registered error handlers
        for handler in self._error_handlers:
            try:
                if await handler(error, context or {}):
                    return True
            except Exception as e:
                logger.error(f"❌ Error in error handler: {e}")
        
        return False
    
    # Abstract methods to be implemented by subclasses
    async def _initialize_resources(self) -> bool:
        """Initialize collector-specific resources."""
        return True
    
    async def _start_collection(self, duration_seconds: int, **kwargs) -> None:
        """Start collector-specific data collection."""
        raise NotImplementedError
    
    async def _stop_collection(self) -> None:
        """Stop collector-specific data collection."""
        pass
    
    async def _cleanup_resources(self) -> None:
        """Cleanup collector-specific resources."""
        pass
