#!/usr/bin/env python3
"""Historical data collection orchestrator for all exchanges."""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger

from binance_historical_collector import BinanceHistoricalCollector
from bybit_historical_collector import BybitHistoricalCollector
from kraken_historical_collector import KrakenHistoricalCollector
from okx_historical_collector import OKXHistoricalCollector
from gate_historical_collector import GateHistoricalCollector

class HistoricalDataOrchestrator:
    """Orchestrates historical data collection across all exchanges."""
    
    def __init__(self, duration_hours: int = 24, timeframe: str = "1h", symbols: List[str] = None):
        self.duration_hours = duration_hours
        self.timeframe = timeframe
        self.symbols = symbols or ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "DOTUSDT"]
        self.collectors = {}
        self.tasks = []
        self.running = False
        
        self._initialize_collectors()
        self._setup_signal_handlers()
    
    def _initialize_collectors(self):
        """Initialize all historical data collectors."""
        logger.info("🔧 Initializing historical data collectors...")
        
        # Convert symbols to exchange-specific formats
        binance_symbols = self.symbols
        bybit_symbols = self.symbols
        kraken_symbols = [self._convert_to_kraken_symbol(s) for s in self.symbols]
        okx_symbols = [self._convert_to_okx_symbol(s) for s in self.symbols]
        gate_symbols = [self._convert_to_gate_symbol(s) for s in self.symbols]
        
        self.collectors = {
            "binance": BinanceHistoricalCollector(binance_symbols),
            "bybit": BybitHistoricalCollector(bybit_symbols),
            "kraken": KrakenHistoricalCollector(kraken_symbols),
            "okx": OKXHistoricalCollector(okx_symbols),
            "gate": GateHistoricalCollector(gate_symbols)
        }
        
        logger.info(f"✅ Initialized {len(self.collectors)} historical collectors")
    
    def _convert_to_kraken_symbol(self, symbol: str) -> str:
        """Convert standard symbol to Kraken format."""
        symbol_map = {
            "BTCUSDT": "XXBTZUSD",
            "ETHUSDT": "XETHZUSD", 
            "ADAUSDT": "ADAUSD",
            "SOLUSDT": "SOLUSD",
            "DOTUSDT": "DOTUSD"
        }
        return symbol_map.get(symbol, symbol)
    
    def _convert_to_okx_symbol(self, symbol: str) -> str:
        """Convert standard symbol to OKX format."""
        return symbol.replace("USDT", "-USDT")
    
    def _convert_to_gate_symbol(self, symbol: str) -> str:
        """Convert standard symbol to Gate.io format."""
        return symbol.replace("USDT", "_USDT")
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start_collection(self):
        """Start historical data collection for all exchanges."""
        logger.info("🚀 Starting historical data collection...")
        logger.info(f"⏱️  Duration: {self.duration_hours} hours")
        logger.info(f"📊 Timeframe: {self.timeframe}")
        logger.info(f"💰 Symbols: {', '.join(self.symbols)}")
        
        self.running = True
        start_time = datetime.now()
        
        try:
            # Start all collectors concurrently
            await self._start_all_collectors()
            
            # Wait for completion or interruption
            await self._monitor_collection()
            
        except Exception as e:
            logger.error(f"❌ Error in historical data collection: {e}")
        finally:
            await self._cleanup()
    
    async def _start_all_collectors(self):
        """Start all historical data collectors as concurrent tasks."""
        logger.info("📡 Starting all historical collectors...")
        
        for exchange, collector in self.collectors.items():
            # Start OHLCV data collection
            ohlcv_task = asyncio.create_task(
                collector.collect_historical_data(
                    duration_hours=self.duration_hours,
                    timeframe=self.timeframe
                ),
                name=f"historical_ohlcv_{exchange}"
            )
            self.tasks.append(ohlcv_task)
            
            # Start trades data collection
            trades_task = asyncio.create_task(
                collector.collect_historical_trades(
                    duration_hours=min(self.duration_hours, 24)  # Limit trades to 24h max
                ),
                name=f"historical_trades_{exchange}"
            )
            self.tasks.append(trades_task)
            
            logger.info(f"✅ Started historical collection for {exchange}")
        
        logger.info(f"🚀 Started {len(self.tasks)} historical collection tasks")
    
    async def _monitor_collection(self):
        """Monitor collection progress and handle graceful shutdown."""
        logger.info("👀 Monitoring historical data collection...")
        
        while self.running:
            # Check if all tasks are done
            if all(task.done() for task in self.tasks):
                logger.info("✅ All historical collection tasks completed")
                break
            
            # Check for failed tasks
            failed_tasks = []
            for task in self.tasks:
                if task.done() and task.exception():
                    failed_tasks.append(task)
                    logger.error(f"❌ Task {task.get_name()} failed: {task.exception()}")
            
            if failed_tasks:
                logger.warning(f"⚠️  {len(failed_tasks)} tasks failed, continuing with remaining tasks...")
            
            await asyncio.sleep(5)  # Check every 5 seconds
        
        # Wait for all tasks to complete
        if self.tasks:
            logger.info("⏳ Waiting for all tasks to complete...")
            await asyncio.gather(*self.tasks, return_exceptions=True)
    
    async def _cleanup(self):
        """Cleanup and disconnect all collectors."""
        logger.info("🧹 Cleaning up historical collectors...")
        
        # Disconnect all collectors
        for exchange, collector in self.collectors.items():
            try:
                await collector.disconnect()
                logger.info(f"✅ Disconnected {exchange} collector")
            except Exception as e:
                logger.error(f"❌ Error disconnecting {exchange}: {e}")
        
        # Cancel any remaining tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()
        
        logger.info("✅ Historical data collection cleanup completed")
    
    def get_collection_summary(self) -> Dict[str, any]:
        """Get summary of collection status."""
        completed_tasks = sum(1 for task in self.tasks if task.done() and not task.exception())
        failed_tasks = sum(1 for task in self.tasks if task.done() and task.exception())
        running_tasks = sum(1 for task in self.tasks if not task.done())
        
        return {
            'total_tasks': len(self.tasks),
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'running_tasks': running_tasks,
            'exchanges': list(self.collectors.keys()),
            'duration_hours': self.duration_hours,
            'timeframe': self.timeframe,
            'symbols': self.symbols
        }

