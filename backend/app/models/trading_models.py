"""
Smart-0DTE-System Trading Models

This module defines data models for trading operations, IBKR integration,
and strategy management.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from datetime import datetime
from enum import Enum as PyEnum
import uuid

from app.core.database import Base


class OrderStatus(PyEnum):
    """Order status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    PARTIAL = "partial"


class StrategyStatus(PyEnum):
    """Strategy status enumeration."""
    PENDING = "pending"
    ACTIVE = "active"
    CLOSED = "closed"
    CANCELLED = "cancelled"


class OptionType(PyEnum):
    """Option type enumeration."""
    CALL = "call"
    PUT = "put"


class OrderAction(PyEnum):
    """Order action enumeration."""
    BUY = "buy"
    SELL = "sell"


class StrategyType(PyEnum):
    """Strategy type enumeration."""
    BULL_CALL_SPREAD = "bull_call_spread"
    BEAR_PUT_SPREAD = "bear_put_spread"
    IRON_CONDOR = "iron_condor"
    IRON_BUTTERFLY = "iron_butterfly"
    STRADDLE = "straddle"
    STRANGLE = "strangle"
    COVERED_CALL = "covered_call"
    PROTECTIVE_PUT = "protective_put"
    COLLAR = "collar"
    CALENDAR_SPREAD = "calendar_spread"


class IBKRAccount(Base):
    """IBKR account information model."""
    __tablename__ = "ibkr_accounts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(String(50), unique=True, nullable=False, index=True)
    account_type = Column(String(20), nullable=False)  # CASH, MARGIN, etc.
    base_currency = Column(String(3), nullable=False, default='USD')
    
    # Account values
    net_liquidation = Column(Float, default=0.0)
    total_cash_value = Column(Float, default=0.0)
    buying_power = Column(Float, default=0.0)
    excess_liquidity = Column(Float, default=0.0)
    maintenance_margin = Column(Float, default=0.0)
    
    # Risk metrics
    day_trades_remaining = Column(Integer, default=0)
    is_pdt = Column(Boolean, default=False)  # Pattern Day Trader
    
    # Status
    is_active = Column(Boolean, default=True)
    last_updated = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    orders = relationship("IBKROrder", back_populates="account")
    positions = relationship("IBKRPosition", back_populates="account")
    trades = relationship("Trade", back_populates="account")


class IBKROrder(Base):
    """IBKR order model."""
    __tablename__ = "ibkr_orders"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(Integer, unique=True, nullable=False, index=True)  # IBKR order ID
    account_id = Column(UUID(as_uuid=True), ForeignKey("ibkr_accounts.id"), nullable=False)
    
    # Contract details
    symbol = Column(String(10), nullable=False, index=True)
    sec_type = Column(String(10), nullable=False)  # STK, OPT, etc.
    exchange = Column(String(20), default='SMART')
    currency = Column(String(3), default='USD')
    
    # Option-specific fields
    expiration = Column(String(8))  # YYYYMMDD format
    strike = Column(Float)
    option_type = Column(Enum(OptionType))
    
    # Order details
    action = Column(Enum(OrderAction), nullable=False)
    order_type = Column(String(10), nullable=False)  # MKT, LMT, STP, etc.
    total_quantity = Column(Integer, nullable=False)
    limit_price = Column(Float)
    stop_price = Column(Float)
    time_in_force = Column(String(10), default='DAY')
    
    # Status and execution
    status = Column(Enum(OrderStatus), default=OrderStatus.PENDING)
    filled_quantity = Column(Integer, default=0)
    remaining_quantity = Column(Integer, default=0)
    avg_fill_price = Column(Float, default=0.0)
    commission = Column(Float, default=0.0)
    
    # Strategy association
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("options_strategies.id"))
    signal_id = Column(String(100))  # Reference to signal that generated this order
    
    # Timestamps
    submitted_at = Column(DateTime, default=datetime.utcnow)
    filled_at = Column(DateTime)
    cancelled_at = Column(DateTime)
    
    # Additional data
    error_message = Column(Text)
    ibkr_data = Column(JSONB)  # Store raw IBKR data
    
    # Relationships
    account = relationship("IBKRAccount", back_populates="orders")
    strategy = relationship("OptionsStrategy", back_populates="orders")
    executions = relationship("OrderExecution", back_populates="order")


class OrderExecution(Base):
    """Order execution details model."""
    __tablename__ = "order_executions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    order_id = Column(UUID(as_uuid=True), ForeignKey("ibkr_orders.id"), nullable=False)
    execution_id = Column(String(50), unique=True, nullable=False)  # IBKR execution ID
    
    # Execution details
    shares = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    side = Column(String(10), nullable=False)  # BOT, SLD
    time = Column(DateTime, nullable=False)
    
    # Commission and fees
    commission = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    
    # Additional data
    ibkr_data = Column(JSONB)
    
    # Relationships
    order = relationship("IBKROrder", back_populates="executions")


