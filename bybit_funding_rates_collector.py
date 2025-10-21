#!/usr/bin/env python3
"""Bybit funding rates WebSocket collector (futures) saving in DATA_DEFINITIONS.md schema."""

import asyncio
import json
import time
from datetime import datetime
from typing import List

from loguru import logger
import websockets

from simple_mongodb_collector import SimpleMongoDBCollector
from models import WebSocketMessage, DataType, FundingRate


class BybitFundingRatesCollector:
    """Collect Bybit futures funding rates and store in Mongo."""

    def __init__(self, symbols: List[str] | None = None):
        self.symbols = symbols or ["BTCUSDT"]  # Only BTCUSDT is available on Bybit
        self.ws_url = "wss://stream-testnet.bybit.com/v5/public/linear"
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0}

    def _build_subscriptions(self) -> List[str]:
        """Build subscription topics for funding rate data."""
        topics = []
        for symbol in self.symbols:
            topics.append(f"tickers.{symbol}")
        return topics

    async def collect(self, duration_seconds: int = 90):
        await self.mongo.connect()
        logger.info("✅ Connected to MongoDB (Bybit Funding Rates)")

        try:
            async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10) as ws:
                logger.info("✅ Connected to Bybit Futures WebSocket")

                # Subscribe to ticker streams (which include funding rate data)
                sub_msg = {
                    "op": "subscribe",
                    "args": self._build_subscriptions()
                }
                await ws.send(json.dumps(sub_msg))
                logger.info(f"📤 Subscribed: {sub_msg['args']}")

                # Start ping task to keep connection alive
                ping_task = asyncio.create_task(self._ping_loop(ws))

                start = time.time()
                while time.time() - start < duration_seconds:
                    try:
                        raw = await asyncio.wait_for(ws.recv(), timeout=2.0)
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"WS recv error: {e}")
                        self.stats["errors"] += 1
                        continue

                    await self._handle_message(raw)

                # Cancel ping task
                ping_task.cancel()

        finally:
            await self.mongo.disconnect()
            logger.info("✅ Disconnected from MongoDB (Bybit Funding Rates)")
            logger.info(f"Stored={self.stats['stored']} errors={self.stats['errors']}")

    async def _ping_loop(self, ws):
        """Send periodic pings to keep WebSocket alive."""
        while True:
            try:
                await asyncio.sleep(10)
                await ws.send(json.dumps({"op": "ping"}))
            except Exception as e:
                logger.error(f"Ping error: {e}")
                break

    async def _handle_message(self, raw: str):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        if not isinstance(msg, dict):
            return

        # Debug: Log all messages (commented out for production)
        # logger.info(f"Received message: {json.dumps(msg, indent=2)}")

        # Handle ticker data (which includes funding rate)
        if msg.get("topic", "").startswith("tickers.") and msg.get("type") == "snapshot":
            await self._handle_ticker_data(msg)

    async def _handle_ticker_data(self, msg: dict):
        """Process ticker data and extract funding rate information."""
        try:
            data = msg.get("data", {})
            symbol = data.get("symbol")
            
            if not symbol:
                return

            # Extract funding rate data
            funding_rate = float(data.get("fundingRate", 0) or 0)
            next_funding_time_ms = int(data.get("nextFundingTime", 0) or 0)
            funding_interval_hours = int(data.get("fundingIntervalHour", 0) or 0)
            
            if funding_rate == 0:
                return

            # Convert timestamp
            next_funding_time = datetime.fromtimestamp(next_funding_time_ms / 1000.0) if next_funding_time_ms else None
            
            # Calculate funding time (funding interval before next funding time)
            funding_time = None
            if next_funding_time and funding_interval_hours:
                from datetime import timedelta
                funding_time = next_funding_time - timedelta(hours=funding_interval_hours)

            # For now, we don't have predicted funding rate from this stream
            predicted_funding_rate = None

            fr = FundingRate(
                symbol=symbol,
                funding_rate=funding_rate,
                funding_time=funding_time,
                next_funding_time=next_funding_time,
                funding_interval=funding_interval_hours,
                predicted_funding_rate=predicted_funding_rate,
                timestamp=datetime.now(),
                exchange="bybit",
            )

            ws = WebSocketMessage(
                data_type=DataType.FUNDING_RATES,
                data=fr,
                raw_message={},
                exchange="bybit",
            )
            await self.mongo.store_message(ws)
            self.stats["stored"] += 1
            
            logger.info(f"💰 Bybit FUNDING RATE: {symbol} - Rate: {funding_rate:.6f} - Next: {next_funding_time}")

        except Exception as e:
            logger.error(f"Bybit funding rate parse error: {e}")
            self.stats["errors"] += 1


async def main():
    collector = BybitFundingRatesCollector()
    await collector.collect(duration_seconds=90)


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda m: print(m, end=""),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n",
    )
    asyncio.run(main())
