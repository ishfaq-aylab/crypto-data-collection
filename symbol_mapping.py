"""Symbol mapping system for different exchanges."""

from typing import Dict, List, Optional

class SymbolMapper:
    """Maps standard symbols to exchange-specific formats."""
    
    # Standard symbols we want to support - BTC pairs with USD-based stablecoins only
    STANDARD_SYMBOLS = ['BTCUSDT', 'BTCUSDC', 'BTCUSD', 'BTCTUSD', 'BTCFDUSD', 'BTCGUSD']
    
    # Exchange-specific symbol mappings
    EXCHANGE_SYMBOLS = {
        'binance': {
            'BTCUSDT': 'BTCUSDT',
            'BTCUSDC': 'BTCUSDC',
            'BTCUSD': 'BTCUSDT',  # Use USDT as proxy for USD
            'BTCTUSD': 'BTCTUSD',
            'BTCFDUSD': 'BTCFDUSD',
            'BTCGUSD': 'BTCUSDT'  # Use USDT as proxy for GUSD
        },
        'bybit': {
            'BTCUSDT': 'BTCUSDT',
            'BTCUSDC': 'BTCUSDC',
            'BTCUSD': 'BTCUSDT',  # Use USDT as proxy for USD
            'BTCTUSD': 'BTCTUSD',
            'BTCFDUSD': 'BTCUSDT',  # Use USDT as proxy for FDUSD
            'BTCGUSD': 'BTCUSDT'  # Use USDT as proxy for GUSD
        },
        'kraken': {
            'BTCUSDT': 'XBT/USDT',  # Bitcoin/USDT (wsname)
            'BTCUSDC': 'XBT/USDC',  # Bitcoin/USDC (wsname)
            'BTCUSD': 'XBT/USD',    # Bitcoin/USD (wsname)
            'BTCTUSD': 'XBT/USD',   # Use USD as proxy for TUSD
            'BTCFDUSD': 'XBT/USD',  # Use USD as proxy for FDUSD
            'BTCGUSD': 'XBT/USD'    # Use USD as proxy for GUSD
        },
        'okx': {
            'BTCUSDT': 'BTC-USDT',
            'BTCUSDC': 'BTC-USDC',
            'BTCUSD': 'BTC-USDT',   # Use USDT as proxy for USD
            'BTCTUSD': 'BTC-USDT',  # Use USDT as proxy for TUSD
            'BTCFDUSD': 'BTC-USDT', # Use USDT as proxy for FDUSD
            'BTCGUSD': 'BTC-USDT'   # Use USDT as proxy for GUSD
        },
        'gate': {
            'BTCUSDT': 'BTC_USDT',
            'BTCUSDC': 'BTC_USDC',
            'BTCUSD': 'BTC_USD1',   # Use USD1 as proxy for USD
            'BTCTUSD': 'BTC_USDT',  # Use USDT as proxy for TUSD
            'BTCFDUSD': 'BTC_USDT', # Use USDT as proxy for FDUSD
            'BTCGUSD': 'BTC_GUSD'
        }
    }
    
    # Reverse mappings for converting back to standard format
    REVERSE_MAPPINGS = {
        'binance': {v: k for k, v in EXCHANGE_SYMBOLS['binance'].items()},
        'bybit': {v: k for k, v in EXCHANGE_SYMBOLS['bybit'].items()},
        'kraken': {v: k for k, v in EXCHANGE_SYMBOLS['kraken'].items()},
        'okx': {v: k for k, v in EXCHANGE_SYMBOLS['okx'].items()},
        'gate': {v: k for k, v in EXCHANGE_SYMBOLS['gate'].items()}
    }
    
    @classmethod
    def get_exchange_symbols(cls, exchange: str, standard_symbols: List[str]) -> List[str]:
        """Convert standard symbols to exchange-specific format."""
        if exchange not in cls.EXCHANGE_SYMBOLS:
            return standard_symbols
        
        exchange_symbols = []
        for symbol in standard_symbols:
            if symbol in cls.EXCHANGE_SYMBOLS[exchange]:
                exchange_symbols.append(cls.EXCHANGE_SYMBOLS[exchange][symbol])
            else:
                # If symbol not found, try to use as-is
                exchange_symbols.append(symbol)
        
        return exchange_symbols
    
    @classmethod
    def get_standard_symbol(cls, exchange: str, exchange_symbol: str) -> str:
        """Convert exchange-specific symbol back to standard format."""
        if exchange not in cls.REVERSE_MAPPINGS:
            return exchange_symbol
        
        return cls.REVERSE_MAPPINGS[exchange].get(exchange_symbol, exchange_symbol)
    
    @classmethod
    def get_supported_symbols(cls, exchange: str) -> List[str]:
        """Get list of supported symbols for an exchange."""
        if exchange not in cls.EXCHANGE_SYMBOLS:
            return []
        
        return list(cls.EXCHANGE_SYMBOLS[exchange].keys())
    
    @classmethod
    def is_symbol_supported(cls, exchange: str, symbol: str) -> bool:
        """Check if a symbol is supported by an exchange."""
        return symbol in cls.get_supported_symbols(exchange)
    
    @classmethod
    def get_all_exchange_symbols(cls, standard_symbols: List[str]) -> Dict[str, List[str]]:
        """Get exchange-specific symbols for all exchanges."""
        result = {}
        for exchange in cls.EXCHANGE_SYMBOLS.keys():
            result[exchange] = cls.get_exchange_symbols(exchange, standard_symbols)
        return result

# Convenience functions
def get_exchange_symbols(exchange: str, standard_symbols: List[str]) -> List[str]:
    """Convert standard symbols to exchange-specific format."""
    return SymbolMapper.get_exchange_symbols(exchange, standard_symbols)

def get_standard_symbol(exchange: str, exchange_symbol: str) -> str:
    """Convert exchange-specific symbol back to standard format."""
    return SymbolMapper.get_standard_symbol(exchange, exchange_symbol)

def get_supported_symbols(exchange: str) -> List[str]:
    """Get list of supported symbols for an exchange."""
    return SymbolMapper.get_supported_symbols(exchange)

def is_symbol_supported(exchange: str, symbol: str) -> bool:
    """Check if a symbol is supported by an exchange."""
    return SymbolMapper.is_symbol_supported(exchange, symbol)
