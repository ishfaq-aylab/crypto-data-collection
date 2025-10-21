#!/usr/bin/env python3
"""Binance realtime WebSocket collector (spot) saving in DATA_DEFINITIONS schema."""

import asyncio
import json
import time
from datetime import datetime
from typing import List

from loguru import logger
import websockets

from simple_mongodb_collector import SimpleMongoDBCollector
from models import WebSocketMessage, DataType, MarketData, OrderBookData, TickPrice, VolumeLiquidity


class BinanceRealtimeCollector:
    """Collect Binance spot data for BTCUSDT/BTCUSDC and store in Mongo."""

    def __init__(self, symbols: List[str] | None = None):
        self.symbols = symbols or ["BTCUSDT", "BTCUSDC"]
        self.ws_url = "wss://stream.binance.com:9443/ws"
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0}

    def _build_params(self) -> List[str]:
        params: List[str] = []
        for s in self.symbols:
            lower = s.lower()
            params.append(f"{lower}@ticker")          # 24hr ticker
            params.append(f"{lower}@trade")           # trades
            params.append(f"{lower}@depth20@100ms")   # order book depth 20
        return params

    async def collect(self, duration_seconds: int = 90):
        await self.mongo.connect()
        logger.info("✅ Connected to MongoDB (Binance)")

        try:
            async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10) as ws:
                logger.info("✅ Connected to Binance WebSocket (spot)")

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
            logger.info("✅ Disconnected from MongoDB (Binance)")
            logger.info(f"Stored={self.stats['stored']} errors={self.stats['errors']}")

    async def _handle_message(self, raw: str):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        if not isinstance(msg, dict):
            return

        # Ignore subscription acks
        if msg.get("result") is None and msg.get("id") is not None and not msg.get("e") and not msg.get("stream"):
            return

        # Combined streams could be used; here we subscribed per-connection params, so payload is single event
        if msg.get("e") == "24hrTicker":
            await self._handle_ticker(msg)
        elif msg.get("e") == "trade":
            await self._handle_trade(msg)
        elif msg.get("e") in ("depthUpdate",) or ("bids" in msg and "asks" in msg):
            await self._handle_depth(msg)

    async def _handle_ticker(self, m: dict):
        try:
            symbol = m.get("s")
            price = float(m.get("c", 0) or 0)  # last price
            vol24 = float(m.get("v", 0) or 0)  # base asset volume
            quote_vol24 = float(m.get("q", 0) or 0)  # quote asset volume
            bid = float(m.get("b", 0) or 0)
            ask = float(m.get("a", 0) or 0)
            bid_size = float(m.get("B", 0) or 0)  # bid size
            ask_size = float(m.get("A", 0) or 0)  # ask size
            high24 = float(m.get("h", 0) or 0)
            low24 = float(m.get("l", 0) or 0)
            
            if not symbol or price <= 0:
                return
            
            # Store market data (ticker)
            md = MarketData(
                symbol=symbol,
                price=price,
                volume=vol24,
                timestamp=datetime.now(),
                exchange="binance",
                bid=bid or None,
                ask=ask or None,
                bid_size=bid_size,
                ask_size=ask_size,
                high_24h=high24 or None,
                low_24h=low24 or None,
            )
            ws = WebSocketMessage(
                data_type=DataType.MARKET_DATA,
                data=md,
                raw_message={},
                exchange="binance",
            )
            await self.mongo.store_message(ws)
            self.stats["stored"] += 1
            
            # Calculate spread in basis points
            spread_bps = 0.0
            if bid > 0 and ask > 0:
                spread_bps = ((ask - bid) / bid) * 10000  # Convert to basis points
            
            # Store volume/liquidity data
            vl = VolumeLiquidity(
                symbol=symbol,
                volume_24h=vol24,  # Base asset volume (BTC)
                liquidity=quote_vol24,  # Quote asset volume (USDT) as liquidity proxy
                timestamp=datetime.now(),
                exchange="binance",
            )
            ws_vl = WebSocketMessage(
                data_type=DataType.VOLUME_LIQUIDITY,
                data=vl,
                raw_message={},
                exchange="binance",
            )
            await self.mongo.store_message(ws_vl)
            self.stats["stored"] += 1
            
        except Exception as e:
            logger.error(f"Binance ticker parse error: {e}")
            self.stats["errors"] += 1

    async def _handle_trade(self, m: dict):
        try:
            symbol = m.get("s")
            price = float(m.get("p", 0) or 0)
            qty = float(m.get("q", 0) or 0)
            buyer_maker = bool(m.get("m", False))
            side = "sell" if buyer_maker else "buy"  # Binance: m=true means the buyer is the market maker -> sell trade from taker
            ts_ms = int(m.get("T", 0) or 0)
            if not symbol or price <= 0 or qty <= 0:
                return
            tp = TickPrice(
                symbol=symbol,
                price=price,
                volume=qty,
                timestamp=datetime.fromtimestamp(ts_ms / 1000.0) if ts_ms else datetime.now(),
                exchange="binance",
                side=side,
            )
            ws = WebSocketMessage(
                data_type=DataType.TICK_PRICES,
                data=tp,
                raw_message={},
                exchange="binance",
            )
            await self.mongo.store_message(ws)
            self.stats["stored"] += 1
        except Exception as e:
            logger.error(f"Binance trade parse error: {e}")
            self.stats["errors"] += 1

    async def _handle_depth(self, m: dict):
        try:
            # Handle both wrapped and direct depth updates
            symbol = m.get("s")  # For wrapped updates
            bids_raw = m.get("b", []) or m.get("bids", [])  # Support both formats
            asks_raw = m.get("a", []) or m.get("asks", [])  # Support both formats
            
            # If no symbol in message, try to determine from context
            if not symbol:
                # For direct depth updates, we need to determine symbol from subscription
                # Since we're subscribing to specific symbols, we can use the first one
                symbol = "BTCUSDT"  # Default for now, could be enhanced to track multiple symbols
            
            bids = []
            asks = []
            for p, q in bids_raw:
                try:
                    bids.append([float(p), float(q)])
                except Exception:
                    continue
            for p, q in asks_raw:
                try:
                    asks.append([float(p), float(q)])
                except Exception:
                    continue
            if not symbol or (not bids and not asks):
                return
            ob = OrderBookData(
                symbol=symbol,
                bids=bids[:20],
                asks=asks[:20],
                timestamp=datetime.now(),
                exchange="binance",
            )
            ws = WebSocketMessage(
                data_type=DataType.ORDER_BOOK_DATA,
                data=ob,
                raw_message={},
                exchange="binance",
            )
            await self.mongo.store_message(ws)
            self.stats["stored"] += 1
        except Exception as e:
            logger.error(f"Binance depth parse error: {e}")
            self.stats["errors"] += 1


async def main():
    collector = BinanceRealtimeCollector()
    await collector.collect(duration_seconds=90)


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda m: print(m, end=""),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n",
    )
    asyncio.run(main())


