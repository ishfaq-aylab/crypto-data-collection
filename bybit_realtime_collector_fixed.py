#!/usr/bin/env python3
"""Fixed Bybit realtime WebSocket collector with better error handling and retry logic."""

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


class BybitRealtimeCollectorFixed:
    """Fixed Bybit realtime collector with better error handling."""

    def __init__(self, symbols: List[str] | None = None):
        self.symbols = symbols or ["BTCUSDT", "BTCUSDC"]
        self.ws_url = "wss://stream.bybit.com/v5/public/spot"
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0, "reconnects": 0}
        self.max_retries = 5
        self.retry_delay = 5

    async def _test_connectivity(self) -> bool:
        """Test if we can reach Bybit API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.bybit.com/v5/market/time", timeout=10) as response:
                    if response.status == 200:
                        logger.info("✅ Bybit API connectivity test passed")
                        return True
                    else:
                        logger.warning(f"⚠️ Bybit API returned status {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ Bybit API connectivity test failed: {e}")
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
                
                logger.info("✅ Connected to Bybit WebSocket")
                return ws

            except Exception as e:
                logger.error(f"❌ Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error("❌ All connection attempts failed")
                    return None

        return None

    async def _handle_message(self, message: dict, exchange: str = "bybit"):
        """Handle incoming WebSocket message."""
        try:
            if "topic" in message:
                topic = message["topic"]
                data = message.get("data", {})
                
                if "tickers" in topic:
                    await self._handle_ticker(data, exchange)
                elif "publicTrade" in topic:
                    await self._handle_trade(data, exchange)
                elif "orderbook" in topic:
                    await self._handle_orderbook(data, exchange)
                    
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
            self.stats["errors"] += 1

    async def _handle_ticker(self, data: dict, exchange: str):
        """Handle ticker data."""
        try:
            if not isinstance(data, list) or not data:
                return
                
            ticker = data[0]
            symbol = ticker.get("symbol", "")
            if not symbol:
                return

            # Create market data
            market_data = MarketData(
                exchange=exchange,
                symbol=symbol,
                price=float(ticker.get("lastPrice", 0)),
                bid=float(ticker.get("bid1Price", 0)),
                ask=float(ticker.get("ask1Price", 0)),
                bid_size=float(ticker.get("bid1Size", 0)),
                ask_size=float(ticker.get("ask1Size", 0)),
                volume=float(ticker.get("volume24h", 0)),
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
            if not isinstance(data, list) or not data:
                return
                
            trade = data[0]
            symbol = trade.get("s", "")
            if not symbol:
                return

            # Create tick price
            tick_price = TickPrice(
                exchange=exchange,
                symbol=symbol,
                price=float(trade.get("p", 0)),
                volume=float(trade.get("v", 0)),
                timestamp=datetime.fromtimestamp(int(trade.get("T", 0)) / 1000)
            )

            await self.mongo.store_tick_price(tick_price)
            self.stats["stored"] += 1

        except Exception as e:
            logger.error(f"❌ Error handling trade: {e}")
            self.stats["errors"] += 1

    async def _handle_orderbook(self, data: dict, exchange: str):
        """Handle order book data."""
        try:
            if not isinstance(data, list) or not data:
                return
                
            book = data[0]
            symbol = book.get("s", "")
            if not symbol:
                return

            bids = book.get("b", [])
            asks = book.get("a", [])

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
        logger.info("✅ Connected to MongoDB (Bybit Fixed)")

        start_time = time.time()
        last_stats_time = start_time

        while time.time() - start_time < duration_seconds:
            ws = None
            try:
                # Connect with retry
                ws = await self._connect_with_retry()
                if not ws:
                    logger.error("❌ Failed to connect to Bybit WebSocket")
                    break

                # Build subscription args
                args = []
                for sym in self.symbols:
                    args.append(f"tickers.{sym}")
                    args.append(f"publicTrade.{sym}")
                    args.append(f"orderbook.50.{sym}")

                sub_msg = {"op": "subscribe", "args": args}
                await ws.send(json.dumps(sub_msg))
                logger.info(f"📤 Subscribed to: {args}")

                # Start ping task
                async def _ping_loop():
                    while True:
                        try:
                            await ws.send(json.dumps({"op": "ping"}))
                            await asyncio.sleep(20)
                        except:
                            break

                ping_task = asyncio.create_task(_ping_loop())

                # Listen for messages
                async for message in ws:
                    try:
                        data = json.loads(message)
                        
                        # Handle subscription confirmation
                        if "success" in data and data.get("op") == "subscribe":
                            logger.info("✅ Subscription confirmed")
                            continue
                        
                        # Handle data messages
                        await self._handle_message(data)
                        
                        # Log stats every 30 seconds
                        if time.time() - last_stats_time > 30:
                            logger.info(f"📊 Bybit stats: {self.stats}")
                            last_stats_time = time.time()

                    except json.JSONDecodeError as e:
                        logger.error(f"❌ JSON decode error: {e}")
                        self.stats["errors"] += 1
                    except Exception as e:
                        logger.error(f"❌ Message handling error: {e}")
                        self.stats["errors"] += 1

                ping_task.cancel()

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

        logger.info(f"✅ Bybit collection completed. Stats: {self.stats}")


# For backward compatibility
BybitRealtimeCollector = BybitRealtimeCollectorFixed
