#!/usr/bin/env python3
"""
4-Year Historical Data Collection Strategy
==========================================

This script implements a comprehensive approach to collect 4 years of historical data
from all supported exchanges while respecting API rate limits.

Strategy:
1. Collect data in monthly batches to avoid overwhelming APIs
2. Implement proper rate limiting per exchange
3. Add progress tracking and resume capability
4. Handle errors gracefully with retry mechanisms
5. Store data incrementally to prevent data loss
"""

import asyncio
import aiohttp
import ssl
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger
import json
import os
from pathlib import Path

from models import HistoricalData, HistoricalTrade, WebSocketMessage, DataType
from simple_mongodb_collector import SimpleMongoDBCollector

class FourYearHistoricalCollector:
    """Collects 4 years of historical data with rate limiting and progress tracking."""
    
    def __init__(self):
        self.mongo = SimpleMongoDBCollector()
        self.progress_file = "collection_progress.json"
        self.progress = self.load_progress()
        
        # Exchange-specific rate limits (requests per minute)
        self.rate_limits = {
            "binance": 1200,  # 1200 requests per minute
            "bybit": 120,     # 120 requests per minute  
            "kraken": 60,     # 60 requests per minute
            "okx": 20,        # 20 requests per minute (conservative)
            "gate": 100       # 100 requests per minute
        }
        
        # Request tracking per exchange
        self.request_counts = {exchange: 0 for exchange in self.rate_limits.keys()}
        self.last_reset = {exchange: datetime.now() for exchange in self.rate_limits.keys()}
        
        # Collection strategy - Bitcoin USD pairs only
        self.symbols = ["BTCUSDT", "BTCUSDC", "BTCBUSD"]
        self.timeframes = ["1m", "1h"]  # Prioritize 1m, fallback to 1h
        self.start_date = datetime(2021, 1, 1)  # 4 years ago
        self.end_date = datetime.now()
        
    def load_progress(self) -> Dict[str, Any]:
        """Load collection progress from file."""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading progress: {e}")
        return {
            "completed_exchanges": [],
            "completed_symbols": {},
            "completed_timeframes": {},
            "last_updated": None
        }
    
    def save_progress(self):
        """Save collection progress to file."""
        self.progress["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(self.progress, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving progress: {e}")
    
    async def check_rate_limit(self, exchange: str) -> bool:
        """Check if we can make a request without exceeding rate limits."""
        now = datetime.now()
        
        # Reset counter every minute
        if (now - self.last_reset[exchange]).seconds >= 60:
            self.request_counts[exchange] = 0
            self.last_reset[exchange] = now
        
        # Check if we can make another request
        if self.request_counts[exchange] >= self.rate_limits[exchange]:
            wait_time = 60 - (now - self.last_reset[exchange]).seconds
            if wait_time > 0:
                logger.info(f"⏳ Rate limit reached for {exchange}, waiting {wait_time}s")
                await asyncio.sleep(wait_time)
                self.request_counts[exchange] = 0
                self.last_reset[exchange] = datetime.now()
        
        return True
    
    async def make_request(self, exchange: str, url: str, params: Dict = None) -> Optional[Dict]:
        """Make a rate-limited request."""
        await self.check_rate_limit(exchange)
        
        try:
            # Create SSL context
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
            }
            
            async with aiohttp.ClientSession(
                connector=aiohttp.TCPConnector(ssl=ssl_context),
                timeout=timeout,
                headers=headers
            ) as session:
                async with session.get(url, params=params) as response:
                    self.request_counts[exchange] += 1
                    
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.warning(f"HTTP {response.status} for {exchange}: {url}")
                        return None
                        
        except Exception as e:
            logger.error(f"Request error for {exchange}: {e}")
            return None
    
    async def collect_binance_data(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime):
        """Collect Binance historical data."""
        logger.info(f"📊 Collecting Binance {symbol} {timeframe} from {start_time} to {end_time}")
        
        # Binance klines endpoint
        url = "https://api.binance.com/api/v3/klines"
        params = {
            "symbol": symbol,
            "interval": timeframe,
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000),
            "limit": 1000
        }
        
        data = await self.make_request("binance", url, params)
        if data:
            await self.store_binance_klines(symbol, timeframe, data)
        
        # Binance trades endpoint
        url = "https://api.binance.com/api/v3/aggTrades"
        params = {
            "symbol": symbol,
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000),
            "limit": 1000
        }
        
        data = await self.make_request("binance", url, params)
        if data:
            await self.store_binance_trades(symbol, data)
    
    async def collect_bybit_data(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime):
        """Collect Bybit historical data."""
        logger.info(f"📊 Collecting Bybit {symbol} {timeframe} from {start_time} to {end_time}")
        
        # Bybit klines endpoint
        url = "https://api.bybit.com/v5/market/kline"
        params = {
            "category": "spot",
            "symbol": symbol,
            "interval": timeframe,
            "start": int(start_time.timestamp() * 1000),
            "end": int(end_time.timestamp() * 1000),
            "limit": 200
        }
        
        data = await self.make_request("bybit", url, params)
        if data and data.get("result", {}).get("list"):
            await self.store_bybit_klines(symbol, timeframe, data["result"]["list"])
        
        # Bybit trades endpoint
        url = "https://api.bybit.com/v5/market/recent-trade"
        params = {
            "category": "spot",
            "symbol": symbol,
            "limit": 1000
        }
        
        data = await self.make_request("bybit", url, params)
        if data and data.get("result", {}).get("list"):
            await self.store_bybit_trades(symbol, data["result"]["list"])
    
    async def collect_kraken_data(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime):
        """Collect Kraken historical data."""
        logger.info(f"📊 Collecting Kraken {symbol} {timeframe} from {start_time} to {end_time}")
        
        # Kraken OHLC endpoint
        url = "https://api.kraken.com/0/public/OHLC"
        params = {
            "pair": symbol,
            "interval": self.get_kraken_interval(timeframe),
            "since": int(start_time.timestamp())
        }
        
        data = await self.make_request("kraken", url, params)
        if data and data.get("result"):
            await self.store_kraken_ohlc(symbol, timeframe, data["result"])
        
        # Kraken trades endpoint
        url = "https://api.kraken.com/0/public/Trades"
        params = {
            "pair": symbol,
            "since": int(start_time.timestamp())
        }
        
        data = await self.make_request("kraken", url, params)
        if data and data.get("result"):
            await self.store_kraken_trades(symbol, data["result"])
    
    async def collect_gate_data(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime):
        """Collect Gate.io historical data."""
        logger.info(f"📊 Collecting Gate.io {symbol} {timeframe} from {start_time} to {end_time}")
        
        # Gate.io candlesticks endpoint
        url = "https://api.gateio.ws/api/v4/spot/candlesticks"
        params = {
            "currency_pair": symbol,
            "interval": timeframe,
            "from": int(start_time.timestamp()),
            "to": int(end_time.timestamp()),
            "limit": 1000
        }
        
        data = await self.make_request("gate", url, params)
        if data:
            await self.store_gate_klines(symbol, timeframe, data)
        
        # Gate.io trades endpoint (simplified - no time range to avoid 400 error)
        url = "https://api.gateio.ws/api/v4/spot/trades"
        params = {
            "currency_pair": symbol,
            "limit": 1000
        }
        
        data = await self.make_request("gate", url, params)
        if data:
            await self.store_gate_trades(symbol, data)
    
    def get_kraken_interval(self, timeframe: str) -> int:
        """Convert timeframe to Kraken interval in minutes."""
        intervals = {
            "1h": 60,
            "4h": 240,
            "1d": 1440
        }
        return intervals.get(timeframe, 60)
    
    async def store_binance_klines(self, symbol: str, timeframe: str, data: List):
        """Store Binance klines data."""
        for kline in data:
            historical_data = HistoricalData(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.fromtimestamp(int(kline[0]) / 1000),
                open=float(kline[1]),
                high=float(kline[2]),
                low=float(kline[3]),
                close=float(kline[4]),
                volume=float(kline[5]),
                exchange="binance"
            )
            
            message = WebSocketMessage(
                data_type=DataType.HISTORICAL_DATA,
                data=historical_data,
                raw_message=kline,
                exchange="binance"
            )
            
            await self.mongo.store_message(message)
    
    async def store_binance_trades(self, symbol: str, data: List):
        """Store Binance trades data."""
        for trade in data:
            historical_trade = HistoricalTrade(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(int(trade["T"]) / 1000),
                price=float(trade["p"]),
                volume=float(trade["q"]),
                side="sell" if trade["m"] else "buy",
                trade_id=str(trade["a"]),
                exchange="binance"
            )
            
            message = WebSocketMessage(
                data_type=DataType.HISTORICAL_TRADES,
                data=historical_trade,
                raw_message=trade,
                exchange="binance"
            )
            
            await self.mongo.store_message(message)
    
    async def store_bybit_klines(self, symbol: str, timeframe: str, data: List):
        """Store Bybit klines data."""
        for kline in data:
            historical_data = HistoricalData(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.fromtimestamp(int(kline[0]) / 1000),
                open=float(kline[1]),
                high=float(kline[2]),
                low=float(kline[3]),
                close=float(kline[4]),
                volume=float(kline[5]),
                exchange="bybit"
            )
            
            message = WebSocketMessage(
                data_type=DataType.HISTORICAL_DATA,
                data=historical_data,
                raw_message=kline,
                exchange="bybit"
            )
            
            await self.mongo.store_message(message)
    
    async def store_bybit_trades(self, symbol: str, data: List):
        """Store Bybit trades data."""
        for trade in data:
            # Handle different field names in Bybit response
            volume_field = trade.get("qty", trade.get("size", "0"))  # Try both qty and size
            trade_id_field = trade.get("execId", trade.get("exec_id", ""))
            
            historical_trade = HistoricalTrade(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(int(trade["time"]) / 1000),
                price=float(trade["price"]),
                volume=float(volume_field),
                side=trade["side"].lower(),
                trade_id=str(trade_id_field),
                exchange="bybit"
            )
            
            message = WebSocketMessage(
                data_type=DataType.HISTORICAL_TRADES,
                data=historical_trade,
                raw_message=trade,
                exchange="bybit"
            )
            
            await self.mongo.store_message(message)
    
    async def store_kraken_ohlc(self, symbol: str, timeframe: str, data: Dict):
        """Store Kraken OHLC data."""
        for pair_name, ohlc_data in data.items():
            # Handle both list and dict formats
            if isinstance(ohlc_data, dict):
                # If it's a dict, get the list from the dict
                ohlc_list = ohlc_data.get("list", [])
            elif isinstance(ohlc_data, list):
                # If it's already a list
                ohlc_list = ohlc_data
            else:
                logger.warning(f"Unexpected Kraken OHLC data format: {type(ohlc_data)}")
                continue
                
            for ohlc in ohlc_list:
                if len(ohlc) >= 7:  # Ensure we have enough data points
                    historical_data = HistoricalData(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=datetime.fromtimestamp(int(ohlc[0])),
                        open=float(ohlc[1]),
                        high=float(ohlc[2]),
                        low=float(ohlc[3]),
                        close=float(ohlc[4]),
                        volume=float(ohlc[6]),
                        exchange="kraken"
                    )
                
                message = WebSocketMessage(
                    data_type=DataType.HISTORICAL_DATA,
                    data=historical_data,
                    raw_message=ohlc,
                    exchange="kraken"
                )
                
                await self.mongo.store_message(message)
    
    async def store_kraken_trades(self, symbol: str, data: Dict):
        """Store Kraken trades data."""
        for pair_name, trades_data in data.items():
            # Handle both list and dict formats
            if isinstance(trades_data, dict):
                # If it's a dict, get the list from the dict
                trades_list = trades_data.get("list", [])
            elif isinstance(trades_data, list):
                # If it's already a list
                trades_list = trades_data
            else:
                logger.warning(f"Unexpected Kraken trades data format: {type(trades_data)}")
                continue
                
            for trade in trades_list:
                if len(trade) >= 4:  # Ensure we have enough data points
                    historical_trade = HistoricalTrade(
                        symbol=symbol,
                        timestamp=datetime.fromtimestamp(int(trade[2])),
                        price=float(trade[0]),
                        volume=float(trade[1]),
                        side="buy" if trade[3] == "b" else "sell",
                        trade_id=f"{trade[2]}_{trade[0]}",
                        exchange="kraken"
                    )
                
                message = WebSocketMessage(
                    data_type=DataType.HISTORICAL_TRADES,
                    data=historical_trade,
                    raw_message=trade,
                    exchange="kraken"
                )
                
                await self.mongo.store_message(message)
    
    async def store_gate_klines(self, symbol: str, timeframe: str, data: List):
        """Store Gate.io klines data."""
        for kline in data:
            historical_data = HistoricalData(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.fromtimestamp(int(kline[0])),
                open=float(kline[1]),
                high=float(kline[2]),
                low=float(kline[3]),
                close=float(kline[4]),
                volume=float(kline[5]),
                exchange="gate"
            )
            
            message = WebSocketMessage(
                data_type=DataType.HISTORICAL_DATA,
                data=historical_data,
                raw_message=kline,
                exchange="gate"
            )
            
            await self.mongo.store_message(message)
    
    async def store_gate_trades(self, symbol: str, data: List):
        """Store Gate.io trades data."""
        for trade in data:
            historical_trade = HistoricalTrade(
                symbol=symbol,
                timestamp=datetime.fromtimestamp(float(trade["create_time_ms"]) / 1000),
                price=float(trade["price"]),
                volume=float(trade["amount"]),
                side=trade["side"].lower(),
                trade_id=trade["id"],
                exchange="gate"
            )
            
            message = WebSocketMessage(
                data_type=DataType.HISTORICAL_TRADES,
                data=historical_trade,
                raw_message=trade,
                exchange="gate"
            )
            
            await self.mongo.store_message(message)
    
    async def collect_monthly_data(self, exchange: str, symbol: str, timeframe: str, year: int, month: int):
        """Collect data for a specific month."""
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        # Check if already completed
        key = f"{exchange}_{symbol}_{timeframe}_{year}_{month:02d}"
        if key in self.progress.get("completed_months", []):
            logger.info(f"⏭️ Skipping {key} (already completed)")
            return True
        
        try:
            if exchange == "binance":
                await self.collect_binance_data(symbol, timeframe, start_date, end_date)
            elif exchange == "bybit":
                await self.collect_bybit_data(symbol, timeframe, start_date, end_date)
            elif exchange == "kraken":
                await self.collect_kraken_data(symbol, timeframe, start_date, end_date)
            elif exchange == "gate":
                await self.collect_gate_data(symbol, timeframe, start_date, end_date)
            
            # Mark as completed
            if "completed_months" not in self.progress:
                self.progress["completed_months"] = []
            self.progress["completed_months"].append(key)
            self.save_progress()
            
            logger.info(f"✅ Completed {key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error collecting {key}: {e}")
            return False
    
    async def run_collection(self):
        """Run the 4-year historical data collection."""
        logger.info("🚀 Starting 4-year historical data collection")
        logger.info(f"📅 Period: {self.start_date} to {self.end_date}")
        logger.info(f"💰 Symbols: {self.symbols}")
        logger.info(f"⏰ Timeframes: {self.timeframes}")
        
        await self.mongo.connect()
        
        total_tasks = 0
        completed_tasks = 0
        
        # Calculate total tasks
        for exchange in ["binance", "bybit", "kraken", "gate"]:  # Skip OKX due to connection issues
            for symbol in self.symbols:
                for timeframe in self.timeframes:
                    for year in range(self.start_date.year, self.end_date.year + 1):
                        for month in range(1, 13):
                            if year == self.start_date.year and month < self.start_date.month:
                                continue
                            if year == self.end_date.year and month > self.end_date.month:
                                continue
                            total_tasks += 1
        
        logger.info(f"📊 Total tasks: {total_tasks}")
        
        # Collect data month by month
        for exchange in ["binance", "bybit", "kraken", "gate"]:
            logger.info(f"🔄 Starting collection for {exchange}")
            
            for symbol in self.symbols:
                logger.info(f"🔄 Collecting {symbol} for {exchange}")
                
                # Try 1-minute first, then fallback to 1-hour
                timeframes_to_try = ["1m", "1h"] if "1m" in self.timeframes and "1h" in self.timeframes else self.timeframes
                
                for timeframe in timeframes_to_try:
                    logger.info(f"🔄 Collecting {timeframe} data for {symbol} on {exchange}")
                    
                    for year in range(self.start_date.year, self.end_date.year + 1):
                        for month in range(1, 13):
                            if year == self.start_date.year and month < self.start_date.month:
                                continue
                            if year == self.end_date.year and month > self.end_date.month:
                                continue
                            
                            success = await self.collect_monthly_data(exchange, symbol, timeframe, year, month)
                            completed_tasks += 1
                            
                            if success:
                                logger.info(f"✅ Progress: {completed_tasks}/{total_tasks} ({completed_tasks/total_tasks*100:.1f}%)")
                                # If 1m succeeded, skip 1h for this month
                                if timeframe == "1m" and "1h" in timeframes_to_try:
                                    logger.info(f"⏭️ Skipping 1h for {symbol} on {exchange} - 1m data collected successfully")
                                    # Skip remaining months for 1h timeframe
                                    break
                            else:
                                logger.error(f"❌ Failed: {completed_tasks}/{total_tasks}")
                                # If 1m failed, try 1h as fallback
                                if timeframe == "1m" and "1h" in timeframes_to_try:
                                    logger.info(f"🔄 1m failed, trying 1h fallback for {symbol} on {exchange}")
                                    continue
                    
                    # If we successfully collected 1m data, break out of timeframe loop
                    if timeframe == "1m" and success:
                        break
                    
                    # Small delay between requests
                    await asyncio.sleep(0.1)
        
        await self.mongo.disconnect()
        logger.info("🎉 4-year historical data collection completed!")

async def main():
    """Main function to run the collection."""
    collector = FourYearHistoricalCollector()
    await collector.run_collection()

if __name__ == "__main__":
    asyncio.run(main())
