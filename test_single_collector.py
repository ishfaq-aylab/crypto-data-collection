#!/usr/bin/env python3
"""Test a single collector to verify setup."""

import asyncio
import sys
from datetime import datetime
from loguru import logger

from binance_realtime_collector_fixed import BinanceRealtimeCollectorFixed


async def test_binance():
    """Test Binance collector."""
    logger.info("🧪 Testing Binance collector...")
    
    try:
        collector = BinanceRealtimeCollectorFixed()
        await collector.collect(30)  # 30 seconds
        logger.info(f"✅ Binance test completed. Stats: {collector.stats}")
        return True
    except Exception as e:
        logger.error(f"❌ Binance test failed: {e}")
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
    
    logger.info("🧪 SINGLE COLLECTOR TEST")
    logger.info("=" * 50)
    
    try:
        success = await test_binance()
        if success:
            logger.info("🎉 Test passed!")
        else:
            logger.error("❌ Test failed!")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
