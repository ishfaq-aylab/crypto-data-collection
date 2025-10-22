#!/usr/bin/env python3
"""Fixed OKX realtime WebSocket collector with better error handling and retry logic."""

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


class OKXRealtimeCollectorFixed:
    """Fixed OKX realtime collector with better error handling."""

    def __init__(self, inst_ids: List[str] | None = None):
        self.inst_ids = inst_ids or ["BTC-USDT", "BTC-USDC"]
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0, "reconnects": 0}
        self.max_retries = 5
        self.retry_delay = 5

    async def _test_connectivity(self) -> bool:
        """Test if we can reach OKX API."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://www.okx.com/api/v5/public/time", timeout=10) as response:
                    if response.status == 200:
                        logger.info("✅ OKX API connectivity test passed")
                        return True
                    else:
                        logger.warning(f"⚠️ OKX API returned status {response.status}")
                        return False
        except Exception as e:
            logger.error(f"❌ OKX API connectivity test failed: {e}")
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
                
                logger.info("✅ Connected to OKX WebSocket")
                return ws

            except Exception as e:
                logger.error(f"❌ Connection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    logger.error("❌ All connection attempts failed")
                    return None

        return None

    async def _handle_message(self, message: dict, exchange: str = "okx"):
        """Handle incoming WebSocket message."""
        try:
            if "arg" in message:
                arg = message["arg"]
                data = message.get("data", [])
                
                if arg.get("channel") == "tickers":
                    await self._handle_ticker(data, exchange)
                elif arg.get("channel") == "trades":
                    await self._handle_trade(data, exchange)
                elif arg.get("channel") == "books5":
                    await self._handle_orderbook(data, exchange)
                    
        except Exception as e:
            logger.error(f"❌ Error handling message: {e}")
            self.stats["errors"] += 1

    async def _handle_ticker(self, data: list, exchange: str):
        """Handle ticker data."""
        try:
            if not data:
                return
                
            ticker = data[0]
            inst_id = ticker.get("instId", "")
            if not inst_id:
                return

            # Create market data
            market_data = MarketData(
                exchange=exchange,
                symbol=inst_id,
                price=float(ticker.get("last", 0)),
                bid=float(ticker.get("bidPx", 0)),
                ask=float(ticker.get("askPx", 0)),
                bid_size=float(ticker.get("bidSz", 0)),
                ask_size=float(ticker.get("askSz", 0)),
                volume=float(ticker.get("vol24h", 0)),
                timestamp=datetime.now()
            )

            await self.mongo.store_market_data(market_data)
            self.stats["stored"] += 1

        except Exception as e:
            logger.error(f"❌ Error handling ticker: {e}")
            self.stats["errors"] += 1

    async def _handle_trade(self, data: list, exchange: str):
        """Handle trade data."""
        try:
            if not data:
                return
                
            trade = data[0]
            inst_id = trade.get("instId", "")
            if not inst_id:
                return

            # Create tick price
            tick_price = TickPrice(
                exchange=exchange,
                symbol=inst_id,
                price=float(trade.get("px", 0)),
                quantity=float(trade.get("sz", 0)),
                timestamp=datetime.fromtimestamp(int(trade.get("ts", 0)) / 1000)
            )

            await self.mongo.store_tick_price(tick_price)
            self.stats["stored"] += 1

        except Exception as e:
            logger.error(f"❌ Error handling trade: {e}")
            self.stats["errors"] += 1

    async def _handle_orderbook(self, data: list, exchange: str):
        """Handle order book data."""
        try:
            if not data:
                return
                
            book = data[0]
            inst_id = book.get("instId", "")
            if not inst_id:
                return

            bids = book.get("bids", [])
            asks = book.get("asks", [])

            if not bids or not asks:
                return

            # Create order book data
            order_book = OrderBookData(
                exchange=exchange,
                symbol=inst_id,
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
        logger.info("✅ Connected to MongoDB (OKX Fixed)")

        start_time = time.time()
        last_stats_time = start_time

        while time.time() - start_time < duration_seconds:
            ws = None
            try:
                # Connect with retry
                ws = await self._connect_with_retry()
                if not ws:
                    logger.error("❌ Failed to connect to OKX WebSocket")
                    break

                # Subscribe to channels
                args = []
                for inst in self.inst_ids:
                    args.append({"channel": "tickers", "instId": inst})
                    args.append({"channel": "trades", "instId": inst})
                    args.append({"channel": "books5", "instId": inst})

                sub_msg = {"op": "subscribe", "args": args}
                await ws.send(json.dumps(sub_msg))
                logger.info(f"📤 Subscribed to: {args}")

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
                            logger.info(f"📊 OKX stats: {self.stats}")
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

        logger.info(f"✅ OKX collection completed. Stats: {self.stats}")


# For backward compatibility
OKXRealtimeCollector = OKXRealtimeCollectorFixed
