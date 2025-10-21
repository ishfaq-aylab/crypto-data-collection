#!/usr/bin/env python3
"""Kraken Futures funding rates and open interest REST API collector saving in DATA_DEFINITIONS.md schema."""

import asyncio
import aiohttp
import time
from datetime import datetime
from typing import List

from loguru import logger

from simple_mongodb_collector import SimpleMongoDBCollector
from models import WebSocketMessage, DataType, FundingRate, OpenInterest


class KrakenFuturesCollector:
    """Collect Kraken Futures funding rates and open interest via REST API and store in Mongo."""

    def __init__(self, symbols: List[str] | None = None):
        # Kraken Futures uses different symbol format - PI_XBTUSD for BTC perpetual
        self.symbols = symbols or ["PI_XBTUSD"]  # BTC perpetual on Kraken Futures
        self.base_url = "https://demo-futures.kraken.com"
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0}

    async def collect(self, duration_seconds: int = 90, poll_interval: int = 30):
        """Collect funding rates and open interest data via REST API polling."""
        await self.mongo.connect()
        logger.info("✅ Connected to MongoDB (Kraken Futures)")

        try:
            start_time = time.time()
            while time.time() - start_time < duration_seconds:
                try:
                    await self._fetch_and_store_futures_data()
                    await asyncio.sleep(poll_interval)
                except Exception as e:
                    logger.error(f"Error in collection cycle: {e}")
                    self.stats["errors"] += 1
                    await asyncio.sleep(poll_interval)

        finally:
            await self.mongo.disconnect()
            logger.info("✅ Disconnected from MongoDB (Kraken Futures)")
            logger.info(f"Stored={self.stats['stored']} errors={self.stats['errors']}")

    async def _fetch_and_store_futures_data(self):
        """Fetch funding rates and open interest for all symbols and store in MongoDB."""
        async with aiohttp.ClientSession() as session:
            try:
                # Fetch all tickers from Kraken Futures (includes funding rates and open interest)
                url = f"{self.base_url}/derivatives/api/v3/tickers"
                
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get("result") == "success" and data.get("tickers"):
                            await self._handle_tickers_data(data["tickers"])
                    else:
                        logger.error(f"HTTP {response.status} for tickers: {await response.text()}")
                        self.stats["errors"] += 1
                        
            except Exception as e:
                logger.error(f"Error fetching futures data: {e}")
                self.stats["errors"] += 1

    async def _handle_tickers_data(self, tickers: list):
        """Process tickers data and extract funding rates and open interest."""
        for ticker in tickers:
            try:
                symbol = ticker.get("symbol")
                if not symbol:
                    continue

                # Only process perpetual contracts
                if ticker.get("tag") != "perpetual":
                    continue

                # Extract funding rate data
                funding_rate = float(ticker.get("fundingRate", 0) or 0)
                if funding_rate != 0:
                    await self._handle_funding_rate_data(symbol, ticker)

                # Extract open interest data
                open_interest = float(ticker.get("openInterest", 0) or 0)
                if open_interest > 0:
                    await self._handle_open_interest_data(symbol, ticker)

            except Exception as e:
                logger.error(f"Error processing ticker {symbol}: {e}")
                self.stats["errors"] += 1

    async def _handle_funding_rate_data(self, symbol: str, ticker: dict):
        """Process and store funding rate data."""
        try:
            # Extract data from Kraken Futures response
            funding_rate = float(ticker.get("fundingRate", 0) or 0)
            funding_rate_prediction = float(ticker.get("fundingRatePrediction", 0) or 0)
            
            if funding_rate == 0:
                return

            # Kraken Futures doesn't provide explicit funding times, so we'll set them to None
            funding_time = None
            next_funding_time = None
            funding_interval = 8  # Standard for most exchanges

            fr = FundingRate(
                symbol=symbol,
                funding_rate=funding_rate,
                funding_time=funding_time,
                next_funding_time=next_funding_time,
                funding_interval=funding_interval,
                predicted_funding_rate=funding_rate_prediction if funding_rate_prediction != 0 else None,
                timestamp=datetime.now(),
                exchange="kraken",
            )

            ws = WebSocketMessage(
                data_type=DataType.FUNDING_RATES,
                data=fr,
                raw_message={},
                exchange="kraken",
            )
            
            await self.mongo.store_message(ws)
            self.stats["stored"] += 1
            
            logger.info(f"💰 Kraken Futures FUNDING RATE: {symbol} - Rate: {funding_rate:.6f} - Predicted: {funding_rate_prediction:.6f}")

        except Exception as e:
            logger.error(f"Error processing funding rate for {symbol}: {e}")
            self.stats["errors"] += 1

    async def _handle_open_interest_data(self, symbol: str, ticker: dict):
        """Process and store open interest data."""
        try:
            # Extract data from Kraken Futures response
            open_interest = float(ticker.get("openInterest", 0) or 0)
            mark_price = float(ticker.get("markPrice", 0) or 0)
            
            if open_interest <= 0:
                return

            # Calculate interest value from open interest and mark price
            open_interest_value = open_interest * mark_price if mark_price > 0 else None

            # Kraken Futures only provides basic open interest data
            # Additional fields like long_short_ratio are not available
            oi = OpenInterest(
                symbol=symbol,
                open_interest=open_interest,
                long_short_ratio=None,  # Not available from Kraken Futures
                long_interest=None,     # Not available from Kraken Futures
                short_interest=None,    # Not available from Kraken Futures
                interest_value=open_interest_value,  # Calculated from openInterest * markPrice
                top_trader_long_short_ratio=None,  # Not available from Kraken Futures
                timestamp=datetime.now(),
                exchange="kraken",
            )

            ws = WebSocketMessage(
                data_type=DataType.OPEN_INTEREST,
                data=oi,
                raw_message={},
                exchange="kraken",
            )
            
            await self.mongo.store_message(ws)
            self.stats["stored"] += 1
            
            logger.info(f"📊 Kraken Futures OPEN INTEREST: {symbol} - {open_interest:,.2f} contracts (${open_interest_value:,.2f})")

        except Exception as e:
            logger.error(f"Error processing open interest for {symbol}: {e}")
            self.stats["errors"] += 1


async def main():
    collector = KrakenFuturesCollector()
    await collector.collect(duration_seconds=90, poll_interval=30)


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda m: print(m, end=""),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n",
    )
    asyncio.run(main())
