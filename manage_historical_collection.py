#!/usr/bin/env python3
"""
Historical Data Collection Manager
==================================

This script provides management capabilities for the 4-year historical data collection:
- Start/stop collection
- Monitor progress
- Resume interrupted collection
- Check data quality
- Generate reports
"""

import asyncio
import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from loguru import logger

from four_year_historical_collector import FourYearHistoricalCollector
from simple_mongodb_collector import SimpleMongoDBCollector

class HistoricalCollectionManager:
    """Manages the 4-year historical data collection process."""
    
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
    
    def save_config(self):
        """Save collection configuration."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    async def start_collection(self, dry_run: bool = False):
        """Start the historical data collection."""
        logger.info("🚀 Starting historical data collection")
        
        if dry_run:
            logger.info("🔍 DRY RUN MODE - No data will be collected")
            await self.show_collection_plan()
            return
        
        collector = FourYearHistoricalCollector()
        await collector.run_collection()
    
    async def show_collection_plan(self):
        """Show the collection plan without executing."""
        logger.info("📋 Collection Plan:")
        
        exchanges = self.config.get("exchanges", {})
        enabled_exchanges = [name for name, config in exchanges.items() if config.get("enabled", False)]
        
        logger.info(f"📊 Exchanges: {', '.join(enabled_exchanges)}")
        
        total_requests = 0
        for exchange_name, exchange_config in exchanges.items():
            if not exchange_config.get("enabled", False):
                continue
                
            symbols = exchange_config.get("symbols", [])
            timeframes = exchange_config.get("timeframes", [])
            rate_limit = exchange_config.get("rate_limit", 60)
            
            # Calculate requests per exchange
            months = 48  # 4 years
            requests_per_symbol_timeframe = months * 2  # OHLCV + Trades
            exchange_requests = len(symbols) * len(timeframes) * requests_per_symbol_timeframe
            total_requests += exchange_requests
            
            logger.info(f"  {exchange_name}: {len(symbols)} symbols × {len(timeframes)} timeframes × {months} months = {exchange_requests} requests")
            logger.info(f"    Rate limit: {rate_limit} requests/minute")
        
        logger.info(f"📈 Total estimated requests: {total_requests}")
        
        # Estimate duration
        min_rate_limit = min(exchange_config.get("rate_limit", 60) for exchange_config in exchanges.values() if exchange_config.get("enabled", False))
        estimated_minutes = total_requests / min_rate_limit
        estimated_hours = estimated_minutes / 60
        
        logger.info(f"⏱️ Estimated duration: {estimated_hours:.1f} hours ({estimated_hours/24:.1f} days)")
    
    async def check_progress(self):
        """Check collection progress from both file and database."""
        # Check file-based progress
        file_progress = None
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    file_progress = json.load(f)
            except Exception as e:
                logger.warning(f"Error reading progress file: {e}")
        
        # Check database progress
        db_progress = await self.get_database_progress()
        
        logger.info("📊 Collection Progress:")
        logger.info("=" * 50)
        
        if file_progress:
            logger.info(f"📄 File Progress - Last updated: {file_progress.get('last_updated', 'Unknown')}")
            completed_months = file_progress.get('completed_months', [])
            logger.info(f"📄 File Progress - Completed months: {len(completed_months)}")
            
            # Show breakdown by exchange
            exchanges = {}
            for month_key in completed_months:
                parts = month_key.split("_")
                if len(parts) >= 2:
                    exchange = parts[0]
                    exchanges[exchange] = exchanges.get(exchange, 0) + 1
            
            for exchange, count in exchanges.items():
                logger.info(f"    {exchange}: {count} months")
        
        if db_progress:
            summary = db_progress["summary"]
            logger.info(f"\n💾 Database Progress - Total Records: {summary['total_records']:,}")
            logger.info(f"💾 Database Progress - Exchanges: {summary['exchanges_count']} ({', '.join(db_progress['exchanges'].keys())})")
            logger.info(f"💾 Database Progress - Symbols: {summary['symbols_count']} ({', '.join(db_progress['symbols'].keys())})")
            logger.info(f"💾 Database Progress - Timeframes: {summary['timeframes_count']} ({', '.join(db_progress['timeframes'].keys())})")
            logger.info(f"💾 Database Progress - Unique Combinations: {db_progress['total_combinations']}")
            
            # Show recent data
            recent_items = sorted(db_progress["monthly_data"].items(), 
                                key=lambda x: x[1]["max_timestamp"], reverse=True)[:5]
            
            logger.info(f"\n📅 Recent Data (Last 5 combinations):")
            for month_key, data in recent_items:
                logger.info(f"  {data['exchange']} {data['symbol']} {data['timeframe']} "
                           f"{data['year']}-{data['month']:02d}: {data['count']:,} records")
        
        if not file_progress and not db_progress:
            logger.info("❌ No progress found. Collection not started yet.")
    
    async def get_database_progress(self) -> Dict[str, Any]:
        """Get real-time progress from database."""
        if not await self.mongo.connect():
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
    
    async def check_data_quality(self):
        """Check the quality of collected data."""
        logger.info("🔍 Checking data quality...")
        
        await self.mongo.connect()
        
        try:
            # Get collection summary
            summary = await self.mongo.get_collection_summary()
            
            logger.info("📊 Data Quality Report:")
            
            for collection_name, stats in summary.items():
                logger.info(f"  {collection_name}:")
                logger.info(f"    Total documents: {stats['total_documents']}")
                logger.info(f"    Unique symbols: {stats['unique_symbols']}")
                logger.info(f"    Unique exchanges: {stats['unique_exchanges']}")
                logger.info(f"    Latest timestamp: {stats['latest_timestamp']}")
                logger.info(f"    Oldest timestamp: {stats['oldest_timestamp']}")
                
                # Check for data gaps
                if stats['latest_timestamp'] and stats['oldest_timestamp']:
                    latest = datetime.fromisoformat(stats['latest_timestamp'].replace('Z', '+00:00'))
                    oldest = datetime.fromisoformat(stats['oldest_timestamp'].replace('Z', '+00:00'))
                    duration = latest - oldest
                    logger.info(f"    Data span: {duration.days} days")
            
        except Exception as e:
            logger.error(f"Error checking data quality: {e}")
        finally:
            await self.mongo.disconnect()
    
    async def generate_report(self):
        """Generate a comprehensive collection report."""
        logger.info("📋 Generating collection report...")
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "collection_status": "Unknown",
            "data_summary": {},
            "exchanges": {},
            "recommendations": []
        }
        
        # Check progress
        if os.path.exists(self.progress_file):
            with open(self.progress_file, 'r') as f:
                progress = json.load(f)
            report["collection_status"] = "In Progress" if progress.get("last_updated") else "Completed"
            report["progress"] = progress
        
        # Check data quality
        await self.mongo.connect()
        try:
            summary = await self.mongo.get_collection_summary()
            report["data_summary"] = summary
            
            # Analyze each exchange
            for collection_name, stats in summary.items():
                if stats['total_documents'] > 0:
                    report["exchanges"][collection_name] = {
                        "status": "Active",
                        "documents": stats['total_documents'],
                        "symbols": stats['unique_symbols'],
                        "latest_data": stats['latest_timestamp']
                    }
                else:
                    report["exchanges"][collection_name] = {
                        "status": "No Data",
                        "documents": 0
                    }
        
        except Exception as e:
            logger.error(f"Error generating report: {e}")
        finally:
            await self.mongo.disconnect()
        
        # Save report
        report_file = f"collection_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Convert datetime objects to strings for JSON serialization
        def convert_datetime(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: convert_datetime(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_datetime(item) for item in obj]
            return obj
        
        report_serializable = convert_datetime(report)
        
        with open(report_file, 'w') as f:
            json.dump(report_serializable, f, indent=2)
        
        logger.info(f"📄 Report saved to: {report_file}")
        
        # Print summary
        logger.info("📊 Report Summary:")
        logger.info(f"  Status: {report['collection_status']}")
        logger.info(f"  Exchanges with data: {len([e for e in report['exchanges'].values() if e['status'] == 'Active'])}")
        
        return report
    
    async def resume_collection(self):
        """Resume interrupted collection."""
        logger.info("🔄 Resuming collection from last checkpoint...")
        
        if not os.path.exists(self.progress_file):
            logger.error("❌ No progress file found. Cannot resume.")
            return
        
        # Start collection (it will automatically resume from progress file)
        await self.start_collection(dry_run=False)
    
    async def clean_old_data(self, days: int = 30):
        """Clean old data older than specified days."""
        logger.warning(f"🧹 Cleaning data older than {days} days...")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        logger.info(f"Cutoff date: {cutoff_date}")
        
        # This would need to be implemented in the MongoDB collector
        logger.warning("⚠️ Data cleaning not implemented yet. Please clean manually if needed.")
    
    def show_help(self):
        """Show help information."""
        print("""
