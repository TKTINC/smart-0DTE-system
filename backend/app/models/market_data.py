"""
Market Data Models for Smart-0DTE-System
Optimized for SPY, QQQ, IWM, and VIX trading

Focused data architecture with minimal storage footprint
and maximum query performance for 0DTE options trading.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum
import json

class InstrumentType(Enum):
    """Supported instrument types"""
    ETF = "etf"
    VIX = "vix"

class Symbol(Enum):
    """Supported trading symbols - focused on major ETFs + VIX"""
    SPY = "SPY"
    QQQ = "QQQ" 
    IWM = "IWM"
    VIX = "VIX"

@dataclass
class MarketDataPoint:
    """
    Optimized market data structure for real-time processing
    Minimal fields for maximum performance
    """
    symbol: Symbol
    timestamp: datetime
    price: float
    volume: int
    bid: Optional[float] = None
    ask: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol.value,
            'timestamp': self.timestamp.isoformat(),
            'price': self.price,
            'volume': self.volume,
            'bid': self.bid,
            'ask': self.ask
        }

@dataclass
class OHLCData:
    """
    OHLC data for chart visualization and technical analysis
    Time-series optimized for 1min, 5min, 15min, 1hour, 1day intervals
    """
    symbol: Symbol
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    interval: str  # '1m', '5m', '15m', '1h', '1d'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol.value,
            'timestamp': self.timestamp.isoformat(),
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume,
            'interval': self.interval
        }

@dataclass
class OptionsData:
    """
    Options chain data for 0DTE trading
    Focused on essential fields for quick decision making
    """
    underlying_symbol: Symbol
    timestamp: datetime
    expiration: datetime
    strike: float
    option_type: str  # 'call' or 'put'
    bid: float
    ask: float
    last: float
    volume: int
    open_interest: int
    implied_volatility: float
    delta: Optional[float] = None
    gamma: Optional[float] = None
    theta: Optional[float] = None
    vega: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'underlying_symbol': self.underlying_symbol.value,
            'timestamp': self.timestamp.isoformat(),
            'expiration': self.expiration.isoformat(),
            'strike': self.strike,
            'option_type': self.option_type,
            'bid': self.bid,
            'ask': self.ask,
            'last': self.last,
            'volume': self.volume,
            'open_interest': self.open_interest,
            'implied_volatility': self.implied_volatility,
            'delta': self.delta,
            'gamma': self.gamma,
            'theta': self.theta,
            'vega': self.vega
        }

@dataclass
class VIXData:
    """
    Specialized VIX data structure for volatility analysis
    Critical for 0DTE options trading decisions
    """
    timestamp: datetime
    vix_level: float
    vix_change: float
    vix_change_percent: float
    term_structure: Dict[str, float]  # VIX9D, VIX, VIX3M, VIX6M
    regime: str  # 'low', 'normal', 'elevated', 'high'
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'vix_level': self.vix_level,
            'vix_change': self.vix_change,
            'vix_change_percent': self.vix_change_percent,
            'term_structure': self.term_structure,
            'regime': self.regime
        }

@dataclass
class CorrelationData:
    """
    Inter-ETF correlation analysis for portfolio optimization
    Essential for understanding market regime changes
    """
    timestamp: datetime
    spy_qqq_correlation: float
    spy_iwm_correlation: float
    qqq_iwm_correlation: float
    spy_vix_correlation: float
    qqq_vix_correlation: float
    iwm_vix_correlation: float
    regime_change_probability: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'timestamp': self.timestamp.isoformat(),
            'spy_qqq_correlation': self.spy_qqq_correlation,
            'spy_iwm_correlation': self.spy_iwm_correlation,
            'qqq_iwm_correlation': self.qqq_iwm_correlation,
            'spy_vix_correlation': self.spy_vix_correlation,
            'qqq_vix_correlation': self.qqq_vix_correlation,
            'iwm_vix_correlation': self.iwm_vix_correlation,
            'regime_change_probability': self.regime_change_probability
        }

class MarketDataValidator:
    """
    Data validation for incoming market data
    Ensures data quality and consistency
    """
    
    @staticmethod
    def validate_price_data(data: MarketDataPoint) -> bool:
        """Validate basic price data"""
        if data.price <= 0:
            return False
        if data.volume < 0:
            return False
        if data.bid and data.ask and data.bid > data.ask:
            return False
        return True
    
    @staticmethod
    def validate_ohlc_data(data: OHLCData) -> bool:
        """Validate OHLC data consistency"""
        if data.high < max(data.open, data.close):
            return False
        if data.low > min(data.open, data.close):
            return False
        if data.volume < 0:
            return False
        return True
    
    @staticmethod
    def validate_options_data(data: OptionsData) -> bool:
        """Validate options data"""
        if data.strike <= 0:
            return False
        if data.bid < 0 or data.ask < 0:
            return False
        if data.bid > data.ask:
            return False
        if data.implied_volatility < 0:
            return False
        return True

# Database schema constants for efficient storage
MARKET_DATA_SCHEMA = {
    'market_data_realtime': {
        'symbol': 'VARCHAR(10)',
        'timestamp': 'TIMESTAMP WITH TIME ZONE',
        'price': 'DECIMAL(10,4)',
        'volume': 'BIGINT',
        'bid': 'DECIMAL(10,4)',
        'ask': 'DECIMAL(10,4)',
        'PRIMARY KEY': '(symbol, timestamp)'
    },
    'ohlc_data': {
        'symbol': 'VARCHAR(10)',
        'timestamp': 'TIMESTAMP WITH TIME ZONE',
        'interval': 'VARCHAR(5)',
        'open': 'DECIMAL(10,4)',
        'high': 'DECIMAL(10,4)',
        'low': 'DECIMAL(10,4)',
        'close': 'DECIMAL(10,4)',
        'volume': 'BIGINT',
        'PRIMARY KEY': '(symbol, timestamp, interval)'
    },
    'options_data': {
        'underlying_symbol': 'VARCHAR(10)',
        'timestamp': 'TIMESTAMP WITH TIME ZONE',
        'expiration': 'DATE',
        'strike': 'DECIMAL(10,2)',
        'option_type': 'VARCHAR(4)',
        'bid': 'DECIMAL(8,4)',
        'ask': 'DECIMAL(8,4)',
        'last': 'DECIMAL(8,4)',
        'volume': 'INTEGER',
        'open_interest': 'INTEGER',
        'implied_volatility': 'DECIMAL(6,4)',
        'delta': 'DECIMAL(6,4)',
        'gamma': 'DECIMAL(8,6)',
        'theta': 'DECIMAL(8,6)',
        'vega': 'DECIMAL(8,6)',
        'PRIMARY KEY': '(underlying_symbol, timestamp, expiration, strike, option_type)'
    },
    'vix_data': {
        'timestamp': 'TIMESTAMP WITH TIME ZONE PRIMARY KEY',
        'vix_level': 'DECIMAL(6,2)',
        'vix_change': 'DECIMAL(6,2)',
        'vix_change_percent': 'DECIMAL(6,2)',
        'term_structure': 'JSONB',
        'regime': 'VARCHAR(20)'
    },
    'correlation_data': {
        'timestamp': 'TIMESTAMP WITH TIME ZONE PRIMARY KEY',
        'spy_qqq_correlation': 'DECIMAL(6,4)',
        'spy_iwm_correlation': 'DECIMAL(6,4)',
        'qqq_iwm_correlation': 'DECIMAL(6,4)',
        'spy_vix_correlation': 'DECIMAL(6,4)',
        'qqq_vix_correlation': 'DECIMAL(6,4)',
        'iwm_vix_correlation': 'DECIMAL(6,4)',
        'regime_change_probability': 'DECIMAL(6,4)'
    }
}

# Optimized indexes for fast queries
DATABASE_INDEXES = [
    'CREATE INDEX idx_market_data_symbol_time ON market_data_realtime(symbol, timestamp DESC)',
    'CREATE INDEX idx_ohlc_symbol_interval_time ON ohlc_data(symbol, interval, timestamp DESC)',
    'CREATE INDEX idx_options_underlying_exp ON options_data(underlying_symbol, expiration, timestamp DESC)',
    'CREATE INDEX idx_vix_timestamp ON vix_data(timestamp DESC)',
    'CREATE INDEX idx_correlation_timestamp ON correlation_data(timestamp DESC)'
]

