"""
Smart-0DTE-System Market Data Models

This module defines SQLAlchemy models for market data including
tickers, market snapshots, and options chains.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Column, Integer, String, DateTime, Date, Numeric, Boolean, 
    BigInteger, Text, ForeignKey, Index, CheckConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Ticker(Base):
    """Model for supported tickers/symbols."""
    
    __tablename__ = "tickers"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    exchange = Column(String(20), nullable=False)
    sector = Column(String(100))
    industry = Column(String(100))
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    options_available = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    market_data_snapshots = relationship("MarketDataSnapshot", back_populates="ticker")
    options_chains = relationship("OptionsChain", back_populates="underlying_ticker")
    signals = relationship("Signal", back_populates="ticker")
    trades = relationship("Trade", back_populates="ticker")
    daily_pnl = relationship("DailyPnL", back_populates="ticker")
    
    def __repr__(self):
        return f"<Ticker(symbol='{self.symbol}', name='{self.name}')>"


class MarketDataSnapshot(Base):
    """Model for real-time market data snapshots."""
    
    __tablename__ = "market_data_snapshots"
    
    id = Column(BigInteger, primary_key=True, index=True)
    ticker_id = Column(Integer, ForeignKey("tickers.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    price = Column(Numeric(10, 4), nullable=False)
    bid = Column(Numeric(10, 4))
    ask = Column(Numeric(10, 4))
    volume = Column(BigInteger)
    open_price = Column(Numeric(10, 4))
    high_price = Column(Numeric(10, 4))
    low_price = Column(Numeric(10, 4))
    previous_close = Column(Numeric(10, 4))
    change_amount = Column(Numeric(10, 4))
    change_percent = Column(Numeric(8, 4))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    ticker = relationship("Ticker", back_populates="market_data_snapshots")
    
    # Indexes
    __table_args__ = (
        Index("idx_market_data_ticker_timestamp", "ticker_id", "timestamp"),
        Index("idx_market_data_timestamp", "timestamp"),
        CheckConstraint("price > 0", name="check_positive_price"),
        CheckConstraint("volume >= 0", name="check_non_negative_volume"),
    )
    
    def __repr__(self):
        return f"<MarketDataSnapshot(ticker_id={self.ticker_id}, price={self.price}, timestamp='{self.timestamp}')>"


class OptionsChain(Base):
    """Model for options chain data."""
    
    __tablename__ = "options_chains"
    
    id = Column(BigInteger, primary_key=True, index=True)
    underlying_ticker_id = Column(Integer, ForeignKey("tickers.id"), nullable=False, index=True)
    expiration_date = Column(Date, nullable=False, index=True)
    strike_price = Column(Numeric(10, 4), nullable=False)
    option_type = Column(String(4), nullable=False)  # 'call' or 'put'
    symbol = Column(String(50), nullable=False, index=True)
    bid = Column(Numeric(8, 4))
    ask = Column(Numeric(8, 4))
    last_price = Column(Numeric(8, 4))
    volume = Column(Integer, default=0)
    open_interest = Column(Integer, default=0)
    implied_volatility = Column(Numeric(8, 6))
    delta = Column(Numeric(8, 6))
    gamma = Column(Numeric(8, 6))
    theta = Column(Numeric(8, 6))
    vega = Column(Numeric(8, 6))
    rho = Column(Numeric(8, 6))
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    underlying_ticker = relationship("Ticker", back_populates="options_chains")
    signal_legs = relationship("SignalLeg", back_populates="option_chain")
    trade_legs = relationship("TradeLeg", back_populates="option_chain")
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_options_underlying_exp_strike", "underlying_ticker_id", "expiration_date", "strike_price"),
        Index("idx_options_symbol", "symbol"),
        Index("idx_options_timestamp", "timestamp"),
        Index("idx_options_expiration", "expiration_date"),
        CheckConstraint("option_type IN ('call', 'put')", name="check_option_type"),
        CheckConstraint("strike_price > 0", name="check_positive_strike"),
        CheckConstraint("volume >= 0", name="check_non_negative_volume"),
        CheckConstraint("open_interest >= 0", name="check_non_negative_oi"),
    )
    
    @property
    def is_call(self) -> bool:
        """Check if this is a call option."""
        return self.option_type.lower() == "call"
    
    @property
    def is_put(self) -> bool:
        """Check if this is a put option."""
        return self.option_type.lower() == "put"
    
    @property
    def days_to_expiration(self) -> int:
        """Calculate days to expiration."""
        today = date.today()
        return (self.expiration_date - today).days
    
    @property
    def is_0dte(self) -> bool:
        """Check if this is a 0DTE option."""
        return self.days_to_expiration == 0
    
    @property
    def mid_price(self) -> Optional[Decimal]:
        """Calculate mid price from bid/ask."""
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2
        return self.last_price
    
    @property
    def bid_ask_spread(self) -> Optional[Decimal]:
        """Calculate bid-ask spread."""
        if self.bid is not None and self.ask is not None:
            return self.ask - self.bid
        return None
    
    @property
    def bid_ask_spread_percent(self) -> Optional[Decimal]:
        """Calculate bid-ask spread as percentage of mid price."""
        spread = self.bid_ask_spread
        mid = self.mid_price
        if spread is not None and mid is not None and mid > 0:
            return (spread / mid) * 100
        return None
    
    def __repr__(self):
        return f"<OptionsChain(symbol='{self.symbol}', strike={self.strike_price}, type='{self.option_type}')>"


class VIXData(Base):
    """Model for VIX (volatility index) data."""
    
    __tablename__ = "vix_data"
    
    id = Column(BigInteger, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    vix_value = Column(Numeric(8, 4), nullable=False)
    vix_change = Column(Numeric(8, 4))
    vix_change_percent = Column(Numeric(8, 4))
    regime_type = Column(String(20))  # 'low', 'normal', 'high', 'extreme'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("vix_value >= 0", name="check_non_negative_vix"),
        CheckConstraint("regime_type IN ('low', 'normal', 'high', 'extreme')", name="check_regime_type"),
    )
    
    @property
    def is_low_volatility(self) -> bool:
        """Check if VIX indicates low volatility (< 15)."""
        return self.vix_value < 15
    
    @property
    def is_normal_volatility(self) -> bool:
        """Check if VIX indicates normal volatility (15-25)."""
        return 15 <= self.vix_value <= 25
    
    @property
    def is_high_volatility(self) -> bool:
        """Check if VIX indicates high volatility (25-35)."""
        return 25 < self.vix_value <= 35
    
    @property
    def is_extreme_volatility(self) -> bool:
        """Check if VIX indicates extreme volatility (> 35)."""
        return self.vix_value > 35
    
    def __repr__(self):
        return f"<VIXData(value={self.vix_value}, regime='{self.regime_type}', timestamp='{self.timestamp}')>"


class CorrelationData(Base):
    """Model for cross-ticker correlation data."""
    
    __tablename__ = "correlation_data"
    
    id = Column(BigInteger, primary_key=True, index=True)
    ticker_pair = Column(String(20), nullable=False, index=True)  # e.g., 'SPY_QQQ'
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    correlation_1d = Column(Numeric(8, 6))  # 1-day correlation
    correlation_7d = Column(Numeric(8, 6))  # 7-day rolling correlation
    correlation_30d = Column(Numeric(8, 6))  # 30-day rolling correlation
    divergence_score = Column(Numeric(8, 6))  # Divergence from historical norm
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_correlation_pair_timestamp", "ticker_pair", "timestamp"),
        CheckConstraint("correlation_1d >= -1 AND correlation_1d <= 1", name="check_correlation_1d_range"),
        CheckConstraint("correlation_7d >= -1 AND correlation_7d <= 1", name="check_correlation_7d_range"),
        CheckConstraint("correlation_30d >= -1 AND correlation_30d <= 1", name="check_correlation_30d_range"),
    )
    
    @property
    def is_highly_correlated(self) -> bool:
        """Check if tickers are highly correlated (> 0.8)."""
        return self.correlation_1d is not None and self.correlation_1d > 0.8
    
    @property
    def is_negatively_correlated(self) -> bool:
        """Check if tickers are negatively correlated (< -0.3)."""
        return self.correlation_1d is not None and self.correlation_1d < -0.3
    
    @property
    def is_diverging(self) -> bool:
        """Check if correlation is diverging from historical norm."""
        return self.divergence_score is not None and abs(self.divergence_score) > 0.3
    
    def __repr__(self):
        return f"<CorrelationData(pair='{self.ticker_pair}', correlation={self.correlation_1d})>"


class MarketRegime(Base):
    """Model for market regime detection data."""
    
    __tablename__ = "market_regimes"
    
    id = Column(BigInteger, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    regime_type = Column(String(20), nullable=False)  # 'bull', 'bear', 'sideways', 'volatile'
    confidence_score = Column(Numeric(4, 3), nullable=False)
    vix_level = Column(Numeric(8, 4))
    correlation_strength = Column(Numeric(8, 6))
    volume_profile = Column(String(20))  # 'low', 'normal', 'high', 'extreme'
    trend_direction = Column(String(10))  # 'up', 'down', 'sideways'
    volatility_regime = Column(String(20))  # 'low', 'normal', 'high', 'extreme'
    adaptation_factor = Column(Numeric(4, 3), default=1.0)  # Risk adjustment factor
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("confidence_score >= 0 AND confidence_score <= 1", name="check_confidence_range"),
        CheckConstraint("adaptation_factor > 0", name="check_positive_adaptation"),
        CheckConstraint("regime_type IN ('bull', 'bear', 'sideways', 'volatile')", name="check_regime_type"),
        CheckConstraint("volume_profile IN ('low', 'normal', 'high', 'extreme')", name="check_volume_profile"),
        CheckConstraint("trend_direction IN ('up', 'down', 'sideways')", name="check_trend_direction"),
        CheckConstraint("volatility_regime IN ('low', 'normal', 'high', 'extreme')", name="check_volatility_regime"),
    )
    
    @property
    def is_bull_market(self) -> bool:
        """Check if current regime is bullish."""
        return self.regime_type == "bull"
    
    @property
    def is_bear_market(self) -> bool:
        """Check if current regime is bearish."""
        return self.regime_type == "bear"
    
    @property
    def is_high_volatility(self) -> bool:
        """Check if current regime has high volatility."""
        return self.volatility_regime in ["high", "extreme"]
    
    @property
    def requires_risk_reduction(self) -> bool:
        """Check if regime requires risk reduction."""
        return self.adaptation_factor < 0.8 or self.volatility_regime == "extreme"
    
    def __repr__(self):
        return f"<MarketRegime(type='{self.regime_type}', confidence={self.confidence_score})>"

