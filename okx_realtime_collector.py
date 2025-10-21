#!/usr/bin/env python3
"""OKX realtime public WebSocket collector (spot) saving in DATA_DEFINITIONS schema."""

import asyncio
import json
import time
from datetime import datetime
from typing import List

from loguru import logger
import websockets

from simple_mongodb_collector import SimpleMongoDBCollector
from models import WebSocketMessage, DataType, MarketData, OrderBookData, TickPrice, VolumeLiquidity


class OKXRealtimeCollector:
    """Collect OKX realtime spot data (BTC-USDT/BTC-USDC) and store in Mongo."""

    def __init__(self, inst_ids: List[str] | None = None):
        # OKX spot instrument ids: BTC-USDT, BTC-USDC
        self.inst_ids = inst_ids or ["BTC-USDT", "BTC-USDC"]
        self.ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0}

    async def collect(self, duration_seconds: int = 90):
        await self.mongo.connect()
        logger.info("✅ Connected to MongoDB (OKX)")

        try:
            async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10) as ws:
                logger.info("✅ Connected to OKX WebSocket (public)")

                # Subscribe to tickers, trades, and books5
                args = []
                for inst in self.inst_ids:
                    args.append({"channel": "tickers", "instId": inst})
                    args.append({"channel": "trades", "instId": inst})
                    args.append({"channel": "books5", "instId": inst})

                sub_msg = {"op": "subscribe", "args": args}
                await ws.send(json.dumps(sub_msg))
                logger.info(f"📤 Subscribed OKX: {args}")

                # Ping loop
                async def _ping_loop():
                    while True:
                        try:
                            await ws.send("ping")
                        except Exception:
                            return
                        await asyncio.sleep(10)

                asyncio.create_task(_ping_loop())

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
            logger.info("✅ Disconnected from MongoDB (OKX)")
            logger.info(f"Stored={self.stats['stored']} errors={self.stats['errors']}")

    async def _handle_message(self, raw: str):
        if raw == "pong":
            return
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        if not isinstance(msg, dict):
            return
        if msg.get("event") in {"subscribe", "error"}:
            return

        arg = msg.get("arg") or {}
        channel = arg.get("channel")
        data = msg.get("data") or []
        if not channel or not data:
            return

        if channel == "tickers":
            await self._handle_tickers(arg, data)
        elif channel == "trades":
            await self._handle_trades(arg, data)
        elif channel == "books5":
            await self._handle_books(arg, data)

    async def _handle_tickers(self, arg: dict, data_list: list):
        inst_id = arg.get("instId")
        for d in data_list:
            try:
                last = float(d.get("last", 0) or 0)
                bid = float(d.get("bidPx", 0) or 0)
                ask = float(d.get("askPx", 0) or 0)
                vol24 = float(d.get("vol24h", 0) or 0)
                vol_ccy_24h = float(d.get("volCcy24h", 0) or 0)  # Quote asset volume (USDT)
                high24 = float(d.get("high24h", 0) or 0)
                low24 = float(d.get("low24h", 0) or 0)
                if last <= 0:
                    continue
                md = MarketData(
                    symbol=inst_id,
                    price=last,
                    volume=vol24,
                    timestamp=datetime.now(),
                    exchange="okx",
                    bid=bid or None,
                    ask=ask or None,
                    bid_size=0.0,
                    ask_size=0.0,
                    high_24h=high24 or None,
                    low_24h=low24 or None,
                )
                ws = WebSocketMessage(
                    data_type=DataType.MARKET_DATA,
                    data=md,
                    raw_message={},
                    exchange="okx",
                )
                await self.mongo.store_message(ws)
                self.stats["stored"] += 1
                
                # Store volume/liquidity data
                if vol24 > 0:
                    volume_liquidity_data = VolumeLiquidity(
                        symbol=inst_id,
                        volume_24h=vol24,  # Base asset volume (BTC)
                        liquidity=vol_ccy_24h,  # Quote asset volume (USDT) as liquidity proxy
                        timestamp=datetime.now(),
                        exchange="okx"
                    )
                    
                    vl_ws = WebSocketMessage(
                        data_type=DataType.VOLUME_LIQUIDITY,
                        data=volume_liquidity_data,
                        raw_message={},
                        exchange="okx"
                    )
                    
                    await self.mongo.store_message(vl_ws)
                    self.stats["stored"] += 1
                    
            except Exception as e:
                logger.error(f"OKX ticker parse error: {e}")
                self.stats["errors"] += 1

    async def _handle_trades(self, arg: dict, data_list: list):
        inst_id = arg.get("instId")
        for d in data_list:
            try:
                price = float(d.get("px", 0) or 0)
                sz = float(d.get("sz", 0) or 0)
                side_code = str(d.get("side") or "").lower()
                side = "buy" if side_code.startswith("b") else "sell" if side_code.startswith("s") else None
                ts_ms = int(d.get("ts", 0) or 0)
                if price <= 0 or sz <= 0:
                    continue
                tp = TickPrice(
                    symbol=inst_id,
                    price=price,
                    volume=sz,
                    timestamp=datetime.fromtimestamp(ts_ms / 1000.0) if ts_ms else datetime.now(),
                    exchange="okx",
                    side=side,
                )
                ws = WebSocketMessage(
                    data_type=DataType.TICK_PRICES,
                    data=tp,
                    raw_message={},
                    exchange="okx",
                )
                await self.mongo.store_message(ws)
                self.stats["stored"] += 1
            except Exception as e:
                logger.error(f"OKX trade parse error: {e}")
                self.stats["errors"] += 1

    async def _handle_books(self, arg: dict, data_list: list):
        inst_id = arg.get("instId")
        for d in data_list:
            try:
                bids = []
                asks = []
                for lvl in d.get("bids", []):
                    try:
                        bids.append([float(lvl[0]), float(lvl[1])])
                    except Exception:
                        continue
                for lvl in d.get("asks", []):
                    try:
                        asks.append([float(lvl[0]), float(lvl[1])])
                    except Exception:
                        continue
                if not bids and not asks:
                    continue
                ob = OrderBookData(
                    symbol=inst_id,
                    bids=bids[:5],
                    asks=asks[:5],
                    timestamp=datetime.now(),
                    exchange="okx",
                )
                ws = WebSocketMessage(
                    data_type=DataType.ORDER_BOOK_DATA,
                    data=ob,
                    raw_message={},
                    exchange="okx",
                )
                await self.mongo.store_message(ws)
                self.stats["stored"] += 1
            except Exception as e:
                logger.error(f"OKX books parse error: {e}")
                self.stats["errors"] += 1


async def main():
    collector = OKXRealtimeCollector()
    await collector.collect(duration_seconds=90)


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda m: print(m, end=""),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n",
    )
    asyncio.run(main())


