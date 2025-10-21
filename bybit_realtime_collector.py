#!/usr/bin/env python3
"""Bybit realtime WebSocket collector (spot) saving in DATA_DEFINITIONS.md schema via SimpleMongoDBCollector."""

import asyncio
import json
import time
from datetime import datetime
from typing import List

from loguru import logger
import websockets

from simple_mongodb_collector import SimpleMongoDBCollector
from models import WebSocketMessage, DataType, MarketData, OrderBookData, TickPrice, VolumeLiquidity


class BybitRealtimeCollector:
    """Collect Bybit realtime market data (spot) and save to Mongo in flattened schema."""

    def __init__(self, symbols: List[str] | None = None):
        # Default to BTC spot pairs focus
        self.symbols = symbols or ["BTCUSDT", "BTCUSDC"]
        self.ws_url = "wss://stream.bybit.com/v5/public/spot"
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0}
        self._debug_seen = 0

    async def collect(self, duration_seconds: int = 90):
        await self.mongo.connect()
        logger.info("✅ Connected to MongoDB (Bybit)")

        try:
            async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10) as ws:
                logger.info("✅ Connected to Bybit WebSocket (spot)")

                # Build args
                args = []
                for sym in self.symbols:
                    args.append(f"tickers.{sym}")
                    args.append(f"publicTrade.{sym}")
                    args.append(f"orderbook.50.{sym}")

                sub_msg = {"op": "subscribe", "args": args}
                await ws.send(json.dumps(sub_msg))
                logger.info(f"📤 Subscribed: {args}")

                # Start ping task
                async def _ping_loop():
                    while True:
                        try:
                            await ws.send(json.dumps({"op": "ping"}))
                        except Exception:
                            return
                        await asyncio.sleep(10)

                ping_task = asyncio.create_task(_ping_loop())

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
            logger.info("✅ Disconnected from MongoDB (Bybit)")
            logger.info(f"Stored={self.stats['stored']} errors={self.stats['errors']}")

    async def _handle_message(self, raw: str):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        # Ignore pings or confirmations
        if isinstance(msg, dict) and msg.get("op") == "subscribe":
            return
        if isinstance(msg, dict) and msg.get("success") is True and msg.get("request"):
            return
        if isinstance(msg, dict) and msg.get("type") in {"snapshot", "delta"} and "topic" in msg:
            # Some Bybit frames include type + topic; fallthrough to topic handling
            pass

        topic = msg.get("topic") if isinstance(msg, dict) else None
        if not topic:
            return

        # Debug first few messages to understand payloads if schema drifts
        if self._debug_seen < 5:
            logger.debug(f"Bybit msg topic={topic} keys={list(msg.keys())} sample={str(msg)[:300]}")
            self._debug_seen += 1

        # topic examples: tickers.BTCUSDT, publicTrade.BTCUSDT, orderbook.25.BTCUSDT
        if topic.startswith("tickers."):
            await self._handle_ticker(msg)
        elif topic.startswith("publicTrade."):
            await self._handle_trades(msg)
        elif topic.startswith("orderbook."):
            await self._handle_orderbook(msg)

    async def _handle_ticker(self, msg: dict):
        try:
            symbol = msg.get("topic", "tickers.").split(".")[-1]
            data = (msg.get("data") or {})
            if isinstance(data, list) and data:
                data = data[0]
            # Bybit v5 tickers returns object (not list)
            # Reference keys: lastPrice, bid1Price, ask1Price, highPrice24h, lowPrice24h, volume24h, turnover24h
            price = float(data.get("lastPrice", 0) or 0)
            bid = float(data.get("bid1Price", 0) or 0)
            ask = float(data.get("ask1Price", 0) or 0)
            volume_24h = float(data.get("volume24h", 0) or 0)
            turnover_24h = float(data.get("turnover24h", 0) or 0)  # Quote asset volume (USDT)
            # Sizes (some streams include bid1Size/ask1Size)
            bid_size = float(data.get("bid1Size", 0) or 0)
            ask_size = float(data.get("ask1Size", 0) or 0)
            high_24h = float(data.get("highPrice24h", 0) or 0)
            low_24h = float(data.get("lowPrice24h", 0) or 0)

            if price <= 0:
                return

            md = MarketData(
                symbol=symbol,
                price=price,
                volume=volume_24h,
                timestamp=datetime.now(),
                exchange="bybit",
                bid=bid or None,
                ask=ask or None,
                bid_size=bid_size or 0.0,
                ask_size=ask_size or 0.0,
                high_24h=high_24h or None,
                low_24h=low_24h or None,
            )

            ws = WebSocketMessage(
                data_type=DataType.MARKET_DATA,
                data=md,
                raw_message={},
                exchange="bybit",
            )
            await self.mongo.store_message(ws)
            self.stats["stored"] += 1
            
            # Store volume/liquidity data
            if volume_24h > 0:
                volume_liquidity_data = VolumeLiquidity(
                    symbol=symbol,
                    volume_24h=volume_24h,  # Base asset volume (BTC)
                    liquidity=turnover_24h,  # Quote asset volume (USDT) as liquidity proxy
                    timestamp=datetime.now(),
                    exchange="bybit"
                )
                
                vl_ws = WebSocketMessage(
                    data_type=DataType.VOLUME_LIQUIDITY,
                    data=volume_liquidity_data,
                    raw_message={},
                    exchange="bybit"
                )
                
                await self.mongo.store_message(vl_ws)
                self.stats["stored"] += 1
                
        except Exception as e:
            logger.error(f"Bybit ticker parse error: {e}")
            self.stats["errors"] += 1

    async def _handle_trades(self, msg: dict):
        try:
            symbol = msg.get("topic", "publicTrade.").split(".")[-1]
            data = msg.get("data") or []
            if isinstance(data, dict):
                # Sometimes wrapped as { list: [...] }
                data = data.get("list") or data.get("trades") or []
            for tr in data:
                # Support both dict and list formats
                if isinstance(tr, dict):
                    price = float(tr.get("p", 0) or 0)
                    qty = float(tr.get("v", 0) or 0)
                    ts_ms = int(tr.get("T", 0) or 0)
                    side_code = (tr.get("S") or "").lower()
                elif isinstance(tr, list) and len(tr) >= 4:
                    price = float(tr[0] or 0)
                    qty = float(tr[1] or 0)
                    ts_ms = int(tr[2] or 0)
                    side_code = str(tr[3]).lower()
                else:
                    continue
                side = "buy" if side_code.startswith("b") else "sell" if side_code.startswith("s") else None
                if price <= 0 or qty <= 0:
                    continue
                tp = TickPrice(
                    symbol=symbol,
                    price=price,
                    volume=qty,
                    timestamp=datetime.fromtimestamp(ts_ms / 1000.0) if ts_ms else datetime.now(),
                    exchange="bybit",
                    side=side,
                )
                ws = WebSocketMessage(
                    data_type=DataType.TICK_PRICES,
                    data=tp,
                    raw_message={},
                    exchange="bybit",
                )
                await self.mongo.store_message(ws)
                self.stats["stored"] += 1
        except Exception as e:
            logger.error(f"Bybit trade parse error: {e}")
            self.stats["errors"] += 1

    async def _handle_orderbook(self, msg: dict):
        try:
            symbol = msg.get("topic", "orderbook.").split(".")[-1]
            data = msg.get("data") or {}
            if isinstance(data, list) and data:
                data = data[0]
            # Data may be snapshot with "b"/"a" arrays or incremental; use current arrays provided
            bids_raw = data.get("b", [])
            asks_raw = data.get("a", [])
            bids = []
            asks = []
            for p, s in bids_raw:
                try:
                    bids.append([float(p), float(s)])
                except Exception:
                    continue
            for p, s in asks_raw:
                try:
                    asks.append([float(p), float(s)])
                except Exception:
                    continue

            if not bids and not asks:
                return

            ob = OrderBookData(
                symbol=symbol,
                bids=bids[:25],
                asks=asks[:25],
                timestamp=datetime.now(),
                exchange="bybit",
            )
            ws = WebSocketMessage(
                data_type=DataType.ORDER_BOOK_DATA,
                data=ob,
                raw_message={},
                exchange="bybit",
            )
            await self.mongo.store_message(ws)
            self.stats["stored"] += 1
        except Exception as e:
            logger.error(f"Bybit orderbook parse error: {e}")
            self.stats["errors"] += 1


async def main():
    collector = BybitRealtimeCollector()
    await collector.collect(duration_seconds=90)


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda m: print(m, end=""),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n",
    )
    asyncio.run(main())


