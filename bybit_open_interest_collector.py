#!/usr/bin/env python3
"""Bybit open interest WebSocket collector (futures) saving in DATA_DEFINITIONS.md schema."""

import asyncio
import json
import time
from datetime import datetime
from typing import List

from loguru import logger
import websockets

from simple_mongodb_collector import SimpleMongoDBCollector
from models import WebSocketMessage, DataType, OpenInterest


class BybitOpenInterestCollector:
    """Collect Bybit futures open interest and store in Mongo."""

    def __init__(self, symbols: List[str] | None = None):
        self.symbols = symbols or ["BTCUSDT"]  # Only BTCUSDT is available on Bybit
        self.ws_url = "wss://stream-testnet.bybit.com/v5/public/linear"
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0}

    def _build_subscriptions(self) -> List[str]:
        """Build subscription topics for open interest data."""
        topics = []
        for symbol in self.symbols:
            topics.append(f"tickers.{symbol}")
        return topics

    async def collect(self, duration_seconds: int = 90):
        await self.mongo.connect()
        logger.info("✅ Connected to MongoDB (Bybit Open Interest)")

        try:
            async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10) as ws:
                logger.info("✅ Connected to Bybit Futures WebSocket")

                # Subscribe to ticker streams (which include open interest data)
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
            logger.info("✅ Disconnected from MongoDB (Bybit Open Interest)")
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

        # Handle ticker data (which includes open interest)
        if msg.get("topic", "").startswith("tickers.") and msg.get("type") == "snapshot":
            await self._handle_ticker_data(msg)

    async def _handle_ticker_data(self, msg: dict):
        """Process ticker data and extract open interest information."""
        try:
            data = msg.get("data", {})
            symbol = data.get("symbol")
            
            if not symbol:
                return

            # Extract open interest data
            open_interest = float(data.get("openInterest", 0) or 0)
            open_interest_value = float(data.get("openInterestValue", 0) or 0)
            
            if open_interest <= 0:
                return

            # Bybit only provides basic open interest data
            # Additional fields like long_short_ratio are not available from this stream
            oi = OpenInterest(
                symbol=symbol,
                open_interest=open_interest,
                long_short_ratio=None,  # Not available from Bybit
                long_interest=None,     # Not available from Bybit
                short_interest=None,    # Not available from Bybit
                interest_value=open_interest_value,  # Use openInterestValue as interest_value
                top_trader_long_short_ratio=None,  # Not available from Bybit
                timestamp=datetime.now(),
                exchange="bybit",
            )

            ws = WebSocketMessage(
                data_type=DataType.OPEN_INTEREST,
                data=oi,
                raw_message={},
                exchange="bybit",
            )
            await self.mongo.store_message(ws)
            self.stats["stored"] += 1
            
            logger.info(f"📊 Bybit OPEN INTEREST: {symbol} - {open_interest:,.2f} BTC (${open_interest_value:,.2f})")

        except Exception as e:
            logger.error(f"Bybit open interest parse error: {e}")
            self.stats["errors"] += 1


async def main():
    collector = BybitOpenInterestCollector()
    await collector.collect(duration_seconds=90)


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda m: print(m, end=""),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n",
    )
    asyncio.run(main())
