"""Base WebSocket client for cryptocurrency exchanges."""

import asyncio
import json
import websockets
from abc import ABC, abstractmethod
from typing import Dict, List, Callable, Optional, Any
from datetime import datetime
from loguru import logger
import aiohttp

from models import WebSocketMessage, DataType
from config import Config

class BaseWebSocketClient(ABC):
    """Base class for WebSocket clients."""
    
    def __init__(self, exchange_name: str, symbols: List[str] = None):
        self.exchange_name = exchange_name
        self.symbols = symbols or []
        self.websocket = None
        self.is_connected = False
        self.reconnect_attempts = 0
        self.message_handler = None
        self.data_handlers: Dict[DataType, List[Callable]] = {
            DataType.MARKET_DATA: [],
            DataType.ORDER_BOOK_DATA: [],
            DataType.TICK_PRICES: [],
            DataType.VOLUME_LIQUIDITY: [],
            DataType.FUNDING_RATES: [],
            DataType.OPEN_INTEREST: []
        }
        
    @abstractmethod
    def get_websocket_url(self) -> str:
        """Get the WebSocket URL for the exchange."""
        pass
    
    @abstractmethod
    def get_subscription_message(self) -> Dict[str, Any]:
        """Get the subscription message for the exchange."""
        pass
    
    @abstractmethod
    def parse_message(self, message: Dict[str, Any]) -> Optional[WebSocketMessage]:
        """Parse incoming WebSocket message."""
        pass
    
    def add_data_handler(self, data_type: DataType, handler: Callable):
        """Add a data handler for specific data type."""
        self.data_handlers[data_type].append(handler)
    
    def remove_data_handler(self, data_type: DataType, handler: Callable):
        """Remove a data handler."""
        if handler in self.data_handlers[data_type]:
            self.data_handlers[data_type].remove(handler)
    
    async def _notify_handlers(self, message: WebSocketMessage):
        """Notify all handlers for the data type."""
        # Call general message handler if set
        if self.message_handler:
            try:
                if asyncio.iscoroutinefunction(self.message_handler):
                    await self.message_handler(message)
                else:
                    self.message_handler(message)
            except Exception as e:
                logger.error(f"Error in general message handler: {e}")
        
        # Call specific data type handlers
        handlers = self.data_handlers.get(message.data_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)
            except Exception as e:
                logger.error(f"Error in data handler: {e}")
    
    async def connect(self):
        """Connect to the WebSocket."""
        try:
            url = self.get_websocket_url()
            logger.info(f"Connecting to {self.exchange_name} WebSocket: {url}")
            
            self.websocket = await websockets.connect(
                url,
                ping_interval=20,
                ping_timeout=10
            )
            
            self.is_connected = True
            self.reconnect_attempts = 0
            logger.info(f"Connected to {self.exchange_name} WebSocket")
            
            # Send subscription message
            subscription_msg = self.get_subscription_message()
            if subscription_msg:
                await self.websocket.send(json.dumps(subscription_msg))
                logger.info(f"Sent subscription message to {self.exchange_name}")
            
            # Send additional subscriptions if method exists (for Gate.io)
            if hasattr(self, 'send_all_subscriptions'):
                await self.send_all_subscriptions()
            
        except Exception as e:
            logger.error(f"Failed to connect to {self.exchange_name}: {e}")
            self.is_connected = False
            raise
    
    async def disconnect(self):
        """Disconnect from the WebSocket."""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info(f"Disconnected from {self.exchange_name} WebSocket")
    
    async def listen(self):
        """Listen for messages from the WebSocket."""
        if not self.is_connected:
            raise ConnectionError("Not connected to WebSocket")
        
        logger.info(f"Starting to listen for messages from {self.exchange_name}")
        
        try:
            message_count = 0
            async for message in self.websocket:
                message_count += 1
                logger.debug(f"Received raw message #{message_count} from {self.exchange_name}: {str(message)[:100]}...")
                
                try:
                    data = json.loads(message)
                    logger.debug(f"Parsed JSON message from {self.exchange_name}")
                    parsed_message = self.parse_message(data)
                    
                    if parsed_message:
                        logger.debug(f"Successfully parsed message from {self.exchange_name}: {parsed_message.data_type}")
                        await self._notify_handlers(parsed_message)
                    else:
                        logger.debug(f"Message parsing returned None for {self.exchange_name}")
                        
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON message from {self.exchange_name}: {e}")
                except Exception as e:
                    logger.error(f"Error processing message from {self.exchange_name}: {e}")
                    
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"WebSocket connection closed for {self.exchange_name}")
            self.is_connected = False
        except Exception as e:
            logger.error(f"Error in WebSocket listener for {self.exchange_name}: {e}")
            self.is_connected = False
    
    async def reconnect(self):
        """Reconnect to the WebSocket with exponential backoff."""
        if self.reconnect_attempts >= Config.MAX_RECONNECT_ATTEMPTS:
            logger.error(f"Max reconnection attempts reached for {self.exchange_name}")
            return False
        
        self.reconnect_attempts += 1
        wait_time = min(Config.WS_RECONNECT_INTERVAL * (2 ** self.reconnect_attempts), 300)
        
        logger.info(f"Reconnecting to {self.exchange_name} in {wait_time} seconds (attempt {self.reconnect_attempts})")
        await asyncio.sleep(wait_time)
        
        try:
            await self.connect()
            return True
        except Exception as e:
            logger.error(f"Reconnection failed for {self.exchange_name}: {e}")
            return False
    
    async def run(self):
        """Main run loop with automatic reconnection."""
        while True:
            try:
                if not self.is_connected:
                    await self.connect()
                
                await self.listen()
                
            except Exception as e:
                logger.error(f"Error in run loop for {self.exchange_name}: {e}")
                self.is_connected = False
                
                if not await self.reconnect():
                    break
