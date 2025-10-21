"""Kraken WebSocket client implementation."""

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

class KrakenWebSocketClient(BaseWebSocketClient):
    """Kraken WebSocket client."""
    
    def __init__(self, symbols: List[str] = None):
        super().__init__("kraken", symbols)
        self.subscription_id = 1
        # Convert symbols to Kraken format
        self.kraken_symbols = get_exchange_symbols("kraken", symbols or [])
    
    def get_websocket_url(self) -> str:
        """Get Kraken WebSocket URL."""
        return "wss://ws.kraken.com/"
    
    def get_subscription_message(self) -> Dict[str, Any]:
        """Get Kraken subscription message."""
        # Subscriptions are sent via send_all_subscriptions after connection
        return {}
    
    async def send_all_subscriptions(self):
        """Send all subscription messages for Kraken."""
        if not self.kraken_symbols:
            return
        
        # Send subscription for each data type
        subscriptions = [
            {
                "event": "subscribe",
                "pair": self.kraken_symbols,
                "subscription": {"name": "ticker"}
            },
            {
                "event": "subscribe",
                "pair": self.kraken_symbols,
                "subscription": {"name": "book", "depth": 10}
            },
            {
                "event": "subscribe",
                "pair": self.kraken_symbols,
                "subscription": {"name": "trade"}
            },
            {
                "event": "subscribe",
                "pair": self.kraken_symbols,
                "subscription": {"name": "spread"}
            }
        ]
        
        for subscription in subscriptions:
            await self.websocket.send(json.dumps(subscription))
            logger.info(f"Sent Kraken subscription: {subscription['subscription']['name']}")
            await asyncio.sleep(0.1)  # Small delay between subscriptions
    
    def parse_message(self, message: Dict[str, Any]) -> Optional[WebSocketMessage]:
        """Parse Kraken WebSocket message."""
        try:
            if isinstance(message, list) and len(message) >= 4:
                # This is a data message
                channel_id = message[0]
                data = message[1]
                channel_name = message[2]
                pair = message[3]
                
                if channel_name == "ticker":
                    return self._parse_ticker_data(pair, data)
                elif channel_name == "book":
                    return self._parse_order_book_data(pair, data)
                elif channel_name == "trade":
                    return self._parse_trade_data(pair, data)
                elif channel_name == "spread":
                    return self._parse_spread_data(pair, data)
            
            elif isinstance(message, dict):
                # This is a system message
                if message.get('event') == 'subscriptionStatus':
                    logger.info(f"Kraken subscription status: {message.get('status')}")
                elif message.get('event') == 'systemStatus':
                    logger.info(f"Kraken system status: {message.get('status')}")
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing Kraken message: {e}")
            return None
    
    def _parse_ticker_data(self, pair: str, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse ticker data."""
        # Convert Kraken pair back to standard format
        symbol = get_standard_symbol("kraken", pair)
        
        market_data = MarketData(
            symbol=symbol,
            price=float(data.get('c', [0])[0]) if data.get('c') else 0,
            volume=float(data.get('v', [0])[0]) if data.get('v') else 0,
            timestamp=datetime.now(),
            exchange="kraken",
            bid=float(data.get('b', [0])[0]) if data.get('b') else None,
            ask=float(data.get('a', [0])[0]) if data.get('a') else None,
            high_24h=float(data.get('h', [0])[0]) if data.get('h') else None,
            low_24h=float(data.get('l', [0])[0]) if data.get('l') else None,
            change_24h=float(data.get('p', [0])[0]) if data.get('p') else None
        )
        
        return WebSocketMessage(
            data_type=DataType.MARKET_DATA,
            data=market_data,
            raw_message=data,
            exchange="kraken"
        )
    
    def _parse_order_book_data(self, pair: str, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse order book data."""
        symbol = get_standard_symbol("kraken", pair)
        
        order_book = OrderBookData(
            symbol=symbol,
            bids=[[float(bid[0]), float(bid[1])] for bid in data.get('bs', [])],
            asks=[[float(ask[0]), float(ask[1])] for ask in data.get('as', [])],
            timestamp=datetime.now(),
            exchange="kraken"
        )
        
        return WebSocketMessage(
            data_type=DataType.ORDER_BOOK_DATA,
            data=order_book,
            raw_message=data,
            exchange="kraken"
        )
    
    def _parse_trade_data(self, pair: str, data: List[List]) -> WebSocketMessage:
        """Parse trade data."""
        symbol = get_standard_symbol("kraken", pair)
        
        # data is a list of trades: [price, volume, time, side, order_type, misc]
        for trade in data:
            price, volume, timestamp, side, order_type, misc = trade
            
            tick_price = TickPrice(
                symbol=symbol,
                price=float(price),
                timestamp=datetime.fromtimestamp(float(timestamp)),
                exchange="kraken",
                side=side
            )
            
            return WebSocketMessage(
                data_type=DataType.TICK_PRICES,
                data=tick_price,
                raw_message=trade,
                exchange="kraken"
            )
        
        return None
    
    def _parse_spread_data(self, pair: str, data: List) -> WebSocketMessage:
        """Parse spread data."""
        symbol = get_standard_symbol("kraken", pair)
        
        if len(data) >= 2:
            bid, ask = data[0], data[1]
            mid_price = (float(bid) + float(ask)) / 2
            
            market_data = MarketData(
                symbol=symbol,
                price=mid_price,
                volume=0,
                timestamp=datetime.now(),
                exchange="kraken",
                bid=float(bid),
                ask=float(ask)
            )
            
            return WebSocketMessage(
                data_type=DataType.MARKET_DATA,
                data=market_data,
                raw_message=data,
                exchange="kraken"
            )
    
    def _parse_spread_data(self, pair: str, data: List) -> WebSocketMessage:
        """Parse spread data."""
        if len(data) >= 2:
            bid = data[0]
            ask = data[1]
            
            market_data = MarketData(
                symbol=pair,
                price=(float(bid) + float(ask)) / 2,
                volume=0,
                timestamp=datetime.now(),
                exchange="kraken",
                bid=float(bid),
                ask=float(ask)
            )
            
            return WebSocketMessage(
                data_type=DataType.MARKET_DATA,
                data=market_data,
                raw_message=data,
                exchange="kraken"
            )
        
        return None
