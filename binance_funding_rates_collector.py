#!/usr/bin/env python3
"""Binance funding rates WebSocket collector (futures) saving in DATA_DEFINITIONS.md schema."""

import asyncio
import json
import time
from datetime import datetime
from typing import List

from loguru import logger
import websockets

from simple_mongodb_collector import SimpleMongoDBCollector
from models import WebSocketMessage, DataType, FundingRate


class BinanceFundingRatesCollector:
    """Collect Binance futures funding rates and store in Mongo."""

    def __init__(self, symbols: List[str] | None = None):
        self.symbols = symbols or ["BTCUSDT", "BTCUSDC"]
        # Multiple Binance futures endpoints to try
        self.ws_endpoints = [
            "wss://fstream.binance.com/ws",
            "wss://fstream1.binance.com/ws",
            "wss://fstream2.binance.com/ws",
            "wss://fstream3.binance.com/ws"
        ]
        self.api_endpoints = [
            "https://fapi.binance.com",
            "https://fapi1.binance.com",
            "https://fapi2.binance.com", 
            "https://fapi3.binance.com"
        ]
        self.current_ws_endpoint = 0
        self.current_api_endpoint = 0
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0}

    def _build_params(self) -> List[str]:
        params: List[str] = []
        for s in self.symbols:
            lower = s.lower()
            params.append(f"{lower}@markPrice")  # Mark price stream includes funding rate
        return params

    async def collect(self, duration_seconds: int = 90):
        await self.mongo.connect()
        logger.info("✅ Connected to MongoDB (Binance Funding Rates)")

        try:
            async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10) as ws:
                logger.info("✅ Connected to Binance Futures WebSocket")

                sub_msg = {
                    "method": "SUBSCRIBE",
                    "params": self._build_params(),
                    "id": 1
                }
                await ws.send(json.dumps(sub_msg))
                logger.info(f"📤 Subscribed: {sub_msg['params']}")

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

        finally:
            await self.mongo.disconnect()
            logger.info("✅ Disconnected from MongoDB (Binance Funding Rates)")
            logger.info(f"Stored={self.stats['stored']} errors={self.stats['errors']}")

    async def _handle_message(self, raw: str):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        if not isinstance(msg, dict):
            return

        # Ignore subscription acks
        if msg.get("result") is None and msg.get("id") is not None and not msg.get("e"):
            return

        # Handle mark price updates (which include funding rate)
        if msg.get("e") == "markPriceUpdate":
            await self._handle_funding_rate(msg)

    async def _handle_funding_rate(self, m: dict):
        try:
            symbol = m.get("s")
            funding_rate = float(m.get("r", 0) or 0)  # Current funding rate
            next_funding_time_ms = int(m.get("T", 0) or 0)  # Next funding time
            
            if not symbol or funding_rate == 0:
                return

            # Calculate funding time (8 hours before next funding time)
            next_funding_time = datetime.fromtimestamp(next_funding_time_ms / 1000.0) if next_funding_time_ms else None
            funding_time = None
            if next_funding_time:
                from datetime import timedelta
                funding_time = next_funding_time - timedelta(hours=8)

            # For Binance, funding interval is always 8 hours
            funding_interval = 8

            # For now, we don't have predicted funding rate from this stream
            # Could be enhanced with additional API calls if needed
            predicted_funding_rate = None

            fr = FundingRate(
                symbol=symbol,
                funding_rate=funding_rate,
                funding_time=funding_time,
                next_funding_time=next_funding_time,
                funding_interval=funding_interval,
                predicted_funding_rate=predicted_funding_rate,
                timestamp=datetime.now(),
                exchange="binance",
            )

            ws = WebSocketMessage(
                data_type=DataType.FUNDING_RATES,
                data=fr,
                raw_message={},
                exchange="binance",
            )
            await self.mongo.store_message(ws)
            self.stats["stored"] += 1
            
            logger.info(f"💰 Binance FUNDING RATE: {symbol} - Rate: {funding_rate:.6f} - Next: {next_funding_time}")

        except Exception as e:
            logger.error(f"Binance funding rate parse error: {e}")
            self.stats["errors"] += 1


async def main():
    collector = BinanceFundingRatesCollector()
    await collector.collect(duration_seconds=90)


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda m: print(m, end=""),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n",
    )
    asyncio.run(main())
