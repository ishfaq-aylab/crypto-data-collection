"""Binance WebSocket client implementation."""

import json
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from base_client import BaseWebSocketClient
from models import (
    WebSocketMessage, DataType, MarketData, OrderBookData, 
    TickPrice, VolumeLiquidity, FundingRate, OpenInterest
)
from symbol_mapping import get_exchange_symbols, get_standard_symbol

class BinanceWebSocketClient(BaseWebSocketClient):
    """Binance WebSocket client."""
    
    def __init__(self, symbols: List[str] = None):
        super().__init__("binance", symbols)
        self.streams = []
        # Convert symbols to Binance format
        self.binance_symbols = get_exchange_symbols("binance", symbols or [])
        self._build_streams()
    
    def _build_streams(self):
        """Build stream names for Binance."""
        if not self.binance_symbols:
            return
        
        for symbol in self.binance_symbols:
            # Convert symbol format (e.g., BTCUSDT -> btcusdt)
            binance_symbol = symbol.lower()
            
            # Add different stream types
            self.streams.extend([
                f"{binance_symbol}@ticker",      # 24hr ticker
                f"{binance_symbol}@depth20@100ms", # Order book
                f"{binance_symbol}@trade",       # Trade data
                f"{binance_symbol}@bookTicker",  # Best bid/ask
                f"{binance_symbol}@markPrice",   # Mark price
                f"{binance_symbol}@openInterest", # Open interest
                f"{binance_symbol}@markPrice@1s", # Mark price 1s
                f"{binance_symbol}@openInterest@1s" # Open interest 1s
            ])
    
    def get_websocket_url(self) -> str:
        """Get Binance WebSocket URL."""
        if self.streams:
            streams_str = "/".join(self.streams)
            return f"wss://stream.binance.com:9443/stream?streams={streams_str}"
        return "wss://stream.binance.com:9443/ws/!ticker@arr"
    
    def get_subscription_message(self) -> Optional[Dict[str, Any]]:
        """Binance doesn't require subscription message for public streams."""
        return None
    
    def parse_message(self, message: Dict[str, Any]) -> Optional[WebSocketMessage]:
        """Parse Binance WebSocket message."""
        try:
            if 'stream' in message and 'data' in message:
                stream = message['stream']
                data = message['data']
                
                # Extract symbol from stream name
                symbol = self._extract_symbol_from_stream(stream)
                
                logger.debug(f"Parsing Binance stream: {stream} for symbol: {symbol}")
                
                if '@ticker' in stream:
                    # Return market data, volume/liquidity will be extracted separately
                    result = self._parse_ticker_data(symbol, data)
                    logger.debug(f"Ticker data parsed: {result is not None}")
                    return result
                elif '@depth' in stream:
                    result = self._parse_order_book_data(symbol, data)
                    logger.debug(f"Order book data parsed: {result is not None}")
                    return result
                elif '@trade' in stream:
                    result = self._parse_trade_data(symbol, data)
                    logger.debug(f"Trade data parsed: {result is not None}")
                    return result
                elif '@bookTicker' in stream:
                    # Book ticker also provides market data (best bid/ask)
                    result = self._parse_book_ticker_data(symbol, data)
                    logger.debug(f"Book ticker data parsed: {result is not None}")
                    return result
                elif '@markPrice' in stream:
                    result = self._parse_mark_price_data(symbol, data)
                    logger.debug(f"Mark price data parsed: {result is not None}")
                    return result
                elif '@openInterest' in stream:
                    result = self._parse_open_interest_data(symbol, data)
                    logger.debug(f"Open interest data parsed: {result is not None}")
                    return result
                else:
                    logger.debug(f"Unknown stream type: {stream}")
            
            logger.debug(f"No stream/data in message: {message.keys()}")
            return None
            
        except Exception as e:
            logger.error(f"Error parsing Binance message: {e}")
            return None
    
    def _extract_symbol_from_stream(self, stream: str) -> str:
        """Extract symbol from stream name."""
        # Extract symbol from stream like "btcusdt@ticker"
        return stream.split('@')[0].upper()
    
    def _parse_ticker_data(self, symbol: str, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse 24hr ticker data."""
        market_data = MarketData(
            symbol=symbol,
            price=float(data.get('c', 0)),  # Close price
            volume=float(data.get('v', 0)),  # Volume
            timestamp=datetime.fromtimestamp(data.get('E', 0) / 1000),
            exchange="binance",
            bid=float(data.get('b', 0)) if data.get('b') else None,
            ask=float(data.get('a', 0)) if data.get('a') else None,
            high_24h=float(data.get('h', 0)) if data.get('h') else None,
            low_24h=float(data.get('l', 0)) if data.get('l') else None,
            change_24h=float(data.get('P', 0)) if data.get('P') else None
        )
        
        # Also extract volume/liquidity data
        self._extract_and_notify_volume_liquidity(symbol, data)
        
        return WebSocketMessage(
            data_type=DataType.MARKET_DATA,
            data=market_data,
            raw_message=data,
            exchange="binance"
        )
    
    def _extract_and_notify_volume_liquidity(self, symbol: str, data: Dict[str, Any]):
        """Extract and notify volume/liquidity data."""
        volume_data = VolumeLiquidity(
            symbol=symbol,
            volume_24h=float(data.get('v', 0)),  # 24h volume
            quote_volume_24h=float(data.get('q', 0)),  # Quote volume
            timestamp=datetime.fromtimestamp(data.get('E', 0) / 1000),
            exchange="binance"
        )
        
        volume_message = WebSocketMessage(
            data_type=DataType.VOLUME_LIQUIDITY,
            data=volume_data,
            raw_message=data,
            exchange="binance"
        )
        
        # Notify handlers directly
        asyncio.create_task(self._notify_handlers(volume_message))
    
    def _extract_volume_liquidity(self, symbol: str, data: Dict[str, Any]) -> WebSocketMessage:
        """Extract volume/liquidity from ticker data."""
        volume_data = VolumeLiquidity(
            symbol=symbol,
            volume_24h=float(data.get('v', 0)),  # 24h volume
            quote_volume_24h=float(data.get('q', 0)),  # Quote volume
            timestamp=datetime.fromtimestamp(data.get('E', 0) / 1000),
            exchange="binance"
        )
        
        return WebSocketMessage(
            data_type=DataType.VOLUME_LIQUIDITY,
            data=volume_data,
            raw_message=data,
            exchange="binance"
        )
    
    def _parse_order_book_data(self, symbol: str, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse order book data."""
        order_book = OrderBookData(
            symbol=symbol,
            bids=[[float(bid[0]), float(bid[1])] for bid in data.get('bids', [])],
            asks=[[float(ask[0]), float(ask[1])] for ask in data.get('asks', [])],
            timestamp=datetime.fromtimestamp(data.get('E', 0) / 1000),
            exchange="binance"
        )
        
        return WebSocketMessage(
            data_type=DataType.ORDER_BOOK_DATA,
            data=order_book,
            raw_message=data,
            exchange="binance"
        )
    
    def _parse_trade_data(self, symbol: str, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse trade data."""
        tick_price = TickPrice(
            symbol=symbol,
            price=float(data.get('p', 0)),
            timestamp=datetime.fromtimestamp(data.get('T', 0) / 1000),
            exchange="binance",
            side=data.get('m', '').lower()  # 'm' indicates if buyer is maker
        )
        
        return WebSocketMessage(
            data_type=DataType.TICK_PRICES,
            data=tick_price,
            raw_message=data,
            exchange="binance"
        )
    
    def _parse_book_ticker_data(self, symbol: str, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse book ticker data."""
        market_data = MarketData(
            symbol=symbol,
            price=(float(data.get('b', 0)) + float(data.get('a', 0))) / 2,
            volume=0,  # Not available in book ticker
            timestamp=datetime.fromtimestamp(data.get('u', 0) / 1000),
            exchange="binance",
            bid=float(data.get('b', 0)) if data.get('b') else None,
            ask=float(data.get('a', 0)) if data.get('a') else None
        )
        
        return WebSocketMessage(
            data_type=DataType.MARKET_DATA,
            data=market_data,
            raw_message=data,
            exchange="binance"
        )
    
    def _parse_mark_price_data(self, symbol: str, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse mark price data - can include funding rate."""
        # Check if this is funding rate data
        if 'r' in data:  # funding rate field
            funding_rate = FundingRate(
                symbol=symbol,
                funding_rate=float(data.get('r', 0)),
                funding_time=datetime.fromtimestamp(data.get('E', 0) / 1000),
                timestamp=datetime.fromtimestamp(data.get('E', 0) / 1000),
                exchange="binance"
            )
            
            return WebSocketMessage(
                data_type=DataType.FUNDING_RATES,
                data=funding_rate,
                raw_message=data,
                exchange="binance"
            )
        else:
            # Regular mark price data
            market_data = MarketData(
                symbol=symbol,
                price=float(data.get('p', 0)),
                volume=0,
                timestamp=datetime.fromtimestamp(data.get('E', 0) / 1000),
                exchange="binance"
            )
            
            return WebSocketMessage(
                data_type=DataType.MARKET_DATA,
                data=market_data,
                raw_message=data,
                exchange="binance"
            )
    
    def _parse_open_interest_data(self, symbol: str, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse open interest data."""
        open_interest = OpenInterest(
            symbol=symbol,
            open_interest=float(data.get('openInterest', 0)),
            timestamp=datetime.fromtimestamp(data.get('E', 0) / 1000),
            exchange="binance"
        )
        
        return WebSocketMessage(
            data_type=DataType.OPEN_INTEREST,
            data=open_interest,
            raw_message=data,
            exchange="binance"
        )
