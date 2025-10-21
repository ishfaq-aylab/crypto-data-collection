"""Data models for WebSocket market data."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from enum import Enum

class DataType(str, Enum):
    """Enum for different types of market data."""
    MARKET_DATA = "market_data"
    ORDER_BOOK_DATA = "order_book_data"
    TICK_PRICES = "tick_prices"
    VOLUME_LIQUIDITY = "volume_liquidity"
    FUNDING_RATES = "funding_rates"
    OPEN_INTEREST = "open_interest"
    HISTORICAL_DATA = "historical_data"
    HISTORICAL_TRADES = "historical_trades"

class MarketData(BaseModel):
    """Market data model."""
    symbol: str
    price: float
    volume: float
    timestamp: datetime
    exchange: str
    bid: Optional[float] = None
    ask: Optional[float] = None
    # Optional sizes for bid/ask to align with DATA_DEFINITIONS.md
    bid_size: Optional[float] = None
    ask_size: Optional[float] = None
    high_24h: Optional[float] = None
    low_24h: Optional[float] = None
    change_24h: Optional[float] = None

class OrderBookData(BaseModel):
    """Order book data model."""
    symbol: str
    bids: List[List[float]]  # [[price, quantity], ...]
    asks: List[List[float]]  # [[price, quantity], ...]
    timestamp: datetime
    exchange: str

class TickPrice(BaseModel):
    """Tick price data model."""
    symbol: str
    price: float
    # Volume (quantity) of the trade to align with DATA_DEFINITIONS.md
    volume: Optional[float] = None
    timestamp: datetime
    exchange: str
    side: Optional[str] = None  # 'buy' or 'sell'

class VolumeLiquidity(BaseModel):
    """Volume and liquidity data model."""
    symbol: str
    volume_24h: float
    liquidity: Optional[float] = None
    timestamp: datetime
    exchange: str

class FundingRate(BaseModel):
    """Funding rate data model."""
    symbol: str
    funding_rate: float
    funding_time: Optional[datetime] = None
    next_funding_time: Optional[datetime] = None
    funding_interval: Optional[int] = None
    predicted_funding_rate: Optional[float] = None
    timestamp: datetime
    exchange: str

class OpenInterest(BaseModel):
    """Open interest data model."""
    symbol: str
    open_interest: float
    long_short_ratio: Optional[float] = None
    long_interest: Optional[float] = None
    short_interest: Optional[float] = None
    interest_value: Optional[float] = None
    top_trader_long_short_ratio: Optional[float] = None
    retail_long_short_ratio: Optional[float] = None
    timestamp: datetime
    exchange: str

class HistoricalData(BaseModel):
    """Historical OHLCV data model."""
    symbol: str
    timeframe: str  # '1m', '5m', '15m', '30m', '1h', '4h', '1d', '1w'
    timestamp: datetime  # Candle start time
    open: float
    high: float
    low: float
    close: float
    volume: float
    exchange: str

class HistoricalTrade(BaseModel):
    """Historical trade data model."""
    symbol: str
    timestamp: datetime
    price: float
    volume: float
    side: Optional[str] = None  # 'buy' or 'sell'
    trade_id: Optional[str] = None
    exchange: str

class WebSocketMessage(BaseModel):
    """Generic WebSocket message model."""
    data_type: DataType
    data: Union[MarketData, OrderBookData, TickPrice, VolumeLiquidity, FundingRate, OpenInterest, HistoricalData, HistoricalTrade]
    # Kraken (and others) may send list-formatted payloads; allow any raw type
    raw_message: Any
    exchange: str
    timestamp: datetime = Field(default_factory=datetime.now)
