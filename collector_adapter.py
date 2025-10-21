#!/usr/bin/env python3
"""Adapter to make existing collectors compatible with the new interface."""

import asyncio
from typing import List, Dict, Any, Optional
from loguru import logger

from interfaces import IDataCollector, CollectorType, DataType, CollectorStatus
from base_collector import BaseCollector


class CollectorAdapter(BaseCollector):
    """Adapter to make existing collectors compatible with the new interface."""
    
    def __init__(self, existing_collector, exchange: str, collector_type: CollectorType, 
                 data_types: List[DataType], symbols: List[str] = None):
        super().__init__(exchange, collector_type, data_types, symbols)
        self.existing_collector = existing_collector
        self._original_methods = {}
        self._wrap_existing_methods()
    
    def _wrap_existing_methods(self):
        """Wrap existing collector methods."""
        # Store original methods
        if hasattr(self.existing_collector, 'collect'):
            self._original_methods['collect'] = self.existing_collector.collect
        if hasattr(self.existing_collector, 'collect_data'):
            self._original_methods['collect_data'] = self.existing_collector.collect_data
        
        # Wrap collect methods
        if 'collect' in self._original_methods:
            self.existing_collector.collect = self._wrap_collect_method(
                self._original_methods['collect']
            )
        if 'collect_data' in self._original_methods:
            self.existing_collector.collect_data = self._wrap_collect_method(
                self._original_methods['collect_data']
            )
    
    def _wrap_collect_method(self, original_method):
        """Wrap the collect method to track stats."""
        async def wrapped_method(*args, **kwargs):
            try:
                self._status = CollectorStatus.RUNNING
                self._stats["start_time"] = self._stats["start_time"] or asyncio.get_event_loop().time()
                
                # Call original method
                await original_method(*args, **kwargs)
                
                self._status = CollectorStatus.COMPLETED
                self.record_message(stored=True)
                
            except Exception as e:
                self._status = CollectorStatus.ERROR
                self.record_message(stored=False)
                await self.handle_error(e, {"collector": self.name})
                raise
        
        return wrapped_method
    
    async def _initialize_resources(self) -> bool:
        """Initialize existing collector resources."""
        try:
            # Try to call initialize if it exists
            if hasattr(self.existing_collector, 'initialize'):
                return await self.existing_collector.initialize()
            
            # Try to connect to MongoDB if it exists
            if hasattr(self.existing_collector, 'mongo') and hasattr(self.existing_collector.mongo, 'connect'):
                return await self.existing_collector.mongo.connect()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Error initializing {self.name}: {e}")
            return False
    
    async def _start_collection(self, duration_seconds: int, **kwargs) -> None:
        """Start collection using existing collector."""
        try:
            # Determine which method to call
            if hasattr(self.existing_collector, 'collect_data'):
                await self.existing_collector.collect_data(duration_seconds=duration_seconds, **kwargs)
            elif hasattr(self.existing_collector, 'collect'):
                if 'poll_interval' in kwargs and 'poll_interval' in self.existing_collector.collect.__code__.co_varnames:
                    await self.existing_collector.collect(duration_seconds=duration_seconds, **kwargs)
                else:
                    await self.existing_collector.collect(duration_seconds=duration_seconds)
            else:
                raise AttributeError("No collect method found")
                
        except Exception as e:
            logger.error(f"❌ Error in collection for {self.name}: {e}")
            raise
    
    async def _stop_collection(self) -> None:
        """Stop collection."""
        try:
            # Try to call stop if it exists
            if hasattr(self.existing_collector, 'stop'):
                await self.existing_collector.stop()
            
            # Try to disconnect if it exists
            if hasattr(self.existing_collector, 'mongo') and hasattr(self.existing_collector.mongo, 'disconnect'):
                await self.existing_collector.mongo.disconnect()
                
        except Exception as e:
            logger.error(f"❌ Error stopping {self.name}: {e}")
    
    async def _cleanup_resources(self) -> None:
        """Cleanup existing collector resources."""
        try:
            # Try to call cleanup if it exists
            if hasattr(self.existing_collector, 'cleanup'):
                await self.existing_collector.cleanup()
            
            # Try to disconnect if it exists
            if hasattr(self.existing_collector, 'mongo') and hasattr(self.existing_collector.mongo, 'disconnect'):
                await self.existing_collector.mongo.disconnect()
                
        except Exception as e:
            logger.error(f"❌ Error cleaning up {self.name}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collector statistics."""
        stats = super().get_stats()
        
        # Try to get stats from existing collector
        try:
            if hasattr(self.existing_collector, 'stats'):
                existing_stats = self.existing_collector.stats
                if isinstance(existing_stats, dict):
                    # Map existing stats to our format
                    stats.update({
                        "messages_stored": existing_stats.get("stored", 0),
                        "errors": existing_stats.get("errors", 0),
                        "original_stats": existing_stats
                    })
        except Exception as e:
            logger.debug(f"Could not get stats from existing collector: {e}")
        
        return stats


def create_collector_adapter(existing_collector, exchange: str, collector_type: CollectorType, 
                           data_types: List[DataType], symbols: List[str] = None) -> CollectorAdapter:
    """Create an adapter for an existing collector."""
    return CollectorAdapter(existing_collector, exchange, collector_type, data_types, symbols)
