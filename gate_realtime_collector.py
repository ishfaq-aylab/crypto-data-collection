#!/usr/bin/env python3
"""Gate.io realtime WebSocket collector (spot) saving in DATA_DEFINITIONS schema."""

import asyncio
import json
import time
from datetime import datetime
from typing import List

from loguru import logger
import websockets

from simple_mongodb_collector import SimpleMongoDBCollector
from models import WebSocketMessage, DataType, MarketData, OrderBookData, TickPrice, VolumeLiquidity


class GateRealtimeCollector:
    """Collect Gate.io realtime spot data for BTC USDT/USDC and store in Mongo."""

    def __init__(self, pairs: List[str] | None = None):
        # Gate spot pairs format: BTC_USDT, BTC_USDC
        self.pairs = pairs or ["BTC_USDT", "BTC_USDC"]
        self.ws_url = "wss://api.gateio.ws/ws/v4/"
        self.mongo = SimpleMongoDBCollector()
        self.stats = {"stored": 0, "errors": 0}

    async def collect(self, duration_seconds: int = 90):
        await self.mongo.connect()
        logger.info("✅ Connected to MongoDB (Gate.io)")

        try:
            async with websockets.connect(self.ws_url, ping_interval=20, ping_timeout=10) as ws:
                logger.info("✅ Connected to Gate.io WebSocket (spot)")

                # Subscribe: spot.tickers, spot.trades, spot.order_book_update (depth 20) per pair
                await self._subscribe(ws, "spot.tickers", self.pairs)
                await self._subscribe(ws, "spot.trades", self.pairs)
                await self._subscribe(ws, "spot.order_book", [[p, "20", "100ms"] for p in self.pairs])  # depth 20, 100ms interval

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
            logger.info("✅ Disconnected from MongoDB (Gate.io)")
            logger.info(f"Stored={self.stats['stored']} errors={self.stats['errors']}")

    async def _subscribe(self, ws, channel: str, payloads):
        msg = {
            "time": int(time.time()),
            "channel": channel,
            "event": "subscribe",
            "payload": payloads,
        }
        await ws.send(json.dumps(msg))
        logger.info(f"📤 Subscribed {channel}: {payloads}")

    async def _handle_message(self, raw: str):
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            return

        if not isinstance(msg, dict):
            return

        # Heartbeats / pings
        if msg.get("event") in {"subscribe", "update"} and not msg.get("result") and not msg.get("time_ms"):
            # ignore simple acks
            pass

        channel = msg.get("channel")
        event = msg.get("event")
        result = msg.get("result")
        if not channel or not result:
            return

        if channel == "spot.tickers" and event in {"update"}:
            await self._handle_ticker(result)
        elif channel == "spot.trades" and event in {"update"}:
            await self._handle_trades(result)
        elif channel == "spot.order_book" and event in {"update", "snapshot"}:
            await self._handle_orderbook(result)

    async def _handle_ticker(self, result):
        # result is a list of ticker objects
        for t in result if isinstance(result, list) else [result]:
            try:
                pair = t.get("currency_pair")
                last = float(t.get("last", 0) or 0)
                bid = float(t.get("highest_bid", 0) or 0)
                ask = float(t.get("lowest_ask", 0) or 0)
                vol24 = float(t.get("base_volume", 0) or 0)
                quote_vol24 = float(t.get("quote_volume", 0) or 0)
                high24 = float(t.get("high_24h", 0) or 0)
                low24 = float(t.get("low_24h", 0) or 0)
                
                if last <= 0 or not pair:
                    continue
                
                # Store market data (ticker)
                md = MarketData(
                    symbol=pair,
                    price=last,
                    volume=vol24,
                    timestamp=datetime.now(),
                    exchange="gate",
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
                    exchange="gate",
                )
                await self.mongo.store_message(ws)
                self.stats["stored"] += 1
                
                # Store volume/liquidity data
                # Use quote_volume as liquidity metric (USDT volume)
                vl = VolumeLiquidity(
                    symbol=pair,
                    volume_24h=vol24,  # Base asset volume (BTC)
                    liquidity=quote_vol24,  # Quote asset volume (USDT) as liquidity proxy
                    timestamp=datetime.now(),
                    exchange="gate",
                )
                ws_vl = WebSocketMessage(
                    data_type=DataType.VOLUME_LIQUIDITY,
                    data=vl,
                    raw_message={},
                    exchange="gate",
                )
                await self.mongo.store_message(ws_vl)
                self.stats["stored"] += 1
                
            except Exception as e:
                logger.error(f"Gate ticker parse error: {e}")
                self.stats["errors"] += 1

    async def _handle_trades(self, result):
        # result is list of trade objects
        for tr in result if isinstance(result, list) else [result]:
            try:
                pair = tr.get("currency_pair")
                price = float(tr.get("price", 0) or 0)
                amount = float(tr.get("amount", 0) or 0)
                side_code = str(tr.get("side") or "").lower()
                side = "buy" if side_code.startswith("b") else "sell" if side_code.startswith("s") else None
                ts_ms = int(float(tr.get("create_time_ms", 0) or 0))
                if price <= 0 or amount <= 0 or not pair:
                    continue
                tp = TickPrice(
                    symbol=pair,
                    price=price,
                    volume=amount,
                    timestamp=datetime.fromtimestamp(ts_ms / 1000.0) if ts_ms else datetime.now(),
                    exchange="gate",
                    side=side,
                )
                ws = WebSocketMessage(
                    data_type=DataType.TICK_PRICES,
                    data=tp,
                    raw_message={},
                    exchange="gate",
                )
                await self.mongo.store_message(ws)
                self.stats["stored"] += 1
            except Exception as e:
                logger.error(f"Gate trade parse error: {e}")
                self.stats["errors"] += 1

    async def _handle_orderbook(self, result):
        # result is object with bids/asks arrays
        try:
            data = result if isinstance(result, dict) else {}
            pair = data.get("s")  # symbol field
            bids_raw = data.get("bids", [])
            asks_raw = data.get("asks", [])
            bids = []
            asks = []
            
            # Parse bids: [["price", "size"], ...]
            for lvl in bids_raw:
                try:
                    p = float(lvl[0])
                    s = float(lvl[1])
                    bids.append([p, s])
                except Exception:
                    continue
                    
            # Parse asks: [["price", "size"], ...]
            for lvl in asks_raw:
                try:
                    p = float(lvl[0])
                    s = float(lvl[1])
                    asks.append([p, s])
                except Exception:
                    continue
                    
            if not pair or (not bids and not asks):
                return
                
            ob = OrderBookData(
                symbol=pair,
                bids=bids[:20],
                asks=asks[:20],
                timestamp=datetime.now(),
                exchange="gate",
            )
            ws = WebSocketMessage(
                data_type=DataType.ORDER_BOOK_DATA,
                data=ob,
                raw_message={},
                exchange="gate",
            )
            await self.mongo.store_message(ws)
            self.stats["stored"] += 1
        except Exception as e:
            logger.error(f"Gate orderbook parse error: {e}")
            self.stats["errors"] += 1


async def main():
    collector = GateRealtimeCollector()
    await collector.collect(duration_seconds=90)


if __name__ == "__main__":
    logger.remove()
    logger.add(
        lambda m: print(m, end=""),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n",
    )
    asyncio.run(main())


