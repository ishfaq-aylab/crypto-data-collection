#!/usr/bin/env python3
"""Robust Kraken WebSocket Data Collector - Handles all message formats."""

import asyncio
import json
import time
from datetime import datetime
from loguru import logger
import websockets
from simple_mongodb_collector import SimpleMongoDBCollector
from models import WebSocketMessage, DataType, MarketData, OrderBookData, TickPrice, VolumeLiquidity, FundingRate, OpenInterest

class RobustKrakenCollector:
    """Robust Kraken data collector that handles all message formats."""
    
    def __init__(self):
        """Initialize the collector."""
        self.mongodb_collector = SimpleMongoDBCollector()
        self.stats = {
            'total_messages': 0,
            'stored_messages': 0,
            'errors': 0,
            'start_time': None
        }
    
    async def collect_data(self, duration_seconds=120):
        """Collect data from Kraken WebSocket."""
        logger.info("🔌 Starting Robust Kraken Data Collection...")
        logger.info("=" * 50)
        
        # Connect to MongoDB
        try:
            await self.mongodb_collector.connect()
            logger.info("✅ Connected to MongoDB")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MongoDB: {e}")
            return
        
        self.stats['start_time'] = datetime.now()
        
        try:
            async with websockets.connect("wss://ws.kraken.com/", ping_interval=20, ping_timeout=10) as websocket:
                logger.info("✅ Connected to Kraken WebSocket")
                
                # Send subscription for BTC pairs
                subscription = {
                    "event": "subscribe",
                    "pair": ["XBT/USD", "XBT/USDT", "XBT/USDC"],
                    "subscription": {"name": "ticker"}
                }
                
                await websocket.send(json.dumps(subscription))
                logger.info("📤 Sent Kraken ticker subscription for BTC pairs")
                
                # Also subscribe to trades
                trade_subscription = {
                    "event": "subscribe",
                    "pair": ["XBT/USD", "XBT/USDT", "XBT/USDC"],
                    "subscription": {"name": "trade"}
                }
                # Subscribe to order book (depth 25)
                book_subscription = {
                    "event": "subscribe",
                    "pair": ["XBT/USD", "XBT/USDT", "XBT/USDC"],
                    "subscription": {"name": "book", "depth": 25}
                }
                await websocket.send(json.dumps(book_subscription))
                logger.info("📤 Sent Kraken book(25) subscription")

                
                await websocket.send(json.dumps(trade_subscription))
                logger.info("📤 Sent Kraken trade subscription")
                
                start_time = time.time()
                
                while time.time() - start_time < duration_seconds:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        await self._handle_kraken_message(message)
                        
                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        logger.error(f"❌ Error receiving message: {e}")
                        self.stats['errors'] += 1
                        
        except Exception as e:
            logger.error(f"❌ Kraken WebSocket connection failed: {e}")
            self.stats['errors'] += 1
        
        # Disconnect from MongoDB
        try:
            await self.mongodb_collector.disconnect()
            logger.info("✅ Disconnected from MongoDB")
        except Exception as e:
            logger.error(f"❌ Error disconnecting from MongoDB: {e}")
        
        # Final statistics
        self._log_final_stats(duration_seconds)
    
    async def _handle_kraken_message(self, message):
        """Handle incoming Kraken WebSocket messages - ROBUST VERSION."""
        try:
            data = json.loads(message)
            
            # Handle system messages
            if isinstance(data, dict):
                if data.get('event') == 'systemStatus':
                    logger.info(f"📊 Kraken system status: {data.get('status')}")
                    return
                
                if data.get('event') == 'heartbeat':
                    logger.debug("💓 Kraken heartbeat received")
                    return
                
                if data.get('event') == 'subscriptionStatus':
                    status = data.get('status')
                    pair = data.get('pair', 'unknown')
                    subscription = data.get('subscription', {})
                    logger.info(f"📊 Kraken subscription: {status} for {pair} - {subscription.get('name', 'unknown')}")
                    return
            
            # Handle data messages (list format)
            if isinstance(data, list) and len(data) >= 4:
                try:
                    channel_id = data[0]
                    channel_data = data[1]  # This should be the actual ticker data
                    channel_name = data[2]
                    pair = data[3]
                    
                    logger.debug(f"📊 Kraken data: {channel_name} for {pair}")
                    
                    if channel_name == 'ticker' and isinstance(channel_data, dict):
                        await self._handle_ticker_data(pair, channel_data)
                    elif channel_name == 'trade' and isinstance(channel_data, list):
                        await self._handle_trade_data(pair, channel_data)
                    elif channel_name == 'book-25' and isinstance(channel_data, dict):
                        await self._handle_book_data(pair, channel_data)
                    else:
                        logger.debug(f"📊 Unhandled Kraken channel: {channel_name} with data type: {type(channel_data)}")
                except Exception as e:
                    logger.error(f"❌ Error processing list data: {e}")
                    self.stats['errors'] += 1
            
            # Handle other list formats (might be different data types)
            elif isinstance(data, list):
                logger.debug(f"📊 Received list message with {len(data)} elements: {data}")
                # Try to handle as ticker data if it looks like it
                if len(data) >= 2 and isinstance(data[1], dict):
                    # This might be ticker data in a different format
                    try:
                        pair = "UNKNOWN"
                        if len(data) > 3:
                            pair = data[3]
                        await self._handle_ticker_data(pair, data[1])
                    except Exception as e:
                        logger.debug(f"📊 Could not process as ticker data: {e}")
            
        except json.JSONDecodeError:
            logger.warning(f"Received non-JSON message from Kraken: {message}")
        except Exception as e:
            logger.error(f"❌ Error handling Kraken message: {e}")
            self.stats['errors'] += 1
    
    async def _handle_ticker_data(self, pair, data):
        """Handle Kraken ticker data - ROBUST VERSION."""
        try:
            if not isinstance(data, dict):
                logger.warning(f"Invalid ticker data format for {pair}: {data}")
                return
            
            # Extract price (last trade closed price)
            price = 0
            if 'c' in data and data['c'] and len(data['c']) > 0:
                price = float(data['c'][0])
            
            # Extract volume (24h volume)
            volume = 0
            if 'v' in data and data['v'] and len(data['v']) > 1:
                volume = float(data['v'][1])  # 24h volume
            
            # Extract bid price
            bid = 0
            if 'b' in data and data['b'] and len(data['b']) > 0:
                bid = float(data['b'][0])
            
            # Extract ask price
            ask = 0
            if 'a' in data and data['a'] and len(data['a']) > 0:
                ask = float(data['a'][0])
            
            # Extract bid/ask sizes (Kraken provides whole lot and lot volume). Use lot volume (index 2).
            bid_size = None
            try:
                if 'b' in data and data['b'] and len(data['b']) > 2:
                    bid_size = float(data['b'][2])
            except Exception:
                bid_size = None
            ask_size = None
            try:
                if 'a' in data and data['a'] and len(data['a']) > 2:
                    ask_size = float(data['a'][2])
            except Exception:
                ask_size = None

            # Extract 24h high
            high_24h = 0
            if 'h' in data and data['h'] and len(data['h']) > 1:
                high_24h = float(data['h'][1])
            
            # Extract 24h low
            low_24h = 0
            if 'l' in data and data['l'] and len(data['l']) > 1:
                low_24h = float(data['l'][1])
            
            # Extract volume/liquidity data
            volume_24h = 0
            vwap_24h = 0
            trade_count_24h = 0
            
            if 'v' in data and data['v'] and len(data['v']) > 1:
                volume_24h = float(data['v'][1])  # 24h volume (base asset)
            
            if 'p' in data and data['p'] and len(data['p']) > 1:
                vwap_24h = float(data['p'][1])  # 24h VWAP (for liquidity calculation)
            
            if 't' in data and data['t'] and len(data['t']) > 1:
                trade_count_24h = int(data['t'][1])  # 24h trade count
            
            # Calculate liquidity as volume * VWAP (quote asset volume)
            liquidity = volume_24h * vwap_24h if vwap_24h > 0 else 0
            
            # Only create market data if we have a valid price
            if price > 0:
                market_data = MarketData(
                    symbol=pair,
                    price=price,
                    volume=volume,
                    timestamp=datetime.now(),
                    exchange="kraken",
                    bid=bid,
                    ask=ask,
                    bid_size=bid_size,
                    ask_size=ask_size,
                    high_24h=high_24h,
                    low_24h=low_24h
                )
                
                ws_message = WebSocketMessage(
                    data_type=DataType.MARKET_DATA,
                    data=market_data,
                    raw_message={},
                    exchange="kraken"
                )
                
                await self.mongodb_collector.store_message(ws_message)
                self._update_stats("market_data")
                
                # Store volume/liquidity data
                if volume_24h > 0:
                    volume_liquidity_data = VolumeLiquidity(
                        symbol=pair,
                        volume_24h=volume_24h,  # Base asset volume (BTC)
                        liquidity=liquidity,    # Quote asset volume (USD) as liquidity proxy
                        timestamp=datetime.now(),
                        exchange="kraken"
                    )
                    
                    vl_ws_message = WebSocketMessage(
                        data_type=DataType.VOLUME_LIQUIDITY,
                        data=volume_liquidity_data,
                        raw_message={},
                        exchange="kraken"
                    )
                    
                    await self.mongodb_collector.store_message(vl_ws_message)
                    self._update_stats("volume_liquidity")
                
                logger.info(f"📊 Kraken TICKER: {pair} - Price: {price}, Volume: {volume}, Volume24h: {volume_24h}, Liquidity: {liquidity}")
            else:
                logger.debug(f"📊 Kraken ticker data for {pair} has no valid price: {data}")
            
        except Exception as e:
            logger.error(f"❌ Error handling ticker data: {e}")
            self.stats['errors'] += 1
    
    async def _handle_trade_data(self, pair, data):
        """Handle Kraken trade data."""
        try:
            if not isinstance(data, list):
                logger.warning(f"Invalid trade data format for {pair}: {data}")
                return
            
            for trade in data:
                if isinstance(trade, list) and len(trade) >= 4:
                    price = float(trade[0])
                    volume = float(trade[1])
                    timestamp = float(trade[2])
                    side_code = str(trade[3]).lower()
                    side = 'buy' if side_code.startswith('b') else 'sell' if side_code.startswith('s') else None
                    
                    trade_data = TickPrice(
                        symbol=pair,
                        price=price,
                        volume=volume,
                        timestamp=datetime.fromtimestamp(timestamp),
                        exchange="kraken",
                        side=side
                    )
                    
                    ws_message = WebSocketMessage(
                        data_type=DataType.TICK_PRICES,
                        data=trade_data,
                        raw_message={},
                        exchange="kraken"
                    )
                    
                    await self.mongodb_collector.store_message(ws_message)
                    self._update_stats("tick_prices")
                    
                    logger.info(f"💹 Kraken TRADE: {pair} - Price: {price}, Volume: {volume}")
            
        except Exception as e:
            logger.error(f"❌ Error handling trade data: {e}")
            self.stats['errors'] += 1

    async def _handle_book_data(self, pair, data):
        """Handle Kraken order book data (level updates and snapshots)."""
        try:
            # Kraken book messages can include 'as' (asks snapshot), 'bs' (bids snapshot), and/or 'a'/'b' updates
            bids = []
            asks = []

            if 'bs' in data:
                # Snapshot bids: [ [price, volume, timestamp], ... ]
                for lvl in data['bs']:
                    try:
                        bids.append([float(lvl[0]), float(lvl[1])])
                    except Exception:
                        continue
            if 'as' in data:
                for lvl in data['as']:
                    try:
                        asks.append([float(lvl[0]), float(lvl[1])])
                    except Exception:
                        continue

            # For updates 'b' and 'a', we record the latest snapshot-style arrays for simplicity
            if 'b' in data:
                for lvl in data['b']:
                    try:
                        bids.append([float(lvl[0]), float(lvl[1])])
                    except Exception:
                        continue
            if 'a' in data:
                for lvl in data['a']:
                    try:
                        asks.append([float(lvl[0]), float(lvl[1])])
                    except Exception:
                        continue

            # Truncate to depth 25 if needed
            bids = bids[:25]
            asks = asks[:25]

            if not bids and not asks:
                return

            ob = OrderBookData(
                symbol=pair,
                bids=bids,
                asks=asks,
                timestamp=datetime.now(),
                exchange="kraken"
            )

            ws_message = WebSocketMessage(
                data_type=DataType.ORDER_BOOK_DATA,
                data=ob,
                raw_message={},
                exchange="kraken"
            )
            await self.mongodb_collector.store_message(ws_message)
            self._update_stats("order_book_data")
            logger.debug(f"📘 Kraken BOOK: {pair} bids={len(bids)} asks={len(asks)}")
        except Exception as e:
            logger.error(f"❌ Error handling book data: {e}")
            self.stats['errors'] += 1
    
    def _update_stats(self, data_type):
        """Update statistics."""
        self.stats['total_messages'] += 1
        self.stats['stored_messages'] += 1
    
    def _log_final_stats(self, duration_seconds):
        """Log final collection statistics."""
        logger.info(f"\n📊 KRAKEN COLLECTION STATISTICS")
        logger.info("=" * 50)
        logger.info(f"Collection duration: {duration_seconds:.1f}s")
        logger.info(f"Total messages collected: {self.stats['total_messages']}")
        logger.info(f"Messages stored in DB: {self.stats['stored_messages']}")
        logger.info(f"Average messages/sec: {self.stats['total_messages'] / duration_seconds:.1f}")
        logger.info(f"Storage success rate: {(self.stats['stored_messages'] / self.stats['total_messages'] * 100) if self.stats['total_messages'] > 0 else 0:.1f}%")
        logger.info(f"Total errors: {self.stats['errors']}")

async def main():
    """Main function."""
    collector = RobustKrakenCollector()
    
    # Collect data for 2 minutes
    await collector.collect_data(duration_seconds=120)

if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>\n"
    )
    
    # Run the collector
    asyncio.run(main())
