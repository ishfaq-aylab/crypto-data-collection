#!/usr/bin/env python3
"""OKX historical data collector for OHLCV and trades data."""

import asyncio
import aiohttp
import ssl
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from loguru import logger

from models import HistoricalData, HistoricalTrade, WebSocketMessage, DataType
from simple_mongodb_collector import SimpleMongoDBCollector

class OKXHistoricalCollector:
    """Collects historical data from OKX REST API."""
    
    def __init__(self, symbols: List[str] = None):
        self.exchange = "okx"
        self.symbols = symbols or ["BTC-USDT", "ETH-USDT", "ADA-USDT", "SOL-USDT", "DOT-USDT"]
        self.base_url = "https://www.okx.com/api/v5"
        self.mongo = SimpleMongoDBCollector()
        self.session = None
        
        # Timeframes supported by OKX
        self.timeframes = {
            "1m": "1m",
            "5m": "5m", 
            "15m": "15m",
            "30m": "30m",
            "1h": "1H",
            "4h": "4H",
            "1d": "1D",
            "1w": "1W"
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
            # Create SSL context with more permissive settings
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')  # Lower security level
            
            # Create connector with SSL context and timeout settings
            connector = aiohttp.TCPConnector(
                ssl=ssl_context,
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
                enable_cleanup_closed=True,
                force_close=True,
            )
            
            timeout = aiohttp.ClientTimeout(total=60, connect=30, sock_read=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Connection': 'keep-alive',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                }
            )
        
        if not await self.connect():
            return
        
        logger.info(f"📊 Collecting OKX historical data for {len(self.symbols)} symbols")
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
        logger.info("✅ OKX historical data collection completed")
    
    async def _collect_symbol_data(self, symbol: str, timeframe: str, start_time: datetime, end_time: datetime):
        """Collect data for a specific symbol."""
        try:
            # Get klines (OHLCV) data
            klines_data = await self._get_klines(symbol, timeframe, start_time, end_time)
            
            for kline in klines_data:
                historical_data = HistoricalData(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=datetime.fromtimestamp(int(kline[0]) / 1000),
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
        """Get klines data from OKX API with retry mechanism and fallback endpoints."""
        # Try multiple OKX endpoints
        endpoints = [
            f"{self.base_url}/market/history-candles",
            f"https://www.okx.com/api/v5/market/history-candles",  # Alternative endpoint
            f"https://aws.okx.com/api/v5/market/history-candles"   # AWS endpoint
        ]
        
        params = {
            "instId": symbol,
            "bar": self.timeframes[timeframe],
            "before": int(end_time.timestamp() * 1000),
            "after": int(start_time.timestamp() * 1000),
            "limit": 300
        }
        
        max_retries = 3
        for endpoint in endpoints:
            for attempt in range(max_retries):
                try:
                    logger.info(f"🔄 Trying OKX endpoint: {endpoint} (attempt {attempt + 1})")
                    async with self.session.get(endpoint, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get("code") == "0":
                                logger.info(f"✅ Successfully connected to OKX: {endpoint}")
                                return data.get("data", [])
                            else:
                                logger.error(f"❌ API error for {symbol}: {data.get('msg')}")
                                return []
                        else:
                            logger.warning(f"⚠️ HTTP error for {symbol}: {response.status} (attempt {attempt + 1})")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                continue
                except Exception as e:
                    logger.warning(f"⚠️ Connection error for {symbol} on {endpoint}: {e} (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    # Try next endpoint
                    break
            
            # If we got here, this endpoint failed completely, try next one
            logger.warning(f"⚠️ Endpoint {endpoint} failed, trying next...")
            await asyncio.sleep(1)  # Brief pause before trying next endpoint
        
        logger.error(f"❌ All OKX endpoints failed for {symbol}")
        return []
    
    async def collect_historical_trades(self, duration_hours: int = 1):
        """Collect historical trades data."""
        if not self.session:
            # Create SSL context with more permissive settings
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            ssl_context.set_ciphers('DEFAULT@SECLEVEL=1')  # Lower security level
            
            # Create connector with SSL context and timeout settings
            connector = aiohttp.TCPConnector(
                ssl=ssl_context,
                limit=100,
                limit_per_host=30,
                ttl_dns_cache=300,
                use_dns_cache=True,
                enable_cleanup_closed=True,
                force_close=True,
            )
            
            timeout = aiohttp.ClientTimeout(total=60, connect=30, sock_read=30)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/json, text/plain, */*',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Connection': 'keep-alive',
                    'Cache-Control': 'no-cache',
                    'Pragma': 'no-cache',
                }
            )
        
        if not await self.connect():
            return
        
        logger.info(f"📊 Collecting OKX historical trades for {len(self.symbols)} symbols")
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
        logger.info("✅ OKX historical trades collection completed")
    
    async def _collect_symbol_trades(self, symbol: str, start_time: datetime, end_time: datetime):
        """Collect trades for a specific symbol."""
        try:
            trades_data = await self._get_trades(symbol, start_time, end_time)
            
            for trade in trades_data:
                historical_trade = HistoricalTrade(
                    symbol=symbol,
                    timestamp=datetime.fromtimestamp(int(trade["ts"]) / 1000),
                    price=float(trade["px"]),
                    volume=float(trade["sz"]),
                    side=trade.get("side", "").lower(),
                    trade_id=trade.get("tradeId", ""),
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
        """Get trades data from OKX API with fallback endpoints."""
        # Try multiple OKX endpoints
        endpoints = [
            f"{self.base_url}/market/history-trades",
            f"https://www.okx.com/api/v5/market/history-trades",  # Alternative endpoint
            f"https://aws.okx.com/api/v5/market/history-trades"   # AWS endpoint
        ]
        
        params = {
            "instId": symbol,
            "before": int(end_time.timestamp() * 1000),
            "after": int(start_time.timestamp() * 1000),
            "limit": 100
        }
        
        max_retries = 3
        for endpoint in endpoints:
            for attempt in range(max_retries):
                try:
                    logger.info(f"🔄 Trying OKX trades endpoint: {endpoint} (attempt {attempt + 1})")
                    async with self.session.get(endpoint, params=params) as response:
                        if response.status == 200:
                            data = await response.json()
                            if data.get("code") == "0":
                                logger.info(f"✅ Successfully connected to OKX trades: {endpoint}")
                                return data.get("data", [])
                            else:
                                logger.error(f"❌ API error for {symbol} trades: {data.get('msg')}")
                                return []
                        else:
                            logger.warning(f"⚠️ HTTP error for {symbol} trades: {response.status} (attempt {attempt + 1})")
                            if attempt < max_retries - 1:
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                continue
                except Exception as e:
                    logger.warning(f"⚠️ Connection error for {symbol} trades on {endpoint}: {e} (attempt {attempt + 1})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    # Try next endpoint
                    break
            
            # If we got here, this endpoint failed completely, try next one
            logger.warning(f"⚠️ Trades endpoint {endpoint} failed, trying next...")
            await asyncio.sleep(1)  # Brief pause before trying next endpoint
        
        logger.error(f"❌ All OKX trades endpoints failed for {symbol}")
        return []

async def main():
    """Test the historical data collector."""
    collector = OKXHistoricalCollector()
    
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
