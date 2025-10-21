#!/usr/bin/env python3
"""Binance historical data collector for OHLCV and trades data."""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger

from models import HistoricalData, HistoricalTrade, WebSocketMessage, DataType
from simple_mongodb_collector import SimpleMongoDBCollector

class BinanceHistoricalCollector:
    """Collects historical data from Binance REST API."""
    
    def __init__(self, symbols: List[str] = None):
        self.exchange = "binance"
        self.symbols = symbols or ["BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "DOTUSDT"]
        self.base_url = "https://api.binance.com/api/v3"
        self.mongo = SimpleMongoDBCollector()
        self.session = None
        
        # Timeframes supported by Binance
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
        
        logger.info(f"📊 Collecting Binance historical data for {len(self.symbols)} symbols")
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
        logger.info("✅ Binance historical data collection completed")
    
    async def _collect_symbol_data(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime):
        """Collect data for a specific symbol."""
        try:
            # Get klines (OHLCV) data
            klines_data = await self._get_klines(symbol, timeframe, start_time, end_time)
            
            for kline in klines_data:
                historical_data = HistoricalData(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=datetime.fromtimestamp(kline[0] / 1000),
                    open=float(kline[1]),
                    high=float(kline[2]),
                    low=float(kline[3]),
                    close=float(kline[4]),
                    volume=float(kline[5]),
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
    
    async def _get_klines(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime) -> List[List]:
        """Get klines data from Binance API."""
        url = f"{self.base_url}/klines"
        params = {
            "symbol": symbol,
            "interval": self.timeframes[timeframe],
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000),
            "limit": 1000
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                logger.error(f"❌ API error for {symbol}: {response.status}")
                return []
    
    async def collect_historical_trades(self, duration_hours: int = 1):
        """Collect historical trades data."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        if not await self.connect():
            return
        
        logger.info(f"📊 Collecting Binance historical trades for {len(self.symbols)} symbols")
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
        logger.info("✅ Binance historical trades collection completed")
    
    async def _collect_symbol_trades(self, symbol: str, start_time: datetime, end_time: datetime):
        """Collect trades for a specific symbol."""
        try:
            trades_data = await self._get_trades(symbol, start_time, end_time)
            
            for trade in trades_data:
                # Handle different possible field names in Binance response
                timestamp_field = trade.get("T", trade.get("time", 0))  # T is the actual trade time
                price_field = trade.get("p", trade.get("price", "0"))
                volume_field = trade.get("q", trade.get("qty", "0"))
                side_field = trade.get("m", trade.get("isBuyerMaker", True))  # m is true if buyer is maker
                trade_id_field = trade.get("a", trade.get("id", "0"))  # a is the aggregate trade ID
                
                historical_trade = HistoricalTrade(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(timestamp_field / 1000),
                    price=float(price_field),
                    volume=float(volume_field),
                    side="sell" if side_field else "buy",  # m=true means buyer is maker, so it's a sell
                    trade_id=str(trade_id_field),
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
        """Get trades data from Binance API."""
        url = f"{self.base_url}/aggTrades"
        params = {
            "symbol": symbol,
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000),
            "limit": 1000
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                return data
            else:
                logger.error(f"❌ API error for {symbol} trades: {response.status}")
                return []

async def main():
    """Test the historical data collector."""
    collector = BinanceHistoricalCollector()
    
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
