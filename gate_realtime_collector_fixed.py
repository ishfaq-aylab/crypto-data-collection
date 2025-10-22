#!/usr/bin/env python3
"""Fixed Gate.io realtime WebSocket collector with better error handling and retry logic."""

import asyncio
import json
import time
import ssl
from datetime import datetime
from typing import List, Optional
from loguru import logger
import websockets
import aiohttp

from simple_mongodb_collector import SimpleMongoDBCollector
from models import WebSocketMessage, DataType, MarketData, OrderBookData, TickPrice, VolumeLiquidity


class GateRealtimeCollectorFixed:
    """Fixed Gate.io realtime collector with better error handling."""

    def __init__(self, pairs: List[str] | None = None):
        self.pairs = pairs or ["BTC_USDT", "BTC_USDC"]
        self.ws_url = "wss://api.gateio.ws/ws/v4/"
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0, "reconnects": 0}
        self.max_retries = 5
        self.retry_delay = 5

    async def _test_connectivity(self) -> bool:
        """Test if we can reach Gate.io API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.gateio.ws/api/v4/spot/currencies", timeout=10) as response:
                    if response.status == 200:
                        logger.info("✅ Gate.io API connectivity test passed")
                        return True
                    else:
                        logger.warning(f"⚠️ Gate.io API returned status {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Gate.io API connectivity test failed: {e}")
            return False

    async def _connect_with_retry(self) -> Optional[websockets.WebSocketServerProtocol]:
        """Connect to WebSocket with retry logic."""
        for attempt in range(self.max_retries):
            try:
                # Test connectivity first
                if not await self._test_connectivity():
                    if attempt < self.max_retries - 1:
                        logger.warning(f"⚠️ Connectivity test failed, retrying in {self.retry_delay}s...")
                        await asyncio.sleep(self.retry_delay)
                        continue
                    else:
                        logger.error("❌ Connectivity test failed after all retries")
                        return None

                # Create SSL context
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                # Connect to WebSocket
                ws = await websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=10,
                    ssl=ssl_context
                )
                
                logger.info("✅ Connected to Gate.io WebSocket")
                return ws

            except Exception as e:
                logger.error(f"❌ Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error("❌ All connection attempts failed")
                    return None

        return None

    async def _subscribe(self, ws, channel: str, pairs: List[str]):
        """Subscribe to a channel for given pairs."""
        try:
            if channel == "spot.order_book":
                # Special handling for order book with depth and interval
                for pair_data in pairs:
                    sub_msg = {
                        "time": int(time.time()),
                        "channel": channel,
                        "event": "subscribe",
                        "payload": pair_data
                    }
                    await ws.send(json.dumps(sub_msg))
            else:
                # Regular subscription
                sub_msg = {
                    "time": int(time.time()),
                    "channel": channel,
                    "event": "subscribe",
                    "payload": pairs
                }
                await ws.send(json.dumps(sub_msg))
            
            logger.info(f"📤 Subscribed to {channel} for {pairs}")
        except Exception as e:
            logger.error(f"❌ Subscription error for {channel}: {e}")

    async def _handle_message(self, message: dict, exchange: str = "gate"):
        """Handle incoming WebSocket message."""
        try:
            if "channel" in message:
                channel = message["channel"]
                data = message.get("result", {})
                
                if "spot.tickers" in channel:
                    await self._handle_ticker(data, exchange)
                elif "spot.trades" in channel:
                    await self._handle_trade(data, exchange)
                elif "spot.order_book" in channel:
                    await self._handle_orderbook(data, exchange)
                    
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
            self.stats["errors"] += 1

    async def _handle_ticker(self, data: dict, exchange: str):
        """Handle ticker data."""
        try:
            if not data:
                return
                
            symbol = data.get("currency_pair", "")
            if not symbol:
                return

            # Create market data
            market_data = MarketData(
                exchange=exchange,
                symbol=symbol,
                price=float(data.get("last", 0)),
                bid=float(data.get("highest_bid", 0)),
                ask=float(data.get("lowest_ask", 0)),
                bid_size=float(data.get("highest_bid_size", 0)),
                ask_size=float(data.get("lowest_ask_size", 0)),
                volume=float(data.get("base_volume", 0)),
                timestamp=datetime.now()
            )

            await self.mongo.store_market_data(market_data)
            self.stats["stored"] += 1

        except Exception as e:
            logger.error(f"❌ Error handling ticker: {e}")
            self.stats["errors"] += 1

    async def _handle_trade(self, data: dict, exchange: str):
        """Handle trade data."""
        try:
            if not data:
                return
                
            symbol = data.get("currency_pair", "")
            if not symbol:
                return

            # Create tick price
            tick_price = TickPrice(
                exchange=exchange,
                symbol=symbol,
                price=float(data.get("price", 0)),
                quantity=float(data.get("amount", 0)),
                timestamp=datetime.fromtimestamp(int(data.get("create_time", 0)))
            )

            await self.mongo.store_tick_price(tick_price)
            self.stats["stored"] += 1

        except Exception as e:
            logger.error(f"❌ Error handling trade: {e}")
            self.stats["errors"] += 1

    async def _handle_orderbook(self, data: dict, exchange: str):
        """Handle order book data."""
        try:
            if not data:
                return
                
            symbol = data.get("s", "")
            if not symbol:
                return

            bids = data.get("bids", [])
            asks = data.get("asks", [])

            if not bids or not asks:
                return

            # Create order book data
            order_book = OrderBookData(
                exchange=exchange,
                symbol=symbol,
                bids=[{"price": float(b[0]), "size": float(b[1])} for b in bids[:10]],
                asks=[{"price": float(a[0]), "size": float(a[1])} for a in asks[:10]],
                timestamp=datetime.now()
            )

            await self.mongo.store_order_book_data(order_book)
            self.stats["stored"] += 1

        except Exception as e:
            logger.error(f"❌ Error handling orderbook: {e}")
            self.stats["errors"] += 1

    async def collect(self, duration_seconds: int = 90):
        """Main collection method with improved error handling."""
        await self.mongo.connect()
        logger.info("✅ Connected to MongoDB (Gate.io Fixed)")

        start_time = time.time()
        last_stats_time = start_time

        while time.time() - start_time < duration_seconds:
            ws = None
            try:
                # Connect with retry
                ws = await self._connect_with_retry()
                if not ws:
                    logger.error("❌ Failed to connect to Gate.io WebSocket")
                    break

                # Subscribe to channels
                await self._subscribe(ws, "spot.tickers", self.pairs)
                await self._subscribe(ws, "spot.trades", self.pairs)
                await self._subscribe(ws, "spot.order_book", [[p, "20", "100ms"] for p in self.pairs])

                # Listen for messages
                async for message in ws:
                    try:
                        data = json.loads(message)
                        
                        # Handle subscription confirmation
                        if "event" in data and data.get("event") == "subscribe":
                            logger.info("✅ Subscription confirmed")
                            continue
                        
                        # Handle data messages
                        await self._handle_message(data)
                        
                        # Log stats every 30 seconds
                        if time.time() - last_stats_time > 30:
                            logger.info(f"📊 Gate.io stats: {self.stats}")
                            last_stats_time = time.time()

                    except json.JSONDecodeError as e:
                        logger.error(f"❌ JSON decode error: {e}")
                        self.stats["errors"] += 1
                    except Exception as e:
                        logger.error(f"❌ Message handling error: {e}")
                        self.stats["errors"] += 1

            except websockets.exceptions.ConnectionClosed:
                logger.warning("⚠️ WebSocket connection closed, reconnecting...")
                self.stats["reconnects"] += 1
                await asyncio.sleep(self.retry_delay)
            except Exception as e:
                logger.error(f"❌ Collection error: {e}")
                self.stats["errors"] += 1
                await asyncio.sleep(self.retry_delay)
            finally:
                if ws:
                    await ws.close()

        logger.info(f"✅ Gate.io collection completed. Stats: {self.stats}")


# For backward compatibility
GateRealtimeCollector = GateRealtimeCollectorFixed