Historical Data Collection Manager
=================================

Usage: python manage_historical_collection.py <command> [options]

Commands:
  start [--dry-run]     Start collection (use --dry-run to see plan without executing)
  progress              Check collection progress
  quality               Check data quality
  report                Generate comprehensive report
  resume                Resume interrupted collection
  clean <days>          Clean data older than specified days
  help                  Show this help message

Examples:
  python manage_historical_collection.py start --dry-run
  python manage_historical_collection.py start
  python manage_historical_collection.py progress
  python manage_historical_collection.py quality
  python manage_historical_collection.py report
  python manage_historical_collection.py resume
  python manage_historical_collection.py clean 30
        """)

async def main():
    """Main function."""
    if len(sys.argv) < 2:
        print("❌ No command specified. Use 'help' to see available commands.")
        return
    
    command = sys.argv[1]
    manager = HistoricalCollectionManager()
    
    if command == "start":
        dry_run = "--dry-run" in sys.argv
        await manager.start_collection(dry_run=dry_run)
    
    elif command == "progress":
        await manager.check_progress()
    
    elif command == "quality":
        await manager.check_data_quality()
    
    elif command == "report":
        await manager.generate_report()
    
    elif command == "resume":
        await manager.resume_collection()
    
    elif command == "clean":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        await manager.clean_old_data(days)
    
    elif command == "help":
        manager.show_help()
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'help' to see available commands.")

if __name__ == "__main__":
    asyncio.run(main())