async def main():
    """Main entry point for historical data collection."""
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    )
    
    # Parse command line arguments
    duration_hours = 24
    timeframe = "1h"
    symbols = ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "DOTUSDT"]
    
    if len(sys.argv) > 1:
        try:
            duration_hours = int(sys.argv[1])
        except ValueError:
            logger.error("Invalid duration. Using default 24 hours.")
    
    if len(sys.argv) > 2:
        timeframe = sys.argv[2]
        if timeframe not in ["1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w"]:
            logger.error("Invalid timeframe. Using default 1h.")
            timeframe = "1h"
    
    if len(sys.argv) > 3:
        symbols = sys.argv[3].split(",")
    
    orchestrator = HistoricalDataOrchestrator(
        duration_hours=duration_hours,
        timeframe=timeframe,
        symbols=symbols
    )
    
    try:
        await orchestrator.start_collection()
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        summary = orchestrator.get_collection_summary()
        logger.info("📊 Historical Collection Summary:")
        logger.info(f"  Total tasks: {summary['total_tasks']}")
        logger.info(f"  Completed: {summary['completed_tasks']}")
        logger.info(f"  Failed: {summary['failed_tasks']}")
        logger.info(f"  Running: {summary['running_tasks']}")
        logger.info(f"  Exchanges: {', '.join(summary['exchanges'])}")
        logger.info(f"  Duration: {summary['duration_hours']} hours")
        logger.info(f"  Timeframe: {summary['timeframe']}")
        logger.info("✅ Historical data collection completed!")

if __name__ == "__main__":
    asyncio.run(main())
