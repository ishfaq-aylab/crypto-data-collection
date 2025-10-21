#!/usr/bin/env python3
"""Gate.io futures funding rates and open interest REST API collector saving in DATA_DEFINITIONS.md schema."""

import asyncio
import aiohttp
import time
from datetime import datetime
from typing import List

from loguru import logger

from simple_mongodb_collector import SimpleMongoDBCollector
from models import WebSocketMessage, DataType, FundingRate, OpenInterest


class GateFuturesCollector:
    """Collect Gate.io futures funding rates and open interest via REST API and store in Mongo."""

    def __init__(self, symbols: List[str] | None = None):
        self.symbols = symbols or ["BTC_USDT"]  # Gate.io uses underscore format
        self.base_url = "https://api.gateio.ws"
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0}

    async def collect(self, duration_seconds: int = 90, poll_interval: int = 30):
        """Collect funding rates and open interest data via REST API polling."""
        await self.mongo.connect()
        logger.info("✅ Connected to MongoDB (Gate.io Futures)")

        try:
            start_time = time.time()
            while time.time() - start_time < duration_seconds:
                try:
                    await self._fetch_and_store_funding_rates()
                    await self._fetch_and_store_open_interest()
                    await asyncio.sleep(poll_interval)
                except Exception as e:
                    logger.error(f"Error in collection cycle: {e}")
                    self.stats["errors"] += 1
                    await asyncio.sleep(poll_interval)

        finally:
            await self.mongo.disconnect()
            logger.info("✅ Disconnected from MongoDB (Gate.io Futures)")
            logger.info(f"Stored={self.stats['stored']} errors={self.stats['errors']}")

    async def _fetch_and_store_funding_rates(self):
        """Fetch funding rates for all symbols and store in MongoDB."""
        async with aiohttp.ClientSession() as session:
            for symbol in self.symbols:
                try:
                    # Fetch funding rate from Gate.io REST API
                    url = f"{self.base_url}/api/v4/futures/usdt/funding_rate"
                    params = {"contract": symbol}
                    
                    async with session.get(url, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data:
                                await self._handle_funding_rate_data(symbol, data[0])
                        else:
                            logger.error(f"HTTP {response.status} for {symbol}: {await response.text()}")
                            self.stats["errors"] += 1
                            
                except Exception as e:
                    logger.error(f"Error fetching funding rate for {symbol}: {e}")
                    self.stats["errors"] += 1

    async def _fetch_and_store_open_interest(self):
        """Fetch open interest for all symbols and store in MongoDB."""
        async with aiohttp.ClientSession() as session:
            for symbol in self.symbols:
                try:
                    # Fetch open interest from Gate.io REST API
                    url = f"{self.base_url}/api/v4/futures/usdt/contracts/{symbol}"
                    
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data:
                                await self._handle_open_interest_data(symbol, data)
                        else:
                            logger.error(f"HTTP {response.status} for {symbol}: {await response.text()}")
                            self.stats["errors"] += 1
                            
                except Exception as e:
                    logger.error(f"Error fetching open interest for {symbol}: {e}")
                    self.stats["errors"] += 1

    async def _handle_funding_rate_data(self, symbol: str, data: dict):
        """Process and store funding rate data."""
        try:
            # Extract data from Gate.io response
            funding_rate = float(data.get("r", 0) or 0)  # Gate.io uses "r" for rate
            next_funding_time_ms = int(data.get("t", 0) or 0) * 1000  # Gate.io uses seconds
            
            if funding_rate == 0:
                return

            # Convert timestamp
            next_funding_time = datetime.fromtimestamp(next_funding_time_ms / 1000.0) if next_funding_time_ms else None
            
            # Calculate funding time (8 hours before next funding time)
            funding_time = None
            if next_funding_time:
                from datetime import timedelta
                funding_time = next_funding_time - timedelta(hours=8)

            # Gate.io funding interval is typically 8 hours
            funding_interval = 8

            # For now, we don't have predicted funding rate from this endpoint
            predicted_funding_rate = None

            fr = FundingRate(
                symbol=symbol,
                funding_rate=funding_rate,
                funding_time=funding_time,
                next_funding_time=next_funding_time,
                funding_interval=funding_interval,
                predicted_funding_rate=predicted_funding_rate,
                timestamp=datetime.now(),
                exchange="gate",
            )

            ws = WebSocketMessage(
                data_type=DataType.FUNDING_RATES,
                data=fr,
                raw_message={},
                exchange="gate",
            )
            
            await self.mongo.store_message(ws)
            self.stats["stored"] += 1
            
            logger.info(f"💰 Gate.io FUNDING RATE: {symbol} - Rate: {funding_rate:.6f} - Next: {next_funding_time}")

        except Exception as e:
            logger.error(f"Error processing funding rate for {symbol}: {e}")
            self.stats["errors"] += 1

    async def _handle_open_interest_data(self, symbol: str, data: dict):
        """Process and store open interest data."""
        try:
            # Extract data from Gate.io response
            open_interest = float(data.get("position_size", 0) or 0)  # Gate.io uses "position_size"
            # Calculate interest value from position size and mark price
            mark_price = float(data.get("mark_price", 0) or 0)
            open_interest_value = open_interest * mark_price if mark_price > 0 else None
            
            if open_interest <= 0:
                return

            # Gate.io only provides basic open interest data
            # Additional fields like long_short_ratio are not available from this endpoint
            oi = OpenInterest(
                symbol=symbol,
                open_interest=open_interest,
                long_short_ratio=None,  # Not available from Gate.io
                long_interest=None,     # Not available from Gate.io
                short_interest=None,    # Not available from Gate.io
                interest_value=open_interest_value,  # Calculated from position_size * mark_price
                top_trader_long_short_ratio=None,  # Not available from Gate.io
                timestamp=datetime.now(),
                exchange="gate",
            )

            ws = WebSocketMessage(
                data_type=DataType.OPEN_INTEREST,
                data=oi,
                raw_message={},
                exchange="gate",
            )
            
            await self.mongo.store_message(ws)
            self.stats["stored"] += 1
            
            logger.info(f"📊 Gate.io OPEN INTEREST: {symbol} - {open_interest:,.2f} contracts (${open_interest_value:,.2f})")

        except Exception as e:
            logger.error(f"Error processing open interest for {symbol}: {e}")
            self.stats["errors"] += 1


async def main():
    collector = GateFuturesCollector()
    await collector.collect(duration_seconds=90, poll_interval=30)


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda m: print(m, end=""),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n",
    )
    asyncio.run(main())
