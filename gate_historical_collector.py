#!/usr/bin/env python3
"""Gate.io historical data collector for OHLCV and trades data."""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger

from models import HistoricalData, HistoricalTrade, WebSocketMessage, DataType
from simple_mongodb_collector import SimpleMongoDBCollector

class GateHistoricalCollector:
    """Collects historical data from Gate.io REST API."""
    
    def __init__(self, symbols: List[str] = None):
        self.exchange = "gate"
        self.symbols = symbols or ["BTC_USDT", "ETH_USDT", "ADA_USDT", "SOL_USDT", "DOT_USDT"]
        self.base_url = "https://api.gateio.ws/api/v4"
        self.mongo = SimpleMongoDBCollector()
        self.session = None
        
        # Timeframes supported by Gate.io (in minutes)
        self.timeframes = {
            "1m": "1m",
            "5m": "5m", 
            "15m": "15m",
            "30m": "30m",
            "1h": "1h",
            "4h": "4h",
            "1d": "1d",
            "1w": "1w"
        }
    
    async def connect(self):
        """Connect to MongoDB."""
        if not await self.mongo.connect():
            logger.error("❌ Failed to connect to MongoDB")
            return False
        logger.info("✅ Connected to MongoDB")
        return True
    
    async def disconnect(self):
        """Disconnect from MongoDB."""
        await self.mongo.disconnect()
        if self.session:
            await self.session.close()
    
    async def collect_historical_data(self, duration_hours: int = 24, timeframe: str = "1h"):
        """Collect historical OHLCV data."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        if not await self.connect():
            return
        
        logger.info(f"📊 Collecting Gate.io historical data for {len(self.symbols)} symbols")
        logger.info(f"⏱️  Timeframe: {timeframe}, Duration: {duration_hours} hours")
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=duration_hours)
        
        for symbol in self.symbols:
            try:
                await self._collect_symbol_data(symbol, timeframe, start_time, end_time)
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.error(f"❌ Error collecting {symbol}: {e}")
        
        await self.disconnect()
        logger.info("✅ Gate.io historical data collection completed")
    
    async def _collect_symbol_data(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime):
        """Collect data for a specific symbol."""
        try:
            # Get klines (OHLCV) data
            klines_data = await self._get_klines(symbol, timeframe, start_time, end_time)
            
            for kline in klines_data:
                historical_data = HistoricalData(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=datetime.fromtimestamp(kline["t"]),
                    open=float(kline["o"]),
                    high=float(kline["h"]),
                    low=float(kline["l"]),
                    close=float(kline["c"]),
                    volume=float(kline["v"]),
                    exchange=self.exchange
                )
                
                message = WebSocketMessage(
                    data_type=DataType.HISTORICAL_DATA,
                    data=historical_data,
                    raw_message=kline,
                    exchange=self.exchange
                )
                
                await self.mongo.store_message(message)
            
            logger.info(f"✅ Collected {len(klines_data)} candles for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error collecting {symbol} data: {e}")
    
    async def _get_klines(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get klines data from Gate.io API."""
        url = f"{self.base_url}/spot/candlesticks"
        params = {
            "currency_pair": symbol,
            "interval": self.timeframes[timeframe],
            "from": int(start_time.timestamp()),
            "to": int(end_time.timestamp()),
            "limit": 1000
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, list):
                        return data
                    else:
                        logger.error(f"❌ Unexpected response format for {symbol}: {data}")
                        return []
                else:
                    logger.error(f"❌ HTTP error for {symbol}: {response.status}")
                    # Try to get error details
                    try:
                        error_data = await response.json()
                        logger.error(f"❌ Error details: {error_data}")
                    except:
                        pass
                    return []
        except Exception as e:
            logger.error(f"❌ Request error for {symbol}: {e}")
            return []
    
    async def collect_historical_trades(self, duration_hours: int = 1):
        """Collect historical trades data."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        if not await self.connect():
            return
        
        logger.info(f"📊 Collecting Gate.io historical trades for {len(self.symbols)} symbols")
        logger.info(f"⏱️  Duration: {duration_hours} hours")
        
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=duration_hours)
        
        for symbol in self.symbols:
            try:
                await self._collect_symbol_trades(symbol, start_time, end_time)
                await asyncio.sleep(0.1)  # Rate limiting
            except Exception as e:
                logger.error(f"❌ Error collecting trades for {symbol}: {e}")
        
        await self.disconnect()
        logger.info("✅ Gate.io historical trades collection completed")
    
    async def _collect_symbol_trades(self, symbol: str, start_time: datetime, end_time: datetime):
        """Collect trades for a specific symbol."""
        try:
            trades_data = await self._get_trades(symbol, start_time, end_time)
            
            for trade in trades_data:
                # Handle decimal timestamp format
                try:
                    timestamp_ms = float(trade["create_time_ms"])
                    timestamp = datetime.fromtimestamp(timestamp_ms / 1000)
                except (ValueError, KeyError) as e:
                    logger.warning(f"⚠️ Invalid timestamp for trade {trade.get('id', 'unknown')}: {e}")
                    continue
                
                historical_trade = HistoricalTrade(
                    symbol=symbol,
                    timestamp=timestamp,
                    price=float(trade["price"]),
                    volume=float(trade["amount"]),
                    side=trade.get("side", "").lower(),
                    trade_id=trade.get("id", ""),
                    exchange=self.exchange
                )
                
                message = WebSocketMessage(
                    data_type=DataType.HISTORICAL_TRADES,
                    data=historical_trade,
                    raw_message=trade,
                    exchange=self.exchange
                )
                
                await self.mongo.store_message(message)
            
            logger.info(f"✅ Collected {len(trades_data)} trades for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error collecting trades for {symbol}: {e}")
    
    async def _get_trades(self, symbol: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get trades data from Gate.io API."""
        url = f"{self.base_url}/spot/trades"
        params = {
            "currency_pair": symbol,
            "from": int(start_time.timestamp()),
            "to": int(end_time.timestamp()),
            "limit": 1000
        }
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if isinstance(data, list):
                        return data
                    else:
                        logger.error(f"❌ Unexpected trades response format for {symbol}: {data}")
                        return []
                else:
                    logger.error(f"❌ HTTP error for {symbol} trades: {response.status}")
                    # Try to get error details
                    try:
                        error_data = await response.json()
                        logger.error(f"❌ Error details: {error_data}")
                    except:
                        pass
                    return []
        except Exception as e:
            logger.error(f"❌ Request error for {symbol} trades: {e}")
            return []

async def main():
    """Test the historical data collector."""
    collector = GateHistoricalCollector()
    
    try:
        # Collect 1 hour of 1h candles
        await collector.collect_historical_data(duration_hours=1, timeframe="1h")
        
        # Collect 1 hour of trades
        await collector.collect_historical_trades(duration_hours=1)
        
    except Exception as e:
        logger.error(f"❌ Error in main: {e}")
    finally:
        await collector.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
