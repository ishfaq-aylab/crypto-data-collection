"""Bybit WebSocket client implementation."""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from loguru import logger

from base_client import BaseWebSocketClient
from models import (
    WebSocketMessage, DataType, MarketData, OrderBookData, 
    TickPrice, VolumeLiquidity, FundingRate, OpenInterest
)
from symbol_mapping import get_exchange_symbols, get_standard_symbol

class BybitWebSocketClient(BaseWebSocketClient):
    """Bybit WebSocket client."""
    
    def __init__(self, symbols: List[str] = None):
        super().__init__("bybit", symbols)
        self.subscription_id = 1
        # Convert symbols to Bybit format
        self.bybit_symbols = get_exchange_symbols("bybit", symbols or [])
    
    def get_websocket_url(self) -> str:
        """Get Bybit WebSocket URL."""
        return "wss://stream.bybit.com/v5/public/linear"
    
    def get_subscription_message(self) -> Dict[str, Any]:
        """Get Bybit subscription message."""
        if not self.bybit_symbols:
            return {}
        
        topics = []
        for symbol in self.bybit_symbols:
            # Bybit uses different topic names for different data types
            topics.extend([
                f"tickers.{symbol}",
                f"orderbook.50.{symbol}",
                f"publicTrade.{symbol}",
                f"kline.1.{symbol}",
                f"orderbook.200.{symbol}",
                f"funding.{symbol}",  # Funding rates
                f"openInterest.{symbol}"  # Open interest
            ])
        
        return {
            "op": "subscribe",
            "args": topics
        }
    
    def parse_message(self, message: Dict[str, Any]) -> Optional[WebSocketMessage]:
        """Parse Bybit WebSocket message."""
        try:
            if message.get('op') == 'subscribe':
                logger.info(f"Bybit subscription response: {message}")
                return None
            
            if message.get('topic'):
                topic = message['topic']
                data = message.get('data', {})
                
                if 'tickers' in topic:
                    return self._parse_ticker_data(topic, data)
                elif 'orderbook' in topic:
                    return self._parse_order_book_data(topic, data)
                elif 'publicTrade' in topic:
                    return self._parse_trade_data(topic, data)
                elif 'kline' in topic:
                    return self._parse_kline_data(topic, data)
                elif 'funding' in topic:
                    return self._parse_funding_data(topic, data)
                elif 'openInterest' in topic:
                    return self._parse_open_interest_data(topic, data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing Bybit message: {e}")
            return None
    
    def _extract_symbol_from_topic(self, topic: str) -> str:
        """Extract symbol from topic name."""
        # Extract symbol from topic like "tickers.BTCUSDT"
        return topic.split('.')[-1]
    
    def _parse_ticker_data(self, topic: str, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse ticker data."""
        symbol = self._extract_symbol_from_topic(topic)
        
        market_data = MarketData(
            symbol=symbol,
            price=float(data.get('lastPrice', 0)),
            volume=float(data.get('volume24h', 0)),
            timestamp=datetime.fromtimestamp(int(data.get('time', 0)) / 1000),
            exchange="bybit",
            bid=float(data.get('bid1Price', 0)) if data.get('bid1Price') else None,
            ask=float(data.get('ask1Price', 0)) if data.get('ask1Price') else None,
            high_24h=float(data.get('highPrice24h', 0)) if data.get('highPrice24h') else None,
            low_24h=float(data.get('lowPrice24h', 0)) if data.get('lowPrice24h') else None,
            change_24h=float(data.get('price24hPcnt', 0)) if data.get('price24hPcnt') else None
        )
        
        return WebSocketMessage(
            data_type=DataType.MARKET_DATA,
            data=market_data,
            raw_message=data,
            exchange="bybit"
        )
    
    def _parse_order_book_data(self, topic: str, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse order book data."""
        symbol = self._extract_symbol_from_topic(topic)
        
        order_book = OrderBookData(
            symbol=symbol,
            bids=[[float(bid[0]), float(bid[1])] for bid in data.get('b', [])],
            asks=[[float(ask[0]), float(ask[1])] for ask in data.get('a', [])],
            timestamp=datetime.fromtimestamp(int(data.get('ts', 0)) / 1000),
            exchange="bybit"
        )
        
        return WebSocketMessage(
            data_type=DataType.ORDER_BOOK_DATA,
            data=order_book,
            raw_message=data,
            exchange="bybit"
        )
    
    def _parse_trade_data(self, topic: str, data: List[Dict[str, Any]]) -> WebSocketMessage:
        """Parse trade data."""
        symbol = self._extract_symbol_from_topic(topic)
        
        # data is a list of trades
        for trade in data:
            tick_price = TickPrice(
                symbol=symbol,
                price=float(trade.get('p', 0)),
                timestamp=datetime.fromtimestamp(int(trade.get('T', 0)) / 1000),
                exchange="bybit",
                side=trade.get('S', '').lower()
            )
            
            return WebSocketMessage(
                data_type=DataType.TICK_PRICES,
                data=tick_price,
                raw_message=trade,
                exchange="bybit"
            )
        
        return None
    
    def _parse_kline_data(self, topic: str, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse kline/candlestick data."""
        symbol = self._extract_symbol_from_topic(topic)
        
        # Extract volume and liquidity data from kline
        volume_liquidity = VolumeLiquidity(
            symbol=symbol,
            volume_24h=float(data.get('v', 0)),
            liquidity=float(data.get('t', 0)),  # Turnover
            timestamp=datetime.fromtimestamp(int(data.get('t', 0)) / 1000),
            exchange="bybit"
        )
        
        return WebSocketMessage(
            data_type=DataType.VOLUME_LIQUIDITY,
            data=volume_liquidity,
            raw_message=data,
            exchange="bybit"
        )
    
    def _parse_funding_data(self, topic: str, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse funding rate data."""
        symbol = self._extract_symbol_from_topic(topic)
        
        funding_rate = FundingRate(
            symbol=symbol,
            funding_rate=float(data.get('fundingRate', 0)),
            funding_time=datetime.fromtimestamp(int(data.get('fundingRateTimestamp', 0)) / 1000),
            timestamp=datetime.fromtimestamp(int(data.get('timestamp', 0)) / 1000),
            exchange="bybit"
        )
        
        return WebSocketMessage(
            data_type=DataType.FUNDING_RATES,
            data=funding_rate,
            raw_message=data,
            exchange="bybit"
        )
    
    def _parse_open_interest_data(self, topic: str, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse open interest data."""
        symbol = self._extract_symbol_from_topic(topic)
        
        open_interest = OpenInterest(
            symbol=symbol,
            open_interest=float(data.get('openInterest', 0)),
            timestamp=datetime.fromtimestamp(int(data.get('timestamp', 0)) / 1000),
            exchange="bybit"
        )
        
        return WebSocketMessage(
            data_type=DataType.OPEN_INTEREST,
            data=open_interest,
            raw_message=data,
            exchange="bybit"
        )