class IBKRPosition(Base):
    """IBKR position model."""
    __tablename__ = "ibkr_positions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    account_id = Column(UUID(as_uuid=True), ForeignKey("ibkr_accounts.id"), nullable=False)
    
    # Contract details
    symbol = Column(String(10), nullable=False, index=True)
    sec_type = Column(String(10), nullable=False)
    exchange = Column(String(20), default='SMART')
    currency = Column(String(3), default='USD')
    
    # Option-specific fields
    expiration = Column(String(8))
    strike = Column(Float)
    option_type = Column(Enum(OptionType))
    
    # Position details
    position = Column(Float, nullable=False)  # Number of shares/contracts
    avg_cost = Column(Float, default=0.0)
    market_price = Column(Float, default=0.0)
    market_value = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    
    # Strategy association
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("options_strategies.id"))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow)
    
    # Additional data
    ibkr_data = Column(JSONB)
    
    # Relationships
    account = relationship("IBKRAccount", back_populates="positions")
    strategy = relationship("OptionsStrategy", back_populates="positions")


class OptionsStrategy(Base):
    """Options strategy model."""
    __tablename__ = "options_strategies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(String(100), unique=True, nullable=False, index=True)
    
    # Strategy details
    symbol = Column(String(10), nullable=False, index=True)
    strategy_type = Column(Enum(StrategyType), nullable=False)
    underlying_price = Column(Float, nullable=False)
    expiration = Column(String(10), nullable=False)  # YYYY-MM-DD format
    
    # Financial metrics
    net_premium = Column(Float, default=0.0)
    max_profit = Column(Float, default=0.0)
    max_loss = Column(Float, default=0.0)
    profit_target = Column(Float, default=0.0)
    stop_loss = Column(Float, default=0.0)
    
    # Current P&L
    current_value = Column(Float, default=0.0)
    unrealized_pnl = Column(Float, default=0.0)
    realized_pnl = Column(Float, default=0.0)
    
    # Status and tracking
    status = Column(Enum(StrategyStatus), default=StrategyStatus.PENDING)
    confidence = Column(Float, default=0.0)
    signal_id = Column(String(100))  # Reference to generating signal
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    executed_at = Column(DateTime)
    closed_at = Column(DateTime)
    
    # Exit details
    close_reason = Column(String(50))  # profit_target, stop_loss, time_exit, manual
    
    # Additional data
    legs_data = Column(JSONB)  # Store strategy legs
    metadata = Column(JSONB)   # Additional strategy metadata
    
    # Relationships
    orders = relationship("IBKROrder", back_populates="strategy")
    positions = relationship("IBKRPosition", back_populates="strategy")
    legs = relationship("TradeLeg", back_populates="strategy")


class TradeLeg(Base):
    """Individual leg of an options strategy."""
    __tablename__ = "trade_legs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("options_strategies.id"), nullable=False)
    leg_number = Column(Integer, nullable=False)  # 1, 2, 3, 4 for multi-leg strategies
    
    # Contract details
    option_type = Column(Enum(OptionType), nullable=False)
    strike = Column(Float, nullable=False)
    action = Column(Enum(OrderAction), nullable=False)
    quantity = Column(Integer, nullable=False)
    
    # Pricing
    premium = Column(Float, nullable=False)
    fill_price = Column(Float, default=0.0)
    
    # Greeks (at entry)
    delta = Column(Float, default=0.0)
    gamma = Column(Float, default=0.0)
    theta = Column(Float, default=0.0)
    vega = Column(Float, default=0.0)
    rho = Column(Float, default=0.0)
    implied_volatility = Column(Float, default=0.0)
    
    # Status
    is_filled = Column(Boolean, default=False)
    fill_time = Column(DateTime)
    
    # Relationships
    strategy = relationship("OptionsStrategy", back_populates="legs")


class Trade(Base):
    """Complete trade record."""
    __tablename__ = "trades"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    trade_id = Column(String(100), unique=True, nullable=False, index=True)
    account_id = Column(UUID(as_uuid=True), ForeignKey("ibkr_accounts.id"), nullable=False)
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("options_strategies.id"), nullable=False)
    
    # Trade details
    symbol = Column(String(10), nullable=False, index=True)
    strategy_type = Column(Enum(StrategyType), nullable=False)
    
    # Entry details
    entry_time = Column(DateTime, nullable=False)
    entry_price = Column(Float, nullable=False)
    underlying_price_entry = Column(Float, nullable=False)
    
    # Exit details
    exit_time = Column(DateTime)
    exit_price = Column(Float, default=0.0)
    underlying_price_exit = Column(Float, default=0.0)
    
    # P&L
    gross_pnl = Column(Float, default=0.0)
    commission = Column(Float, default=0.0)
    net_pnl = Column(Float, default=0.0)
    
    # Performance metrics
    return_percentage = Column(Float, default=0.0)
    hold_time_minutes = Column(Integer, default=0)
    max_favorable_excursion = Column(Float, default=0.0)
    max_adverse_excursion = Column(Float, default=0.0)
    
    # Trade classification
    is_winner = Column(Boolean, default=False)
    exit_reason = Column(String(50))  # profit_target, stop_loss, time_exit, manual
    
    # Signal and AI data
    signal_id = Column(String(100))
    signal_confidence = Column(Float, default=0.0)
    ai_prediction_accuracy = Column(Float)  # How accurate was the AI prediction
    
    # Market conditions at entry
    vix_level = Column(Float, default=0.0)
    market_regime = Column(String(20))
    correlation_spy_qqq = Column(Float, default=0.0)
    correlation_spy_iwm = Column(Float, default=0.0)
    
    # Additional data
    metadata = Column(JSONB)
    
    # Relationships
    account = relationship("IBKRAccount", back_populates="trades")
    strategy = relationship("OptionsStrategy")


