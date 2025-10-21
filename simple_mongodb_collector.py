#!/usr/bin/env python3
"""Simplified MongoDB data collector for all exchange data types."""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger
from pymongo import MongoClient
from config import Config
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, OperationFailure

from models import WebSocketMessage, DataType, MarketData, OrderBookData, TickPrice, VolumeLiquidity, FundingRate, OpenInterest

class SimpleMongoDBCollector:
    """Simplified MongoDB collector for all data types."""
    
    def __init__(self, mongodb_url: str = Config.MONGODB_URL, database_name: str = Config.MONGODB_DATABASE):
        """Initialize MongoDB collector."""
        self.mongodb_url = mongodb_url
        self.database_name = database_name
        self.client: Optional[MongoClient] = None
        self.database: Optional[Database] = None
        self.collections: Dict[DataType, Collection] = {}
        
        # Statistics
        self.stats = {
            'total_messages': 0,
            'successful_stores': 0,
            'failed_stores': 0,
            'start_time': datetime.now(),
            'by_exchange': {},
            'by_data_type': {}
        }
    
    async def connect(self):
        """Connect to MongoDB and setup collections."""
        try:
            self.client = MongoClient(self.mongodb_url, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            self.database = self.client[self.database_name]
            
            # Initialize collections for all data types
            self.collections = {
                DataType.MARKET_DATA: self.database["market_data"],
                DataType.ORDER_BOOK_DATA: self.database["order_book_data"],
                DataType.TICK_PRICES: self.database["tick_prices"],
                DataType.VOLUME_LIQUIDITY: self.database["volume_liquidity"],
                DataType.FUNDING_RATES: self.database["funding_rates"],
                DataType.OPEN_INTEREST: self.database["open_interest"],
                DataType.HISTORICAL_DATA: self.database["historical_data"],
                DataType.HISTORICAL_TRADES: self.database["tick_prices"]  # Store historical trades in tick_prices collection
            }
            
            # Create indexes for optimal performance
            await self._create_indexes()
            
            logger.info(f"Connected to MongoDB: {self.database_name}")
            return True
            
        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            return False
        except Exception as e:
            logger.error(f"MongoDB connection error: {e}")
            return False
    
    async def _create_indexes(self):
        """Create database indexes for optimal performance."""
        try:
            for data_type, collection in self.collections.items():
                # Compound index: exchange + symbol + timestamp
                collection.create_index([
                    ("exchange", 1),
                    ("symbol", 1),
                    ("timestamp", -1)
                ], name="exchange_symbol_timestamp")
                
                # Index for timestamp-based queries
                collection.create_index([("timestamp", -1)], name="timestamp")
                
                # Index for exchange-based queries
                collection.create_index([("exchange", 1), ("timestamp", -1)], name="exchange_timestamp")
                
                # Index for symbol-based queries
                collection.create_index([("symbol", 1), ("timestamp", -1)], name="symbol_timestamp")
                
                # TTL index for automatic cleanup (30 days)
                collection.create_index(
                    "timestamp",
                    expireAfterSeconds=30 * 24 * 60 * 60,
                    name="ttl_timestamp"
                )
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.error(f"Error creating indexes: {e}")
    
    async def store_message(self, message: WebSocketMessage) -> bool:
        """Store WebSocket message in MongoDB."""
        try:
            if not self.client:
                logger.error("MongoDB not connected")
                return False
            
            # Get the appropriate collection
            collection = self.collections.get(message.data_type)
            if collection is None:
                logger.error(f"No collection found for data type: {message.data_type}")
                return False
            
            # Create flattened document per DATA_DEFINITIONS.md
            base_doc = {
                "exchange": message.exchange,
                "symbol": message.data.symbol,
                "timestamp": message.timestamp,
                "data_type": message.data_type.value,  # Add required data_type field
                "created_at": datetime.now()  # Add required created_at field
            }

            # Map data_type to MD naming: ticker/orderbook/trade
            md_data_type = None
            if message.data_type == DataType.MARKET_DATA:
                md_data_type = "ticker"
                # Expected MarketData fields
                data = self._serialize_data(message.data)
                # Ensure numeric defaults for sizes
                bid_size = data.get("bid_size")
                ask_size = data.get("ask_size")
                try:
                    bid_size = float(bid_size) if bid_size is not None else 0.0
                except Exception:
                    bid_size = 0.0
                try:
                    ask_size = float(ask_size) if ask_size is not None else 0.0
                except Exception:
                    ask_size = 0.0
                base_doc.update({
                    "price": data.get("price"),
                    "volume": data.get("volume"),
                    "bid": data.get("bid"),
                    "ask": data.get("ask"),
                    "bid_size": bid_size,
                    "ask_size": ask_size,
                })
            elif message.data_type == DataType.ORDER_BOOK_DATA:
                md_data_type = "orderbook"
                data = self._serialize_data(message.data)
                base_doc.update({
                    # Optional level (may be absent in current models)
                    "level": data.get("level"),
                    "bids": data.get("bids"),
                    "asks": data.get("asks"),
                })
            elif message.data_type == DataType.TICK_PRICES:
                md_data_type = "trade"
                data = self._serialize_data(message.data)
                base_doc.update({
                    "price": data.get("price"),
                    "volume": data.get("volume"),
                    "side": data.get("side"),
                    # trade_id optional; include if present in models in future
                })
            elif message.data_type == DataType.VOLUME_LIQUIDITY:
                md_data_type = "volume_liquidity"
                data = self._serialize_data(message.data)
                base_doc.update({
                    "volume_24h": data.get("volume_24h"),
                    "liquidity": data.get("liquidity"),
                })
            elif message.data_type == DataType.FUNDING_RATES:
                md_data_type = "funding_rates"
                data = self._serialize_data(message.data)
                base_doc.update({
                    "funding_rate": data.get("funding_rate"),
                    "funding_time": data.get("funding_time"),
                    "next_funding_time": data.get("next_funding_time"),
                    "funding_interval": data.get("funding_interval"),
                    "predicted_funding_rate": data.get("predicted_funding_rate"),
                })
            elif message.data_type == DataType.OPEN_INTEREST:
                md_data_type = "open_interest"
                data = self._serialize_data(message.data)
                base_doc.update({
                    "open_interest": data.get("open_interest"),
                    "long_short_ratio": data.get("long_short_ratio"),
                    "long_interest": data.get("long_interest"),
                    "short_interest": data.get("short_interest"),
                    "interest_value": data.get("interest_value"),
                    "top_trader_long_short_ratio": data.get("top_trader_long_short_ratio"),
                    "retail_long_short_ratio": data.get("retail_long_short_ratio"),
                })
            elif message.data_type == DataType.HISTORICAL_DATA:
                md_data_type = "historical_data"
                data = self._serialize_data(message.data)
                base_doc.update({
                    "timeframe": data.get("timeframe"),
                    "open": data.get("open"),
                    "high": data.get("high"),
                    "low": data.get("low"),
                    "close": data.get("close"),
                    "volume": data.get("volume"),
                })
            elif message.data_type == DataType.HISTORICAL_TRADES:
                md_data_type = "trade"  # Historical trades should be stored in tick_prices collection
                data = self._serialize_data(message.data)
                base_doc.update({
                    "price": data.get("price"),
                    "volume": data.get("volume"),
                    "side": data.get("side"),
                    "trade_id": data.get("trade_id"),
                })

            # Do not store raw_message to align with DATA_DEFINITIONS.md
            document = base_doc
            
            # Insert document
            result = collection.insert_one(document)
            
            # Update statistics
            self.stats['total_messages'] += 1
            self.stats['successful_stores'] += 1
            
            # Update exchange stats
            if message.exchange not in self.stats['by_exchange']:
                self.stats['by_exchange'][message.exchange] = 0
            self.stats['by_exchange'][message.exchange] += 1
            
            # Update data type stats
            if message.data_type.value not in self.stats['by_data_type']:
                self.stats['by_data_type'][message.data_type.value] = 0
            self.stats['by_data_type'][message.data_type.value] += 1
            
            # Log every 100 messages
            if self.stats['total_messages'] % 100 == 0:
                logger.info(f"Stored {self.stats['total_messages']} messages to MongoDB")
            
            return True
            
        except Exception as e:
            logger.error(f"Error storing message: {e}")
            self.stats['failed_stores'] += 1
            return False
    
    def _serialize_data(self, data) -> Dict[str, Any]:
        """Serialize Pydantic model to dictionary."""
        try:
            if hasattr(data, 'model_dump'):
                return data.model_dump()
            elif hasattr(data, 'dict'):
                return data.dict()
            else:
                return str(data)
        except Exception as e:
            logger.error(f"Error serializing data: {e}")
            return {"error": str(e)}
    
    async def get_data_stats(self) -> Dict[str, Any]:
        """Get statistics about stored data."""
        try:
            stats = {
                "total_documents": 0,
                "by_collection": {},
                "by_exchange": {},
                "by_data_type": {},
                "recent_activity": {}
            }
            
            # Get counts for each collection
            for data_type, collection in self.collections.items():
                count = collection.count_documents({})
                stats["by_collection"][data_type.value] = count
                stats["total_documents"] += count
                
                # Get exchange breakdown for this collection
                pipeline = [
                    {"$group": {"_id": "$exchange", "count": {"$sum": 1}}},
                    {"$sort": {"count": -1}}
                ]
                exchange_breakdown = list(collection.aggregate(pipeline))
                stats["by_exchange"][data_type.value] = exchange_breakdown
            
            # Get recent activity (last hour)
            one_hour_ago = datetime.now() - timedelta(hours=1)
            for data_type, collection in self.collections.items():
                recent_count = collection.count_documents({"timestamp": {"$gte": one_hour_ago}})
                stats["recent_activity"][data_type.value] = recent_count
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting data stats: {e}")
            return {}
    
    async def get_collection_summary(self) -> Dict[str, Any]:
        """Get summary of all collections."""
        try:
            summary = {}
            
            for data_type, collection in self.collections.items():
                # Get basic stats
                total_count = collection.count_documents({})
                
                # Get latest document
                latest_doc = collection.find_one(sort=[("timestamp", -1)])
                
                # Get oldest document
                oldest_doc = collection.find_one(sort=[("timestamp", 1)])
                
                # Get unique symbols
                symbols = collection.distinct("symbol")
                
                # Get unique exchanges
                exchanges = collection.distinct("exchange")
                
                summary[data_type.value] = {
                    "total_documents": total_count,
                    "unique_symbols": len(symbols),
                    "unique_exchanges": len(exchanges),
                    "symbols": symbols[:10],  # First 10 symbols
                    "exchanges": exchanges,
                    "latest_timestamp": latest_doc["timestamp"] if latest_doc else None,
                    "oldest_timestamp": oldest_doc["timestamp"] if oldest_doc else None
                }
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting collection summary: {e}")
            return {}
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        uptime = (datetime.now() - self.stats['start_time']).total_seconds()
        return {
            **self.stats,
            'uptime_seconds': uptime,
            'messages_per_second': self.stats['total_messages'] / uptime if uptime > 0 else 0,
            'success_rate': self.stats['successful_stores'] / self.stats['total_messages'] if self.stats['total_messages'] > 0 else 0
        }

