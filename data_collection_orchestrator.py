#!/usr/bin/env python3
"""Simplified optimized orchestrator that works with existing collectors."""

import asyncio
import signal
import sys
from datetime import datetime
from typing import Dict, List, Optional, Any
from loguru import logger

from collector_factory import get_collector_factory
from monitoring_service import get_monitoring_service
from error_handler import get_error_handler
from collector_config import get_enabled_exchanges, get_enabled_data_types


class SimpleOptimizedOrchestrator:
    """Simplified optimized orchestrator that works with existing collectors."""
    
    def __init__(self, duration_seconds: int = 3600, poll_interval: int = 30):
        self.duration_seconds = duration_seconds
        self.poll_interval = poll_interval
        self.collectors: Dict[str, Any] = {}
        self.tasks: List[asyncio.Task] = []
        self.running = False
        self.start_time: Optional[datetime] = None
        
        # Services
        self.factory = get_collector_factory()
        self.monitoring = get_monitoring_service()
        self.error_handler = get_error_handler()
        
        # Setup
        self._setup_signal_handlers()
        self._setup_monitoring()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _setup_monitoring(self):
        """Setup monitoring and error handling."""
        # Record startup event
        self.monitoring.record_event("orchestrator_started", {
            "duration_seconds": self.duration_seconds,
            "poll_interval": self.poll_interval
        })
    
    async def start_collection(self, duration_seconds: int = 0, **kwargs) -> None:
        """Start data collection."""
        try:
            self.duration_seconds = duration_seconds or self.duration_seconds
            self.running = True
            self.start_time = datetime.now()
            
            logger.info("🚀 Starting simplified optimized data collection...")
            logger.info(f"⏱️  Duration: {self.duration_seconds} seconds")
            logger.info(f"🔄 Poll interval: {self.poll_interval} seconds")
            
            # Initialize and start collectors
            await self._initialize_collectors()
            await self._start_all_collectors()
            
            # Monitor collection
            await self._monitor_collection()
            
        except Exception as e:
            logger.error(f"❌ Error in data collection: {e}")
            await self.error_handler.handle_error(e, {"orchestrator": "start_collection"})
        finally:
            await self.stop_collection()
    
    async def _initialize_collectors(self):
        """Initialize all collectors using the original approach."""
        logger.info("🔧 Initializing collectors...")
        
        # Import collectors directly (original approach)
        from binance_realtime_collector_fixed import BinanceRealtimeCollectorFixed as BinanceRealtimeCollector
        from binance_funding_rates_collector import BinanceFundingRatesCollector
        from binance_open_interest_collector import BinanceOpenInterestCollector
        
        from bybit_realtime_collector_fixed import BybitRealtimeCollectorFixed as BybitRealtimeCollector
        from bybit_funding_rates_collector import BybitFundingRatesCollector
        from bybit_open_interest_collector import BybitOpenInterestCollector
        
        from robust_kraken_collector import RobustKrakenCollector
        from kraken_futures_collector import KrakenFuturesCollector
        
        from gate_realtime_collector_fixed import GateRealtimeCollectorFixed as GateRealtimeCollector
        from gate_futures_collector import GateFuturesCollector
        
        from okx_realtime_collector_fixed import OKXRealtimeCollectorFixed as OKXRealtimeCollector
        from okx_futures_websocket_collector import OKXFuturesWebSocketCollector
        
        # Create collectors (original approach)
        collector_configs = [
            # Binance
            ("binance_realtime", BinanceRealtimeCollector()),
            ("binance_funding_rates", BinanceFundingRatesCollector()),
            ("binance_open_interest", BinanceOpenInterestCollector()),
            
            # Bybit
            ("bybit_realtime", BybitRealtimeCollector()),
            ("bybit_funding_rates", BybitFundingRatesCollector()),
            ("bybit_open_interest", BybitOpenInterestCollector()),
            
            # Kraken
            ("kraken_realtime", RobustKrakenCollector()),
            ("kraken_futures", KrakenFuturesCollector()),
            
            # Gate.io
            ("gate_realtime", GateRealtimeCollector()),
            ("gate_futures", GateFuturesCollector()),
            
            # OKX
            ("okx_realtime", OKXRealtimeCollector()),
            ("okx_futures", OKXFuturesWebSocketCollector()),
        ]
        
        for name, collector in collector_configs:
            try:
                self.collectors[name] = collector
                logger.info(f"✅ Initialized {name}")
                self.monitoring.record_metric("collectors_initialized", 1)
                
            except Exception as e:
                logger.error(f"❌ Error initializing {name}: {e}")
                await self.error_handler.handle_error(e, {
                    "collector": name,
                    "operation": "initialize"
                })
        
        logger.info(f"✅ Initialized {len(self.collectors)} collectors")
    
    async def _start_all_collectors(self):
        """Start all collectors as concurrent tasks."""
        logger.info("📡 Starting all collectors...")
        
        for name, collector in self.collectors.items():
            try:
                # Determine which method to call
                if hasattr(collector, 'collect_data'):
                    method = collector.collect_data
                elif hasattr(collector, 'collect'):
                    method = collector.collect
                else:
                    logger.error(f"❌ {name} has no collect method")
                    continue
                
                # Start collector
                if 'poll_interval' in method.__code__.co_varnames:
                    task = asyncio.create_task(
                        method(duration_seconds=self.duration_seconds, poll_interval=self.poll_interval),
                        name=f"collector_{name}"
                    )
                else:
                    task = asyncio.create_task(
                        method(duration_seconds=self.duration_seconds),
                        name=f"collector_{name}"
                    )
                
                self.tasks.append(task)
                logger.info(f"✅ Started {name}")
                self.monitoring.record_event("collector_started", {"name": name})
                
            except Exception as e:
                logger.error(f"❌ Error starting {name}: {e}")
                await self.error_handler.handle_error(e, {
                    "collector": name,
                    "operation": "start"
                })
        
        logger.info(f"🚀 Started {len(self.tasks)} collection tasks")
        self.monitoring.record_metric("collectors_started", len(self.tasks))
    
    async def _monitor_collection(self):
        """Monitor collection progress."""
        logger.info("👀 Monitoring data collection...")
        
        last_stats_log = datetime.now()
        
        while self.running:
            try:
                now = datetime.now()
                elapsed = (now - self.start_time).total_seconds()
                
                # Check duration
                if self.duration_seconds > 0 and elapsed >= self.duration_seconds:
                    logger.info("⏰ Collection duration completed")
                    break
                
                # Log stats every 5 minutes
                if (now - last_stats_log).total_seconds() >= 300:
                    await self._log_collection_stats()
                    last_stats_log = now
                
                # Check for failed tasks
                await self._check_failed_tasks()
                
                # Record monitoring metrics
                self.monitoring.record_metric("orchestrator_uptime", elapsed)
                self.monitoring.record_metric("active_collectors", len(self.collectors))
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"❌ Error in monitoring: {e}")
                await self.error_handler.handle_error(e, {
                    "orchestrator": "monitor_collection"
                })
                await asyncio.sleep(5)
    
    async def _log_collection_stats(self):
        """Log collection statistics."""
        try:
            total_messages = 0
            total_errors = 0
            
            for name, collector in self.collectors.items():
                if hasattr(collector, 'stats'):
                    stats = collector.stats
                    total_messages += stats.get("stored", 0)
                    total_errors += stats.get("errors", 0)
            
            logger.info(f"📊 Collection Stats - Messages: {total_messages}, Errors: {total_errors}")
            
            # Record metrics
            self.monitoring.record_metric("total_messages_stored", total_messages)
            self.monitoring.record_metric("total_errors", total_errors)
            
        except Exception as e:
            logger.error(f"❌ Error logging stats: {e}")
    
    async def _check_failed_tasks(self):
        """Check for failed tasks and restart if needed."""
        failed_tasks = []
        
        for task in self.tasks:
            if task.done() and task.exception():
                failed_tasks.append(task)
        
        if failed_tasks:
            logger.warning(f"⚠️  Found {len(failed_tasks)} failed tasks")
            
            for task in failed_tasks:
                try:
                    error = task.exception()
                    logger.error(f"❌ Task {task.get_name()} failed: {error}")
                    
                except Exception as e:
                    logger.error(f"❌ Error handling failed task: {e}")
    
    async def stop_collection(self) -> None:
        """Stop data collection."""
        logger.info("🛑 Stopping data collection...")
        self.running = False
        
        try:
            # Cancel all tasks
            for task in self.tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for tasks to complete
            if self.tasks:
                await asyncio.gather(*self.tasks, return_exceptions=True)
            
            logger.info("✅ Stopped data collection")
            self.monitoring.record_event("orchestrator_stopped", {})
            
        except Exception as e:
            logger.error(f"❌ Error stopping collection: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get orchestrator status."""
        try:
            running_tasks = sum(1 for task in self.tasks if not task.done())
            uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            
            return {
                "running": self.running,
                "uptime_seconds": uptime,
                "total_collectors": len(self.collectors),
                "running_tasks": running_tasks,
                "total_tasks": len(self.tasks),
                "start_time": self.start_time.isoformat() if self.start_time else None,
                "health_status": self.monitoring.get_health_status()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting status: {e}")
            return {"error": str(e)}
    
    def get_collector_status(self, collector_name: str) -> Optional[Dict[str, Any]]:
        """Get specific collector status."""
        if collector_name not in self.collectors:
            return None
        
        try:
            collector = self.collectors[collector_name]
            stats = getattr(collector, 'stats', {})
            
            return {
                "name": collector_name,
                "status": "running" if collector_name in [t.get_name().replace("collector_", "") for t in self.tasks if not t.done()] else "stopped",
                "stats": stats
            }
        except Exception as e:
            logger.error(f"❌ Error getting collector status for {collector_name}: {e}")
            return {"error": str(e)}


async def main():
    """Main entry point for the simplified optimized orchestrator."""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    )
    
    # Parse command line arguments
    duration = 3600  # 1 hour default
    poll_interval = 30  # 30 seconds default
    
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            logger.error("Invalid duration. Using default 3600 seconds.")
    
    if len(sys.argv) > 2:
        try:
            poll_interval = int(sys.argv[2])
        except ValueError:
            logger.error("Invalid poll interval. Using default 30 seconds.")
    
    # Create and run orchestrator
    orchestrator = SimpleOptimizedOrchestrator(
        duration_seconds=duration,
        poll_interval=poll_interval
    )
    
    try:
        await orchestrator.start_collection()
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
    finally:
        # Print final summary
        status = orchestrator.get_status()
        logger.info("📊 Final Summary:")
        logger.info(f"  Total collectors: {status.get('total_collectors', 0)}")
        logger.info(f"  Running tasks: {status.get('running_tasks', 0)}")
        logger.info(f"  Uptime: {status.get('uptime_seconds', 0):.1f} seconds")


if __name__ == "__main__":
    asyncio.run(main())
