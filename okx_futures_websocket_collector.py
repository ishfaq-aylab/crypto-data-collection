#!/usr/bin/env python3
"""OKX futures funding rates and open interest WebSocket collector saving in DATA_DEFINITIONS.md schema."""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import List

import websockets
from loguru import logger

from simple_mongodb_collector import SimpleMongoDBCollector
from models import WebSocketMessage, DataType, FundingRate, OpenInterest


class OKXFuturesWebSocketCollector:
    """Collect OKX futures funding rates and open interest via WebSocket and store in Mongo."""

    def __init__(self, symbols: List[str] | None = None):
        self.symbols = symbols or ["BTC-USDT-SWAP", "BTC-USDC-SWAP"]
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0}

    def _build_subscriptions(self) -> List[dict]:
        """Builds a list of subscription topics for funding rates and open interest."""
        subscriptions = []
        for symbol in self.symbols:
            subscriptions.extend([
                {"channel": "funding-rate", "instId": symbol},
                {"channel": "open-interest", "instId": symbol}
            ])
        return subscriptions

    async def collect(self, duration_seconds: int = 90):
        """Collect funding rates and open interest data via WebSocket."""
        await self.mongo.connect()
        logger.info("✅ Connected to MongoDB (OKX Futures WebSocket)")

        try:
            async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10) as ws:
                logger.info("✅ Connected to OKX Futures WebSocket")

                # Subscribe to funding rates and open interest
                subscriptions = self._build_subscriptions()
                subscribe_msg = {"op": "subscribe", "args": subscriptions}
                await ws.send(json.dumps(subscribe_msg))
                logger.info(f"📤 Subscribed: {len(subscriptions)} topics")

                start_time = time.time()
                while time.time() - start_time < duration_seconds:
                    try:
                        raw_message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        await self._handle_message(raw_message)
                    except asyncio.TimeoutError:
                        # No message received in 1 second, continue loop
                        pass
                    except websockets.exceptions.ConnectionClosedOK:
                        logger.info("OKX WebSocket connection closed gracefully.")
                        break
                    except Exception as e:
                        logger.error(f"Error receiving message: {e}")
                        self.stats["errors"] += 1

        except Exception as e:
            logger.error(f"OKX WebSocket connection error: {e}")
            self.stats["errors"] += 1
        finally:
            await self.mongo.disconnect()
            logger.info("✅ Disconnected from MongoDB (OKX Futures WebSocket)")
            logger.info(f"Stored={self.stats['stored']} errors={self.stats['errors']}")

    async def _handle_message(self, raw: str):
        """Process incoming WebSocket messages."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON: {raw}")
            self.stats["errors"] += 1
            return

        if not isinstance(msg, dict):
            return

        # Handle funding rate data
        if msg.get("arg", {}).get("channel") == "funding-rate" and "data" in msg:
            await self._handle_funding_rate_data(msg)

        # Handle open interest data
        elif msg.get("arg", {}).get("channel") == "open-interest" and "data" in msg:
            await self._handle_open_interest_data(msg)

    async def _handle_funding_rate_data(self, msg: dict):
        """Process and store funding rate data."""
        try:
            data_list = msg.get("data", [])
            if not data_list:
                return

            for data in data_list:
                symbol = data.get("instId")
                funding_rate = float(data.get("fundingRate", 0) or 0)
                funding_time_ms = int(data.get("fundingTime", 0) or 0)
                next_funding_time_ms = int(data.get("nextFundingTime", 0) or 0)
                
                if not symbol or funding_rate == 0:
                    continue

                # Convert timestamps
                funding_time = datetime.fromtimestamp(funding_time_ms / 1000.0) if funding_time_ms else None
                next_funding_time = datetime.fromtimestamp(next_funding_time_ms / 1000.0) if next_funding_time_ms else None
                
                # Calculate funding interval (typically 8 hours)
                funding_interval = 8
                if next_funding_time and funding_time:
                    interval_hours = (next_funding_time - funding_time).total_seconds() / 3600
                    if 0 < interval_hours <= 24:  # Reasonable funding interval
                        funding_interval = int(interval_hours)

                # Get predicted funding rate if available
                predicted_funding_rate = None
                next_funding_rate = data.get("nextFundingRate")
                if next_funding_rate and next_funding_rate != "":
                    try:
                        predicted_funding_rate = float(next_funding_rate)
                    except (ValueError, TypeError):
                        pass

                fr = FundingRate(
                    symbol=symbol,
                    funding_rate=funding_rate,
                    funding_time=funding_time,
                    next_funding_time=next_funding_time,
                    funding_interval=funding_interval,
                    predicted_funding_rate=predicted_funding_rate,
                    timestamp=datetime.now(),
                    exchange="okx",
                )

                ws = WebSocketMessage(
                    data_type=DataType.FUNDING_RATES,
                    data=fr,
                    raw_message={},
                    exchange="okx",
                )
                
                await self.mongo.store_message(ws)
                self.stats["stored"] += 1
                
                logger.info(f"💰 OKX Futures FUNDING RATE: {symbol} - Rate: {funding_rate:.6f} - Next: {next_funding_time}")

        except Exception as e:
            logger.error(f"Error processing funding rate: {e}")
            self.stats["errors"] += 1

    async def _handle_open_interest_data(self, msg: dict):
        """Process and store open interest data."""
        try:
            data_list = msg.get("data", [])
            if not data_list:
                return

            for data in data_list:
                symbol = data.get("instId")
                open_interest = float(data.get("oi", 0) or 0)
                open_interest_ccy = float(data.get("oiCcy", 0) or 0)
                open_interest_usd = float(data.get("oiUsd", 0) or 0)
                
                if not symbol or open_interest <= 0:
                    continue

                # OKX provides open interest in base asset (oi), quote asset (oiCcy), and USD (oiUsd)
                # We'll use oiUsd as the interest_value
                oi = OpenInterest(
                    symbol=symbol,
                    open_interest=open_interest,
                    long_short_ratio=None,  # Not available from OKX
                    long_interest=None,     # Not available from OKX
                    short_interest=None,    # Not available from OKX
                    interest_value=open_interest_usd,  # Use USD value
                    top_trader_long_short_ratio=None,  # Not available from OKX
                    timestamp=datetime.now(),
                    exchange="okx",
                )

                ws = WebSocketMessage(
                    data_type=DataType.OPEN_INTEREST,
                    data=oi,
                    raw_message={},
                    exchange="okx",
                )
                
                await self.mongo.store_message(ws)
                self.stats["stored"] += 1
                
                logger.info(f"📊 OKX Futures OPEN INTEREST: {symbol} - {open_interest:,.2f} contracts (${open_interest_usd:,.2f})")

        except Exception as e:
            logger.error(f"Error processing open interest: {e}")
            self.stats["errors"] += 1


async def main():
    collector = OKXFuturesWebSocketCollector()
    await collector.collect(duration_seconds=90)


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda m: print(m, end=""),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n",
    )
    asyncio.run(main())
