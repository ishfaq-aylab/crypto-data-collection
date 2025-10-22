#!/usr/bin/env python3
"""Test script for all fixed real-time collectors."""

import asyncio
import sys
from datetime import datetime
from loguru import logger

# Import fixed collectors
from binance_realtime_collector_fixed import BinanceRealtimeCollectorFixed
from bybit_realtime_collector_fixed import BybitRealtimeCollectorFixed
from okx_realtime_collector_fixed import OKXRealtimeCollectorFixed
from gate_realtime_collector_fixed import GateRealtimeCollectorFixed


async def test_collector(collector_class, name: str, duration: int = 60):
    """Test a single collector."""
    logger.info(f"🧪 Testing {name} collector for {duration} seconds...")
    
    try:
        collector = collector_class()
        await collector.collect(duration)
        logger.info(f"✅ {name} test completed. Stats: {collector.stats}")
        return True
    except Exception as e:
        logger.error(f"❌ {name} test failed: {e}")
        return False


async def test_all_collectors():
    """Test all fixed collectors."""
    logger.info("🚀 Starting collector tests...")
    logger.info("=" * 80)
    
    # Test configuration
    test_duration = 60  # 1 minute per collector
    collectors = [
        (BinanceRealtimeCollectorFixed, "Binance"),
        (BybitRealtimeCollectorFixed, "Bybit"),
        (OKXRealtimeCollectorFixed, "OKX"),
        (GateRealtimeCollectorFixed, "Gate.io"),
    ]
    
    results = {}
    
    for collector_class, name in collectors:
        logger.info(f"\n🔄 Testing {name}...")
        success = await test_collector(collector_class, name, test_duration)
        results[name] = success
        logger.info(f"{'✅' if success else '❌'} {name} test {'passed' if success else 'failed'}")
    
    # Summary
    logger.info("\n" + "=" * 80)
    logger.info("📊 TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for success in results.values() if success)
    total = len(results)
    
    for name, success in results.items():
        status = "✅ PASSED" if success else "❌ FAILED"
        logger.info(f"{name:12} - {status}")
    
    logger.info(f"\nOverall: {passed}/{total} collectors passed")
    
    if passed == total:
        logger.info("🎉 All collectors are working!")
        return True
    else:
        logger.warning(f"⚠️ {total - passed} collectors need attention")
        return False


async def main():
    """Main test function."""
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - <level>{message}</level>",
    )
    
    logger.info("🧪 FIXED COLLECTORS TEST SUITE")
    logger.info("=" * 80)
    logger.info(f"📅 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("⏱️  Test duration: 60 seconds per collector")
    logger.info("")
    
    try:
        success = await test_all_collectors()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Tests interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Test suite failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
