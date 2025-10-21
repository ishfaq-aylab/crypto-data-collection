"""OKX WebSocket client implementation."""

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
from config import Config

class OKXWebSocketClient(BaseWebSocketClient):
    """OKX WebSocket client."""
    
    def __init__(self, symbols: List[str] = None):
        super().__init__("okx", symbols)
        self.subscription_id = 1
        # Convert symbols to OKX format using symbol mapping
        self.okx_symbols = get_exchange_symbols("okx", symbols or [])
    
    
    def get_websocket_url(self) -> str:
        """Get OKX WebSocket URL."""
        return "wss://ws.okx.com:8443/ws/v5/public"
    
    def get_subscription_message(self) -> Dict[str, Any]:
        """Get OKX subscription message."""
        if not self.okx_symbols:
            return {}
        
        args = []
        for symbol in self.okx_symbols:
            args.extend([
                {"channel": "tickers", "instId": symbol},
                {"channel": "books", "instId": symbol, "depth": "20"},
                {"channel": "trades", "instId": symbol},
                {"channel": "mark-price", "instId": symbol},
                {"channel": "funding-rate", "instId": symbol},
                {"channel": "open-interest", "instId": symbol}
            ])
        
        return {
            "op": "subscribe",
            "args": args
        }
    
    def parse_message(self, message: Dict[str, Any]) -> Optional[WebSocketMessage]:
        """Parse OKX WebSocket message."""
        try:
            if message.get('event') == 'subscribe':
                logger.info(f"OKX subscription response: {message}")
                return None
            
            # Log all messages to debug
            logger.debug(f"OKX message: {message}")
            
            if message.get('arg') and message.get('data'):
                channel = message['arg'].get('channel')
                data = message['data']
                inst_id = message['arg'].get('instId')
                
                logger.info(f"OKX data received for {channel}: {inst_id}")
                
                if channel == 'tickers':
                    return self._parse_ticker_data(inst_id, data)
                elif channel == 'books':
                    return self._parse_order_book_data(inst_id, data)
                elif channel == 'trades':
                    return self._parse_trade_data(inst_id, data)
                elif channel == 'mark-price':
                    return self._parse_mark_price_data(inst_id, data)
                elif channel == 'funding-rate':
                    return self._parse_funding_rate_data(inst_id, data)
                elif channel == 'open-interest':
                    return self._parse_open_interest_data(inst_id, data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error parsing OKX message: {e}")
            return None
    
    def _parse_ticker_data(self, symbol: str, data: List[Dict[str, Any]]) -> WebSocketMessage:
        """Parse ticker data."""
        try:
            if not data:
                logger.warning("No ticker data received")
                return None
            
            ticker = data[0]
            # Convert symbol back to standard format
            standard_symbol = get_standard_symbol("okx", symbol)
            
            logger.info(f"Parsing OKX ticker data for {standard_symbol}: {ticker}")
            
            market_data = MarketData(
                symbol=standard_symbol,
                price=float(ticker.get('last', 0)),
                volume=float(ticker.get('volCcy24h', 0)),
                timestamp=datetime.fromtimestamp(int(ticker.get('ts', 0)) / 1000),
                exchange="okx",
                bid=float(ticker.get('bidPx', 0)) if ticker.get('bidPx') else None,
                ask=float(ticker.get('askPx', 0)) if ticker.get('askPx') else None,
                high_24h=float(ticker.get('high24h', 0)) if ticker.get('high24h') else None,
                low_24h=float(ticker.get('low24h', 0)) if ticker.get('low24h') else None,
                change_24h=float(ticker.get('chg', 0)) if ticker.get('chg') else None
            )
            
            logger.info(f"Successfully parsed OKX ticker data: {market_data}")
            
            return WebSocketMessage(
                data_type=DataType.MARKET_DATA,
                data=market_data,
                raw_message=ticker,
                exchange="okx"
            )
        except Exception as e:
            logger.error(f"Error parsing OKX ticker data: {e}")
            return None
    
    def _parse_order_book_data(self, symbol: str, data: List[Dict[str, Any]]) -> WebSocketMessage:
        """Parse order book data."""
        if not data:
            return None
        
        book = data[0]
        # Convert symbol back to standard format
        standard_symbol = get_standard_symbol("okx", symbol)
        
        order_book = OrderBookData(
            symbol=standard_symbol,
            bids=[[float(bid[0]), float(bid[1])] for bid in book.get('bids', [])],
            asks=[[float(ask[0]), float(ask[1])] for ask in book.get('asks', [])],
            timestamp=datetime.fromtimestamp(int(book.get('ts', 0)) / 1000),
            exchange="okx"
        )
        
        return WebSocketMessage(
            data_type=DataType.ORDER_BOOK_DATA,
            data=order_book,
            raw_message=book,
            exchange="okx"
        )
    
    def _parse_trade_data(self, symbol: str, data: List[Dict[str, Any]]) -> WebSocketMessage:
        """Parse trade data."""
        if not data:
            return None
        
        trade = data[0]
        # Convert symbol back to standard format
        standard_symbol = get_standard_symbol("okx", symbol)
        
        tick_price = TickPrice(
            symbol=standard_symbol,
            price=float(trade.get('px', 0)),
            timestamp=datetime.fromtimestamp(int(trade.get('ts', 0)) / 1000),
            exchange="okx",
            side=trade.get('side', '').lower()
        )
        
        return WebSocketMessage(
            data_type=DataType.TICK_PRICES,
            data=tick_price,
            raw_message=trade,
            exchange="okx"
        )
    
    def _parse_mark_price_data(self, symbol: str, data: List[Dict[str, Any]]) -> WebSocketMessage:
        """Parse mark price data."""
        if not data:
            return None
        
        mark_price = data[0]
        # Convert symbol back to standard format
        standard_symbol = get_standard_symbol("okx", symbol)
        
        market_data = MarketData(
            symbol=standard_symbol,
            price=float(mark_price.get('markPx', 0)),
            volume=0,
            timestamp=datetime.fromtimestamp(int(mark_price.get('ts', 0)) / 1000),
            exchange="okx"
        )
        
        return WebSocketMessage(
            data_type=DataType.MARKET_DATA,
            data=market_data,
            raw_message=mark_price,
            exchange="okx"
        )
    
    def _parse_funding_rate_data(self, symbol: str, data: List[Dict[str, Any]]) -> WebSocketMessage:
        """Parse funding rate data."""
        if not data:
            return None
        
        funding = data[0]
        # Convert symbol back to standard format
        standard_symbol = get_standard_symbol("okx", symbol)
        
        funding_rate = FundingRate(
            symbol=standard_symbol,
            funding_rate=float(funding.get('fundingRate', 0)),
            next_funding_time=datetime.fromtimestamp(int(funding.get('nextFundingTime', 0)) / 1000) if funding.get('nextFundingTime') else None,
            timestamp=datetime.fromtimestamp(int(funding.get('ts', 0)) / 1000),
            exchange="okx"
        )
        
        return WebSocketMessage(
            data_type=DataType.FUNDING_RATES,
            data=funding_rate,
            raw_message=funding,
            exchange="okx"
        )
    
    def _parse_open_interest_data(self, symbol: str, data: List[Dict[str, Any]]) -> WebSocketMessage:
        """Parse open interest data."""
        if not data:
            return None
        
        oi = data[0]
        # Convert symbol back to standard format
        standard_symbol = get_standard_symbol("okx", symbol)
        
        open_interest = OpenInterest(
            symbol=standard_symbol,
            open_interest=float(oi.get('oi', 0)),
            timestamp=datetime.fromtimestamp(int(oi.get('ts', 0)) / 1000),
            exchange="okx"
        )
        
        return WebSocketMessage(
            data_type=DataType.OPEN_INTEREST,
            data=open_interest,
            raw_message=oi,
            exchange="okx"
        )
