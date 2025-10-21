#!/usr/bin/env python3
"""Binance open interest REST API collector (futures) saving in DATA_DEFINITIONS.md schema."""

import asyncio
import aiohttp
import time
from datetime import datetime
from typing import List

from loguru import logger

from simple_mongodb_collector import SimpleMongoDBCollector
from models import WebSocketMessage, DataType, OpenInterest


class BinanceOpenInterestCollector:
    """Collect Binance futures open interest via REST API and store in Mongo."""

    def __init__(self, symbols: List[str] | None = None):
        self.symbols = symbols or ["BTCUSDT", "BTCUSDC"]
        self.base_url = "https://fapi.binance.com"
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0}

    async def collect(self, duration_seconds: int = 90, poll_interval: int = 10):
        """Collect open interest data via REST API polling."""
        await self.mongo.connect()
        logger.info("✅ Connected to MongoDB (Binance Open Interest)")

        try:
            start_time = time.time()
            while time.time() - start_time < duration_seconds:
                try:
                    await self._fetch_and_store_open_interest()
                    await asyncio.sleep(poll_interval)
                except Exception as e:
                    logger.error(f"Error in collection cycle: {e}")
                    self.stats["errors"] += 1
                    await asyncio.sleep(poll_interval)

        finally:
            await self.mongo.disconnect()
            logger.info("✅ Disconnected from MongoDB (Binance Open Interest)")
            logger.info(f"Stored={self.stats['stored']} errors={self.stats['errors']}")

    async def _fetch_and_store_open_interest(self):
        """Fetch open interest for all symbols and store in MongoDB."""
        async with aiohttp.ClientSession() as session:
            for symbol in self.symbols:
                try:
                    # Fetch open interest from Binance REST API
                    url = f"{self.base_url}/fapi/v1/openInterest"
                    params = {"symbol": symbol}
                    
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            await self._handle_open_interest_data(symbol, data)
                        else:
                            logger.error(f"HTTP {response.status} for {symbol}: {await response.text()}")
                            self.stats["errors"] += 1
                            
                except Exception as e:
                    logger.error(f"Error fetching open interest for {symbol}: {e}")
                    self.stats["errors"] += 1

    async def _handle_open_interest_data(self, symbol: str, data: dict):
        """Process and store open interest data."""
        try:
            # Extract data from Binance response
            open_interest = float(data.get("openInterest", 0) or 0)
            timestamp_ms = int(data.get("time", 0) or 0)
            
            if open_interest <= 0:
                logger.warning(f"Invalid open interest for {symbol}: {open_interest}")
                return

            # Convert timestamp
            timestamp = datetime.fromtimestamp(timestamp_ms / 1000.0) if timestamp_ms else datetime.now()

            # Binance only provides basic open interest data
            # Additional fields like long_short_ratio are not available from this endpoint
            oi = OpenInterest(
                symbol=symbol,
                open_interest=open_interest,
                long_short_ratio=None,  # Not available from Binance
                long_interest=None,     # Not available from Binance
                short_interest=None,    # Not available from Binance
                interest_value=None,    # Could be calculated as open_interest * current_price
                top_trader_long_short_ratio=None,  # Not available from Binance
                timestamp=timestamp,
                exchange="binance",
            )

            ws = WebSocketMessage(
                data_type=DataType.OPEN_INTEREST,
                data=oi,
                raw_message={},
                exchange="binance",
            )
            
            await self.mongo.store_message(ws)
            self.stats["stored"] += 1
            
            logger.info(f"📊 Binance OPEN INTEREST: {symbol} - {open_interest:,.2f} BTC")

        except Exception as e:
            logger.error(f"Error processing open interest for {symbol}: {e}")
            self.stats["errors"] += 1


async def main():
    collector = BinanceOpenInterestCollector()
    await collector.collect(duration_seconds=90, poll_interval=10)


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda m: print(m, end=""),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n",
    )
    asyncio.run(main())
