#!/usr/bin/env python3
"""Kraken historical data collector for OHLCV and trades data."""

import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger

from models import HistoricalData, HistoricalTrade, WebSocketMessage, DataType
from simple_mongodb_collector import SimpleMongoDBCollector

class KrakenHistoricalCollector:
    """Collects historical data from Kraken REST API."""
    
    def __init__(self, symbols: List[str] = None):
        self.exchange = "kraken"
        # Convert symbols to Kraken format
        self.symbols = symbols or ["XXBTZUSD", "XETHZUSD", "ADAUSD", "SOLUSD", "DOTUSD"]
        self.base_url = "https://api.kraken.com/0/public"
        self.mongo = SimpleMongoDBCollector()
        self.session = None
        
        # Timeframes supported by Kraken (in minutes)
        self.timeframes = {
            "1m": 1,
            "5m": 5, 
            "15m": 15,
            "30m": 30,
            "1h": 60,
            "4h": 240,
            "1d": 1440,
            "1w": 10080
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
        
        logger.info(f"📊 Collecting Kraken historical data for {len(self.symbols)} symbols")
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
        logger.info("✅ Kraken historical data collection completed")
    
    async def _collect_symbol_data(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime):
        """Collect data for a specific symbol."""
        try:
            # Get OHLC data
            ohlc_data = await self._get_ohlc(symbol, timeframe, start_time, end_time)
            
            for ohlc in ohlc_data:
                historical_data = HistoricalData(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=datetime.fromtimestamp(ohlc["time"]),
                    open=float(ohlc["open"]),
                    high=float(ohlc["high"]),
                    low=float(ohlc["low"]),
                    close=float(ohlc["close"]),
                    volume=float(ohlc["vwap"]),  # Using vwap as volume proxy
                    exchange=self.exchange
                )
                
                message = WebSocketMessage(
                    data_type=DataType.HISTORICAL_DATA,
                    data=historical_data,
                    raw_message=ohlc,
                    exchange=self.exchange
                )
                
                await self.mongo.store_message(message)
            
            logger.info(f"✅ Collected {len(ohlc_data)} candles for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Error collecting {symbol} data: {e}")
    
    async def _get_ohlc(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Get OHLC data from Kraken API."""
        url = f"{self.base_url}/OHLC"
        params = {
            "pair": symbol,
            "interval": self.timeframes[timeframe],
            "since": int(start_time.timestamp())
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if not data.get("error"):
                    result = data.get("result", {})
                    # Kraken returns data in a nested structure
                    for pair_name, ohlc_list in result.items():
                        if pair_name != "last":
                            return self._parse_kraken_ohlc(ohlc_list)
                    return []
                else:
                    logger.error(f"❌ API error for {symbol}: {data.get('error')}")
                    return []
            else:
                logger.error(f"❌ HTTP error for {symbol}: {response.status}")
                return []
    
    def _parse_kraken_ohlc(self, ohlc_list: List[List]) -> List[Dict]:
        """Parse Kraken OHLC data format."""
        parsed_data = []
        for item in ohlc_list:
            if len(item) >= 7:
                parsed_data.append({
                    "time": item[0],
                    "open": item[1],
                    "high": item[2],
                    "low": item[3],
                    "close": item[4],
                    "vwap": item[5],
                    "volume": item[6],
                    "count": item[7] if len(item) > 7 else 0
                })
        return parsed_data
    
    async def collect_historical_trades(self, duration_hours: int = 1):
        """Collect historical trades data."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        
        if not await self.connect():
            return
        
        logger.info(f"📊 Collecting Kraken historical trades for {len(self.symbols)} symbols")
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
        logger.info("✅ Kraken historical trades collection completed")
    
    async def _collect_symbol_trades(self, symbol: str, start_time: datetime, end_time: datetime):
        """Collect trades for a specific symbol."""
        try:
            trades_data = await self._get_trades(symbol, start_time, end_time)
            
            for trade in trades_data:
                historical_trade = HistoricalTrade(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(trade["time"]),
                    price=float(trade["price"]),
                    volume=float(trade["volume"]),
                    side=trade.get("side", "").lower(),
                    trade_id=trade.get("trade_id", ""),
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
        """Get trades data from Kraken API."""
        url = f"{self.base_url}/Trades"
        params = {
            "pair": symbol,
            "since": int(start_time.timestamp())
        }
        
        async with self.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                if not data.get("error"):
                    result = data.get("result", {})
                    # Kraken returns data in a nested structure
                    for pair_name, trades_list in result.items():
                        if pair_name != "last":
                            return self._parse_kraken_trades(trades_list)
                    return []
                else:
                    logger.error(f"❌ API error for {symbol} trades: {data.get('error')}")
                    return []
            else:
                logger.error(f"❌ HTTP error for {symbol} trades: {response.status}")
                return []
    
    def _parse_kraken_trades(self, trades_list: List[List]) -> List[Dict]:
        """Parse Kraken trades data format."""
        parsed_data = []
        for i, item in enumerate(trades_list):
            if len(item) >= 4:
                parsed_data.append({
                    "time": item[2],
                    "price": item[0],
                    "volume": item[1],
                    "side": "buy" if item[3] == "b" else "sell",
                    "trade_id": f"kraken_{i}_{item[2]}"
                })
        return parsed_data

async def main():
    """Test the historical data collector."""
    collector = KrakenHistoricalCollector()
    
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