class TradingSession(Base):
    """Trading session tracking."""
    __tablename__ = "trading_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    
    # Session statistics
    total_trades = Column(Integer, default=0)
    winning_trades = Column(Integer, default=0)
    losing_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    
    # P&L
    gross_pnl = Column(Float, default=0.0)
    commission = Column(Float, default=0.0)
    net_pnl = Column(Float, default=0.0)
    
    # Volume
    total_volume = Column(Integer, default=0)
    total_premium = Column(Float, default=0.0)
    
    # Performance metrics
    sharpe_ratio = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    
    # Market conditions
    avg_vix = Column(Float, default=0.0)
    dominant_regime = Column(String(20))
    market_direction = Column(String(10))  # UP, DOWN, SIDEWAYS
    
    # AI performance
    ai_accuracy = Column(Float, default=0.0)
    signals_generated = Column(Integer, default=0)
    signals_executed = Column(Integer, default=0)
    
    # Timestamps
    session_start = Column(DateTime)
    session_end = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Additional data
    session_notes = Column(Text)
    metadata = Column(JSONB)


class RiskMetrics(Base):
    """Risk metrics tracking."""
    __tablename__ = "risk_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    
    # Portfolio metrics
    total_exposure = Column(Float, default=0.0)
    net_delta = Column(Float, default=0.0)
    net_gamma = Column(Float, default=0.0)
    net_theta = Column(Float, default=0.0)
    net_vega = Column(Float, default=0.0)
    
    # Risk measures
    var_95 = Column(Float, default=0.0)  # Value at Risk 95%
    var_99 = Column(Float, default=0.0)  # Value at Risk 99%
    expected_shortfall = Column(Float, default=0.0)
    maximum_loss = Column(Float, default=0.0)
    
    # Position limits
    positions_count = Column(Integer, default=0)
    max_position_size = Column(Float, default=0.0)
    concentration_risk = Column(Float, default=0.0)
    
    # Correlation risk
    correlation_risk_spy = Column(Float, default=0.0)
    correlation_risk_qqq = Column(Float, default=0.0)
    correlation_risk_iwm = Column(Float, default=0.0)
    
    # Timestamps
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    # Additional data
    risk_factors = Column(JSONB)
    stress_test_results = Column(JSONB)


class SystemAlert(Base):
    """System alerts and notifications."""
    __tablename__ = "system_alerts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    
    # Alert details
    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)
    source = Column(String(50), nullable=False)  # service that generated the alert
    
    # Status
    is_active = Column(Boolean, default=True)
    is_acknowledged = Column(Boolean, default=False)
    acknowledged_by = Column(String(100))
    acknowledged_at = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)
    
    # Additional data
    alert_data = Column(JSONB)
    resolution_notes = Column(Text)


class PerformanceMetrics(Base):
    """Performance metrics tracking."""
    __tablename__ = "performance_metrics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    metric_date = Column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    period_type = Column(String(20), nullable=False)  # DAILY, WEEKLY, MONTHLY
    
    # Trading performance
    total_return = Column(Float, default=0.0)
    annualized_return = Column(Float, default=0.0)
    volatility = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    sortino_ratio = Column(Float, default=0.0)
    calmar_ratio = Column(Float, default=0.0)
    
    # Drawdown metrics
    max_drawdown = Column(Float, default=0.0)
    current_drawdown = Column(Float, default=0.0)
    drawdown_duration = Column(Integer, default=0)
    
    # Trade statistics
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    profit_factor = Column(Float, default=0.0)
    avg_win = Column(Float, default=0.0)
    avg_loss = Column(Float, default=0.0)
    largest_win = Column(Float, default=0.0)
    largest_loss = Column(Float, default=0.0)
    
    # Strategy performance
    best_strategy = Column(String(50))
    worst_strategy = Column(String(50))
    strategy_diversification = Column(Float, default=0.0)
    
    # AI performance
    ai_signal_accuracy = Column(Float, default=0.0)
    ai_contribution = Column(Float, default=0.0)
    model_performance_score = Column(Float, default=0.0)
    
    # Timestamps
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    # Additional data
    detailed_metrics = Column(JSONB)
    benchmark_comparison = Column(JSONB)

