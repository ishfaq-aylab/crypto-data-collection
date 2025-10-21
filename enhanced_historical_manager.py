#!/usr/bin/env python3
"""
Enhanced Historical Data Collection Manager
===========================================

This script provides real-time progress monitoring based on actual database data:
- Real-time progress from database
- Data quality analysis
- Collection statistics
- Resume capabilities
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List, Tuple
from loguru import logger
from collections import defaultdict

from four_year_historical_collector import FourYearHistoricalCollector
from simple_mongodb_collector import SimpleMongoDBCollector
from config import Config

class EnhancedHistoricalCollectionManager:
    """Enhanced manager with real-time database progress monitoring."""
    
    def __init__(self):
        self.config_file = "collection_config.json"
        self.progress_file = "collection_progress.json"
        self.config = self.load_config()
        self.mongo = SimpleMongoDBCollector()
        
    def load_config(self) -> Dict[str, Any]:
        """Load collection configuration."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        return {}
    
    async def connect_mongo(self):
        """Connect to MongoDB."""
        if not await self.mongo.connect():
            logger.error("Failed to connect to MongoDB")
            return False
        return True
    
    async def get_database_progress(self) -> Dict[str, Any]:
        """Get real-time progress from database."""
        if not await self.connect_mongo():
            return {}
        
        try:
            # Get historical data collection
            historical_data = self.mongo.database["historical_data"]
            
            # Get all unique combinations
            pipeline = [
                {
                    "$group": {
                        "_id": {
                            "exchange": "$exchange",
                            "symbol": "$symbol",
                            "timeframe": "$timeframe",
                            "year": {"$year": "$timestamp"},
                            "month": {"$month": "$timestamp"}
                        },
                        "count": {"$sum": 1},
                        "min_timestamp": {"$min": "$timestamp"},
                        "max_timestamp": {"$max": "$timestamp"}
                    }
                },
                {
                    "$sort": {
                        "_id.exchange": 1,
                        "_id.symbol": 1,
                        "_id.timeframe": 1,
                        "_id.year": 1,
                        "_id.month": 1
                    }
                }
            ]
            
            results = list(historical_data.aggregate(pipeline))
            
            # Process results
            progress = {
                "total_combinations": len(results),
                "exchanges": {},
                "symbols": {},
                "timeframes": {},
                "monthly_data": {},
                "summary": {
                    "total_records": 0,
                    "date_range": {"start": None, "end": None},
                    "exchanges_count": 0,
                    "symbols_count": 0,
                    "timeframes_count": 0
                }
            }
            
            min_date = None
            max_date = None
            
            for result in results:
                exchange = result["_id"]["exchange"]
                symbol = result["_id"]["symbol"]
                timeframe = result["_id"]["timeframe"]
                year = result["_id"]["year"]
                month = result["_id"]["month"]
                count = result["count"]
                min_ts = result["min_timestamp"]
                max_ts = result["max_timestamp"]
                
                # Update counters
                progress["exchanges"][exchange] = progress["exchanges"].get(exchange, 0) + 1
                progress["symbols"][symbol] = progress["symbols"].get(symbol, 0) + 1
                progress["timeframes"][timeframe] = progress["timeframes"].get(timeframe, 0) + 1
                
                # Monthly data
                month_key = f"{exchange}_{symbol}_{timeframe}_{year}_{month:02d}"
                progress["monthly_data"][month_key] = {
                    "exchange": exchange,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "year": year,
                    "month": month,
                    "count": count,
                    "min_timestamp": min_ts,
                    "max_timestamp": max_ts
                }
                
                # Update summary
                progress["summary"]["total_records"] += count
                
                if min_date is None or min_ts < min_date:
                    min_date = min_ts
                if max_date is None or max_ts > max_date:
                    max_date = max_ts
            
            progress["summary"]["date_range"]["start"] = min_date
            progress["summary"]["date_range"]["end"] = max_date
            progress["summary"]["exchanges_count"] = len(progress["exchanges"])
            progress["summary"]["symbols_count"] = len(progress["symbols"])
            progress["summary"]["timeframes_count"] = len(progress["timeframes"])
            
            return progress
            
        except Exception as e:
            logger.error(f"Error getting database progress: {e}")
            return {}
        finally:
            await self.mongo.disconnect()
    
    async def show_realtime_progress(self):
        """Show real-time progress from database."""
        logger.info("🔍 Checking real-time progress from database...")
        
        progress = await self.get_database_progress()
        if not progress:
            logger.error("❌ Could not retrieve progress from database")
            return
        
        summary = progress["summary"]
        
        logger.info("📊 Real-time Collection Progress:")
        logger.info("=" * 60)
        logger.info(f"📈 Total Records: {summary['total_records']:,}")
        logger.info(f"📅 Date Range: {summary['date_range']['start']} to {summary['date_range']['end']}")
        logger.info(f"🏦 Exchanges: {summary['exchanges_count']} ({', '.join(progress['exchanges'].keys())})")
        logger.info(f"💰 Symbols: {summary['symbols_count']} ({', '.join(progress['symbols'].keys())})")
        logger.info(f"⏰ Timeframes: {summary['timeframes_count']} ({', '.join(progress['timeframes'].keys())})")
        logger.info(f"📊 Unique Combinations: {progress['total_combinations']}")
        
        # Show exchange breakdown
        logger.info("\n🏦 Exchange Breakdown:")
        for exchange, count in progress["exchanges"].items():
            logger.info(f"  {exchange}: {count} month-symbol-timeframe combinations")
        
        # Show symbol breakdown
        logger.info("\n💰 Symbol Breakdown:")
        for symbol, count in progress["symbols"].items():
            logger.info(f"  {symbol}: {count} month-exchange-timeframe combinations")
        
        # Show timeframe breakdown
        logger.info("\n⏰ Timeframe Breakdown:")
        for timeframe, count in progress["timeframes"].items():
            logger.info(f"  {timeframe}: {count} month-exchange-symbol combinations")
        
        # Show recent data
        logger.info("\n📅 Recent Data (Last 10 combinations):")
        recent_items = sorted(progress["monthly_data"].items(), 
                            key=lambda x: x[1]["max_timestamp"], reverse=True)[:10]
        
        for month_key, data in recent_items:
            logger.info(f"  {data['exchange']} {data['symbol']} {data['timeframe']} "
                       f"{data['year']}-{data['month']:02d}: {data['count']:,} records")
    
    async def show_data_quality(self):
        """Show data quality analysis."""
        logger.info("🔍 Analyzing data quality...")
        
        if not await self.connect_mongo():
            return
        
        try:
            historical_data = self.mongo.database["historical_data"]
            
            # Get quality metrics
            pipeline = [
                {
                    "$group": {
                        "_id": None,
                        "total_docs": {"$sum": 1},
                        "unique_exchanges": {"$addToSet": "$exchange"},
                        "unique_symbols": {"$addToSet": "$symbol"},
                        "unique_timeframes": {"$addToSet": "$timeframe"},
                        "min_timestamp": {"$min": "$timestamp"},
                        "max_timestamp": {"$max": "$timestamp"},
                        "avg_volume": {"$avg": "$volume"},
                        "avg_price": {"$avg": "$close"}
                    }
                }
            ]
            
            result = list(historical_data.aggregate(pipeline))
            if not result:
                logger.warning("No historical data found")
                return
            
            data = result[0]
            
            logger.info("📊 Data Quality Report:")
            logger.info("=" * 50)
            logger.info(f"📈 Total Documents: {data['total_docs']:,}")
            logger.info(f"🏦 Exchanges: {len(data['unique_exchanges'])} ({', '.join(data['unique_exchanges'])})")
            logger.info(f"💰 Symbols: {len(data['unique_symbols'])} ({', '.join(data['unique_symbols'])})")
            logger.info(f"⏰ Timeframes: {len(data['unique_timeframes'])} ({', '.join(data['unique_timeframes'])})")
            logger.info(f"📅 Date Range: {data['min_timestamp']} to {data['max_timestamp']}")
            logger.info(f"📊 Average Volume: {data['avg_volume']:,.2f}")
            logger.info(f"💰 Average Price: ${data['avg_price']:,.2f}")
            
            # Check for data gaps
            logger.info("\n🔍 Data Quality Checks:")
            
            # Check for missing data
            missing_data = []
            for exchange in data['unique_exchanges']:
                for symbol in data['unique_symbols']:
                    for timeframe in data['unique_timeframes']:
                        count = historical_data.count_documents({
                            "exchange": exchange,
                            "symbol": symbol,
                            "timeframe": timeframe
                        })
                        if count == 0:
                            missing_data.append(f"{exchange}_{symbol}_{timeframe}")
            
            if missing_data:
                logger.warning(f"⚠️  Missing data combinations: {len(missing_data)}")
                for missing in missing_data[:5]:  # Show first 5
                    logger.warning(f"    {missing}")
                if len(missing_data) > 5:
                    logger.warning(f"    ... and {len(missing_data) - 5} more")
            else:
                logger.info("✅ No missing data combinations found")
            
            # Check for recent data
            recent_cutoff = datetime.now() - timedelta(days=1)
            recent_count = historical_data.count_documents({
                "timestamp": {"$gte": recent_cutoff}
            })
            
            if recent_count > 0:
                logger.info(f"✅ Recent data (last 24h): {recent_count:,} records")
            else:
                logger.warning("⚠️  No recent data found (last 24h)")
            
        except Exception as e:
            logger.error(f"Error analyzing data quality: {e}")
        finally:
            await self.mongo.disconnect()
    
    async def show_collection_statistics(self):
        """Show detailed collection statistics."""
        logger.info("📊 Generating collection statistics...")
        
        if not await self.connect_mongo():
            return
        
        try:
            historical_data = self.mongo.database["historical_data"]
            
            # Get monthly statistics
            pipeline = [
                {
                    "$group": {
                        "_id": {
                            "exchange": "$exchange",
                            "year": {"$year": "$timestamp"},
                            "month": {"$month": "$timestamp"}
                        },
                        "records": {"$sum": 1},
                        "symbols": {"$addToSet": "$symbol"},
                        "timeframes": {"$addToSet": "$timeframe"},
                        "min_date": {"$min": "$timestamp"},
                        "max_date": {"$max": "$timestamp"}
                    }
                },
                {
                    "$sort": {
                        "_id.exchange": 1,
                        "_id.year": 1,
                        "_id.month": 1
                    }
                }
            ]
            
            results = list(historical_data.aggregate(pipeline))
            
            logger.info("📅 Monthly Collection Statistics:")
            logger.info("=" * 70)
            
            current_exchange = None
            for result in results:
                exchange = result["_id"]["exchange"]
                year = result["_id"]["year"]
                month = result["_id"]["month"]
                records = result["records"]
                symbols = len(result["symbols"])
                timeframes = len(result["timeframes"])
                min_date = result["min_date"]
                max_date = result["max_date"]
                
                if exchange != current_exchange:
                    logger.info(f"\n🏦 {exchange.upper()}:")
                    current_exchange = exchange
                
                logger.info(f"  {year}-{month:02d}: {records:,} records, "
                          f"{symbols} symbols, {timeframes} timeframes")
                logger.info(f"    Date range: {min_date} to {max_date}")
            
        except Exception as e:
            logger.error(f"Error generating statistics: {e}")
        finally:
            await self.mongo.disconnect()
    
    async def show_help(self):
        """Show help information."""
        print("Enhanced Historical Data Collection Manager")
        print("=" * 50)
        print()
        print("Usage: python enhanced_historical_manager.py <command>")
        print()
        print("Commands:")
        print("  progress     - Show real-time progress from database")
        print("  quality      - Analyze data quality")
        print("  stats        - Show detailed collection statistics")
        print("  help         - Show this help message")
        print()
        print("Examples:")
        print("  python enhanced_historical_manager.py progress")
        print("  python enhanced_historical_manager.py quality")
        print("  python enhanced_historical_manager.py stats")

async def main():
    """Main function."""
    if len(sys.argv) < 2:
        await EnhancedHistoricalCollectionManager().show_help()
        return
    
    command = sys.argv[1].lower()
    manager = EnhancedHistoricalCollectionManager()
    
    if command == "progress":
        await manager.show_realtime_progress()
    elif command == "quality":
        await manager.show_data_quality()
    elif command == "stats":
        await manager.show_collection_statistics()
    elif command == "help":
        await manager.show_help()
    else:
        print(f"Unknown command: {command}")
        await manager.show_help()

if __name__ == "__main__":
    asyncio.run(main())
