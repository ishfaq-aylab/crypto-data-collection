"""Gate.io WebSocket client implementation."""

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
from config import Config

class GateWebSocketClient(BaseWebSocketClient):
    """Gate.io WebSocket client."""
    
    def __init__(self, symbols: List[str] = None):
        super().__init__("gate", symbols)
        self.subscription_id = 1
        # Convert symbols to Gate.io format using symbol mapping
        self.gate_symbols = get_exchange_symbols("gate", symbols or [])
    
    
    def get_websocket_url(self) -> str:
        """Get Gate.io WebSocket URL."""
        return "wss://api.gateio.ws/ws/v4/"
    
    def get_subscription_message(self) -> Dict[str, Any]:
        """Get Gate.io subscription message."""
        if not self.gate_symbols:
            return {}
        
        # Gate.io requires separate subscription messages for each channel
        # We'll send multiple messages, starting with tickers
        return {
            "time": int(datetime.now().timestamp()),
            "channel": "spot.tickers",
            "event": "subscribe",
            "payload": self.gate_symbols
        }
    
    async def send_all_subscriptions(self):
        """Send all subscription messages for Gate.io."""
        if not self.gate_symbols:
            return
        
        # Send subscription for each channel
        channels = [
            "spot.tickers",
            "spot.trades",
            "spot.candlesticks",
            "futures.tickers",  # For funding rates and open interest
            "futures.funding_rates",
            "futures.open_interest"
        ]
        
        for channel in channels:
            message = {
                "time": int(datetime.now().timestamp()),
                "channel": channel,
                "event": "subscribe",
                "payload": self.gate_symbols
            }
            await self.websocket.send(json.dumps(message))
            logger.info(f"Sent {channel} subscription to Gate.io")
            await asyncio.sleep(0.1)  # Small delay between subscriptions
        
        # Send order book subscription with required parameters
        await self._send_order_book_subscription()
    
    async def _send_order_book_subscription(self):
        """Send order book subscription with required parameters."""
        if not self.gate_symbols:
            return
        
        for symbol in self.gate_symbols:
            message = {
                "time": int(datetime.now().timestamp()),
                "channel": "spot.order_book",
                "event": "subscribe",
                "payload": [symbol, "20", "100ms"]  # symbol, depth, interval
            }
            await self.websocket.send(json.dumps(message))
            logger.info(f"Sent order book subscription for {symbol} to Gate.io")
            await asyncio.sleep(0.1)
    
    def parse_message(self, message: Dict[str, Any]) -> Optional[WebSocketMessage]:
        """Parse Gate.io WebSocket message."""
        try:
            # Skip non-dict messages (like 0)
            if not isinstance(message, dict):
                return None
                
            if message.get('event') == 'subscribe':
                logger.info(f"Gate.io subscription response: {message}")
                return None
            
            if message.get('channel') and message.get('result'):
                channel = message['channel']
                data = message['result']
                
                if 'tickers' in channel:
                    return self._parse_ticker_data(data)
                elif 'order_book' in channel:
                    return self._parse_order_book_data(data)
                elif 'trades' in channel:
                    return self._parse_trade_data(data)
                elif 'funding_rates' in channel:
                    return self._parse_funding_rate_data(data)
                elif 'open_interest' in channel:
                    return self._parse_open_interest_data(data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing Gate.io message: {e}")
            return None
    
    def _parse_ticker_data(self, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse ticker data."""
        symbol = get_standard_symbol("gate", data.get('currency_pair', ''))
        
        market_data = MarketData(
            symbol=symbol,
            price=float(data.get('last', 0)),
            volume=float(data.get('base_volume', 0)),
            timestamp=datetime.fromtimestamp(int(data.get('timestamp', 0))),
            exchange="gate",
            bid=float(data.get('highest_bid', 0)) if data.get('highest_bid') else None,
            ask=float(data.get('lowest_ask', 0)) if data.get('lowest_ask') else None,
            high_24h=float(data.get('high_24h', 0)) if data.get('high_24h') else None,
            low_24h=float(data.get('low_24h', 0)) if data.get('low_24h') else None,
            change_24h=float(data.get('change_percentage', 0)) if data.get('change_percentage') else None
        )
        
        return WebSocketMessage(
            data_type=DataType.MARKET_DATA,
            data=market_data,
            raw_message=data,
            exchange="gate"
        )
    
    def _parse_order_book_data(self, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse order book data."""
        symbol = data.get('s', '').replace('_', '')
        
        order_book = OrderBookData(
            symbol=symbol,
            bids=[[float(bid[0]), float(bid[1])] for bid in data.get('bids', [])],
            asks=[[float(ask[0]), float(ask[1])] for ask in data.get('asks', [])],
            timestamp=datetime.fromtimestamp(int(data.get('t', 0)) / 1000),
            exchange="gate"
        )
        
        return WebSocketMessage(
            data_type=DataType.ORDER_BOOK_DATA,
            data=order_book,
            raw_message=data,
            exchange="gate"
        )
    
    def _parse_trade_data(self, data: List[Dict[str, Any]]) -> WebSocketMessage:
        """Parse trade data."""
        if not data:
            return None
        
        trade = data[0]
        symbol = trade.get('currency_pair', '').replace('_', '')
        
        tick_price = TickPrice(
            symbol=symbol,
            price=float(trade.get('price', 0)),
            timestamp=datetime.fromtimestamp(int(trade.get('time', 0))),
            exchange="gate",
            side=trade.get('side', '').lower()
        )
        
        return WebSocketMessage(
            data_type=DataType.TICK_PRICES,
            data=tick_price,
            raw_message=trade,
            exchange="gate"
        )
    
    def _parse_funding_rate_data(self, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse funding rate data."""
        symbol = data.get('contract', '')
        
        funding_rate = FundingRate(
            symbol=symbol,
            funding_rate=float(data.get('rate', 0)),
            next_funding_time=datetime.fromtimestamp(int(data.get('next_funding_time', 0))) if data.get('next_funding_time') else None,
            timestamp=datetime.fromtimestamp(int(data.get('time', 0))),
            exchange="gate"
        )
        
        return WebSocketMessage(
            data_type=DataType.FUNDING_RATES,
            data=funding_rate,
            raw_message=data,
            exchange="gate"
        )
    
    def _parse_open_interest_data(self, data: Dict[str, Any]) -> WebSocketMessage:
        """Parse open interest data."""
        symbol = data.get('contract', '')
        
        open_interest = OpenInterest(
            symbol=symbol,
            open_interest=float(data.get('open_interest', 0)),
            timestamp=datetime.fromtimestamp(int(data.get('time', 0))),
            exchange="gate"
        )
        
        return WebSocketMessage(
            data_type=DataType.OPEN_INTEREST,
            data=open_interest,
            raw_message=data,
            exchange="gate"
        )
