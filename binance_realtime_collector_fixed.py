#!/usr/bin/env python3
"""Fixed Binance realtime WebSocket collector with better error handling and retry logic."""

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


class BinanceRealtimeCollectorFixed:
    """Fixed Binance realtime collector with better error handling."""

    def __init__(self, symbols: List[str] | None = None):
        self.symbols = symbols or ["BTCUSDT", "BTCUSDC"]
        self.ws_url = "wss://stream.binance.com:9443/ws"
        self.alt_ws_url = "wss://stream1.binance.com:9443/ws"  # Alternative endpoint
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0, "reconnects": 0}
        self.max_retries = 5
        self.retry_delay = 5

    def _build_params(self) -> List[str]:
        """Build subscription parameters."""
        params: List[str] = []
        for s in self.symbols:
            lower = s.lower()
            params.append(f"{lower}@ticker")          # 24hr ticker
            params.append(f"{lower}@trade")           # trades
            params.append(f"{lower}@depth20@100ms")   # order book depth 20
        return params

    async def _test_connectivity(self) -> bool:
        """Test if we can reach Binance API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.binance.com/api/v3/ping", timeout=10) as response:
                    if response.status == 200:
                        logger.info("✅ Binance API connectivity test passed")
                        return True
                    elif response.status == 451:
                        logger.warning("⚠️ Binance API blocked due to geographic restrictions (HTTP 451)")
                        logger.info("🔄 Attempting to use alternative endpoints...")
                        # Try alternative endpoints
                        try:
                            async with session.get("https://api1.binance.com/api/v3/ping", timeout=10) as alt_response:
                                if alt_response.status == 200:
                                    logger.info("✅ Alternative Binance endpoint accessible")
                                    return True
                        except:
                            pass
                        return False
                    else:
                        logger.warning(f"⚠️ Binance API returned status {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Binance API connectivity test failed: {e}")
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

                # Create SSL context for better compatibility
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE

                # Try primary WebSocket endpoint first
                try:
                    ws = await websockets.connect(
                        self.ws_url,
                        ping_interval=20,
                        ping_timeout=10,
                        ssl=ssl_context
                    )
                except Exception as e:
                    logger.warning(f"⚠️ Primary WebSocket failed: {e}")
                    logger.info("🔄 Trying alternative WebSocket endpoint...")
                    # Try alternative endpoint
                    ws = await websockets.connect(
                        self.alt_ws_url,
                        ping_interval=20,
                        ping_timeout=10,
                        ssl=ssl_context
                    )
                
                logger.info("✅ Connected to Binance WebSocket")
                return ws

            except Exception as e:
                logger.error(f"❌ Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error("❌ All connection attempts failed")
                    return None

        return None

    async def _handle_message(self, message: dict, exchange: str = "binance"):
        """Handle incoming WebSocket message."""
        try:
            if "stream" in message:
                stream = message["stream"]
                data = message["data"]
                
                if "@ticker" in stream:
                    await self._handle_ticker(data, exchange)
                elif "@trade" in stream:
                    await self._handle_trade(data, exchange)
                elif "@depth" in stream:
                    await self._handle_orderbook(data, exchange)
                    
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
            self.stats["errors"] += 1

    async def _handle_ticker(self, data: dict, exchange: str):
        """Handle ticker data."""
        try:
            symbol = data.get("s", "")
            if not symbol:
                return

            # Create market data
            market_data = MarketData(
                exchange=exchange,
                symbol=symbol,
                price=float(data.get("c", 0)),
                bid=float(data.get("b", 0)),
                ask=float(data.get("a", 0)),
                bid_size=float(data.get("B", 0)),
                ask_size=float(data.get("A", 0)),
                volume=float(data.get("v", 0)),
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
            symbol = data.get("s", "")
            if not symbol:
                return

            # Create tick price
            tick_price = TickPrice(
                exchange=exchange,
                symbol=symbol,
                price=float(data.get("p", 0)),
                volume=float(data.get("q", 0)),
                timestamp=datetime.fromtimestamp(data.get("T", 0) / 1000)
            )

            await self.mongo.store_tick_price(tick_price)
            self.stats["stored"] += 1

        except Exception as e:
            logger.error(f"❌ Error handling trade: {e}")
            self.stats["errors"] += 1

    async def _handle_orderbook(self, data: dict, exchange: str):
        """Handle order book data."""
        try:
            symbol = data.get("s", "")
            if not symbol:
                return

            bids = data.get("b", [])
            asks = data.get("a", [])

            if not bids or not asks:
                return

            # Create order book data
            order_book = OrderBookData(
                exchange=exchange,
                symbol=symbol,
                bids=[[float(b[0]), float(b[1])] for b in bids[:10]],
                asks=[[float(a[0]), float(a[1])] for a in asks[:10]],
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
        logger.info("✅ Connected to MongoDB (Binance Fixed)")

        start_time = time.time()
        last_stats_time = start_time

        while time.time() - start_time < duration_seconds:
            ws = None
            try:
                # Connect with retry
                ws = await self._connect_with_retry()
                if not ws:
                    logger.error("❌ Failed to connect to Binance WebSocket")
                    break

                # Subscribe to streams
                sub_msg = {
                    "method": "SUBSCRIBE",
                    "params": self._build_params(),
                    "id": 1
                }
                await ws.send(json.dumps(sub_msg))
                logger.info(f"📤 Subscribed to: {sub_msg['params']}")

                # Listen for messages
                async for message in ws:
                    try:
                        data = json.loads(message)
                        
                        # Handle subscription confirmation
                        if "result" in data and data.get("id") == 1:
                            logger.info("✅ Subscription confirmed")
                            continue
                        
                        # Handle data messages
                        await self._handle_message(data)
                        
                        # Log stats every 30 seconds
                        if time.time() - last_stats_time > 30:
                            logger.info(f"📊 Binance stats: {self.stats}")
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

        logger.info(f"✅ Binance collection completed. Stats: {self.stats}")


# For backward compatibility
BinanceRealtimeCollector = BinanceRealtimeCollectorFixed
