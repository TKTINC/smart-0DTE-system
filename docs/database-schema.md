# Smart-0DTE-System Database Schema

## Overview

The Smart-0DTE-System uses a multi-database architecture optimized for different data types and access patterns:

- **PostgreSQL**: Primary relational database for structured data
- **Redis**: High-speed caching and real-time data storage
- **InfluxDB**: Time-series database for high-frequency market data

## PostgreSQL Schema

### Users and Authentication

#### users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    role VARCHAR(20) DEFAULT 'trader' CHECK (role IN ('admin', 'trader', 'viewer')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_role ON users(role);
```

#### user_sessions
```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash VARCHAR(255) NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ip_address INET,
    user_agent TEXT
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_token_hash ON user_sessions(token_hash);
CREATE INDEX idx_user_sessions_expires_at ON user_sessions(expires_at);
```

### Market Data

#### tickers
```sql
CREATE TABLE tickers (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(10) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    exchange VARCHAR(20) NOT NULL,
    sector VARCHAR(100),
    industry VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    options_available BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_tickers_symbol ON tickers(symbol);
CREATE INDEX idx_tickers_is_active ON tickers(is_active);
```

#### market_data_snapshots
```sql
CREATE TABLE market_data_snapshots (
    id BIGSERIAL PRIMARY KEY,
    ticker_id INTEGER NOT NULL REFERENCES tickers(id),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    price DECIMAL(10,4) NOT NULL,
    bid DECIMAL(10,4),
    ask DECIMAL(10,4),
    volume BIGINT,
    open_price DECIMAL(10,4),
    high_price DECIMAL(10,4),
    low_price DECIMAL(10,4),
    previous_close DECIMAL(10,4),
    change_amount DECIMAL(10,4),
    change_percent DECIMAL(8,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_market_data_ticker_timestamp ON market_data_snapshots(ticker_id, timestamp DESC);
CREATE INDEX idx_market_data_timestamp ON market_data_snapshots(timestamp DESC);
```

#### options_chains
```sql
CREATE TABLE options_chains (
    id BIGSERIAL PRIMARY KEY,
    underlying_ticker_id INTEGER NOT NULL REFERENCES tickers(id),
    expiration_date DATE NOT NULL,
    strike_price DECIMAL(10,4) NOT NULL,
    option_type VARCHAR(4) NOT NULL CHECK (option_type IN ('call', 'put')),
    symbol VARCHAR(50) NOT NULL,
    bid DECIMAL(8,4),
    ask DECIMAL(8,4),
    last_price DECIMAL(8,4),
    volume INTEGER DEFAULT 0,
    open_interest INTEGER DEFAULT 0,
    implied_volatility DECIMAL(8,6),
    delta DECIMAL(8,6),
    gamma DECIMAL(8,6),
    theta DECIMAL(8,6),
    vega DECIMAL(8,6),
    rho DECIMAL(8,6),
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_options_chains_underlying_exp_strike ON options_chains(underlying_ticker_id, expiration_date, strike_price);
CREATE INDEX idx_options_chains_symbol ON options_chains(symbol);
CREATE INDEX idx_options_chains_timestamp ON options_chains(timestamp DESC);
CREATE INDEX idx_options_chains_expiration ON options_chains(expiration_date);
```

### Signal Generation

#### signals
```sql
CREATE TABLE signals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker_id INTEGER NOT NULL REFERENCES tickers(id),
    signal_type VARCHAR(20) NOT NULL CHECK (signal_type IN ('bullish', 'bearish', 'neutral')),
    strategy_type VARCHAR(50) NOT NULL,
    confidence_score DECIMAL(4,3) NOT NULL CHECK (confidence_score >= 0 AND confidence_score <= 1),
    generated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'executed', 'cancelled')),
    underlying_price DECIMAL(10,4) NOT NULL,
    target_profit DECIMAL(6,4),
    stop_loss DECIMAL(6,4),
    max_risk DECIMAL(10,2),
    max_reward DECIMAL(10,2),
    probability_profit DECIMAL(4,3),
    break_even_price DECIMAL(10,4),
    analysis_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signals_ticker_id ON signals(ticker_id);
CREATE INDEX idx_signals_generated_at ON signals(generated_at DESC);
CREATE INDEX idx_signals_status ON signals(status);
CREATE INDEX idx_signals_confidence ON signals(confidence_score DESC);
CREATE INDEX idx_signals_strategy_type ON signals(strategy_type);
```

#### signal_legs
```sql
CREATE TABLE signal_legs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id UUID NOT NULL REFERENCES signals(id) ON DELETE CASCADE,
    leg_order INTEGER NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('buy', 'sell')),
    option_type VARCHAR(4) NOT NULL CHECK (option_type IN ('call', 'put')),
    strike_price DECIMAL(10,4) NOT NULL,
    expiration_date DATE NOT NULL,
    quantity INTEGER NOT NULL,
    estimated_price DECIMAL(8,4),
    option_symbol VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_signal_legs_signal_id ON signal_legs(signal_id);
CREATE INDEX idx_signal_legs_leg_order ON signal_legs(signal_id, leg_order);
```

### Trading

#### trading_accounts
```sql
CREATE TABLE trading_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    account_number VARCHAR(50) NOT NULL,
    account_type VARCHAR(20) NOT NULL CHECK (account_type IN ('paper', 'live')),
    broker VARCHAR(20) DEFAULT 'ibkr',
    is_active BOOLEAN DEFAULT true,
    buying_power DECIMAL(15,2),
    net_liquidation DECIMAL(15,2),
    total_cash DECIMAL(15,2),
    api_credentials JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trading_accounts_user_id ON trading_accounts(user_id);
CREATE INDEX idx_trading_accounts_account_type ON trading_accounts(account_type);
```

#### trades
```sql
CREATE TABLE trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    account_id UUID NOT NULL REFERENCES trading_accounts(id),
    signal_id UUID REFERENCES signals(id),
    ticker_id INTEGER NOT NULL REFERENCES tickers(id),
    strategy_type VARCHAR(50) NOT NULL,
    trade_type VARCHAR(20) NOT NULL CHECK (trade_type IN ('manual', 'automated')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'submitted', 'filled', 'partially_filled', 'cancelled', 'rejected')),
    opened_at TIMESTAMP WITH TIME ZONE NOT NULL,
    closed_at TIMESTAMP WITH TIME ZONE,
    total_cost DECIMAL(12,2),
    total_proceeds DECIMAL(12,2),
    realized_pnl DECIMAL(12,2),
    unrealized_pnl DECIMAL(12,2),
    commission DECIMAL(8,2),
    fees DECIMAL(8,2),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_account_id ON trades(account_id);
CREATE INDEX idx_trades_signal_id ON trades(signal_id);
CREATE INDEX idx_trades_opened_at ON trades(opened_at DESC);
CREATE INDEX idx_trades_status ON trades(status);
```

#### trade_legs
```sql
CREATE TABLE trade_legs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_id UUID NOT NULL REFERENCES trades(id) ON DELETE CASCADE,
    leg_order INTEGER NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('buy', 'sell')),
    option_symbol VARCHAR(50) NOT NULL,
    quantity INTEGER NOT NULL,
    avg_fill_price DECIMAL(8,4),
    commission DECIMAL(8,2),
    fees DECIMAL(8,2),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'filled', 'partially_filled', 'cancelled')),
    filled_quantity INTEGER DEFAULT 0,
    remaining_quantity INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_trade_legs_trade_id ON trade_legs(trade_id);
CREATE INDEX idx_trade_legs_option_symbol ON trade_legs(option_symbol);
```

#### orders
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    trade_leg_id UUID NOT NULL REFERENCES trade_legs(id),
    broker_order_id VARCHAR(100),
    order_type VARCHAR(20) NOT NULL CHECK (order_type IN ('market', 'limit', 'stop', 'stop_limit')),
    action VARCHAR(10) NOT NULL CHECK (action IN ('buy', 'sell')),
    quantity INTEGER NOT NULL,
    limit_price DECIMAL(8,4),
    stop_price DECIMAL(8,4),
    time_in_force VARCHAR(10) DEFAULT 'DAY' CHECK (time_in_force IN ('DAY', 'GTC', 'IOC', 'FOK')),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'submitted', 'filled', 'partially_filled', 'cancelled', 'rejected')),
    filled_quantity INTEGER DEFAULT 0,
    avg_fill_price DECIMAL(8,4),
    submitted_at TIMESTAMP WITH TIME ZONE,
    filled_at TIMESTAMP WITH TIME ZONE,
    cancelled_at TIMESTAMP WITH TIME ZONE,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_orders_trade_leg_id ON orders(trade_leg_id);
CREATE INDEX idx_orders_broker_order_id ON orders(broker_order_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_submitted_at ON orders(submitted_at DESC);
```

### Risk Management

#### risk_parameters
```sql
CREATE TABLE risk_parameters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    account_id UUID NOT NULL REFERENCES trading_accounts(id),
    parameter_name VARCHAR(50) NOT NULL,
    parameter_value DECIMAL(15,4) NOT NULL,
    parameter_type VARCHAR(20) NOT NULL CHECK (parameter_type IN ('percentage', 'absolute', 'multiplier')),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, account_id, parameter_name)
);

CREATE INDEX idx_risk_parameters_user_account ON risk_parameters(user_id, account_id);
CREATE INDEX idx_risk_parameters_name ON risk_parameters(parameter_name);
```

#### risk_events
```sql
CREATE TABLE risk_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    account_id UUID REFERENCES trading_accounts(id),
    event_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    description TEXT NOT NULL,
    triggered_value DECIMAL(15,4),
    threshold_value DECIMAL(15,4),
    action_taken VARCHAR(100),
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_risk_events_user_id ON risk_events(user_id);
CREATE INDEX idx_risk_events_account_id ON risk_events(account_id);
CREATE INDEX idx_risk_events_severity ON risk_events(severity);
CREATE INDEX idx_risk_events_created_at ON risk_events(created_at DESC);
```

### Analytics and Performance

#### daily_pnl
```sql
CREATE TABLE daily_pnl (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    account_id UUID NOT NULL REFERENCES trading_accounts(id),
    ticker_id INTEGER REFERENCES tickers(id),
    trade_date DATE NOT NULL,
    realized_pnl DECIMAL(12,2) DEFAULT 0,
    unrealized_pnl DECIMAL(12,2) DEFAULT 0,
    total_pnl DECIMAL(12,2) DEFAULT 0,
    commission DECIMAL(8,2) DEFAULT 0,
    fees DECIMAL(8,2) DEFAULT 0,
    net_pnl DECIMAL(12,2) DEFAULT 0,
    trades_count INTEGER DEFAULT 0,
    winning_trades INTEGER DEFAULT 0,
    losing_trades INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, account_id, ticker_id, trade_date)
);

CREATE INDEX idx_daily_pnl_user_account_date ON daily_pnl(user_id, account_id, trade_date DESC);
CREATE INDEX idx_daily_pnl_ticker_date ON daily_pnl(ticker_id, trade_date DESC);
```

#### performance_metrics
```sql
CREATE TABLE performance_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    account_id UUID NOT NULL REFERENCES trading_accounts(id),
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_return DECIMAL(8,4),
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate DECIMAL(4,3),
    avg_win DECIMAL(8,4),
    avg_loss DECIMAL(8,4),
    profit_factor DECIMAL(8,4),
    sharpe_ratio DECIMAL(8,4),
    max_drawdown DECIMAL(8,4),
    max_drawdown_duration INTEGER,
    volatility DECIMAL(8,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, account_id, period_start, period_end)
);

CREATE INDEX idx_performance_metrics_user_account ON performance_metrics(user_id, account_id);
CREATE INDEX idx_performance_metrics_period ON performance_metrics(period_start, period_end);
```

### System Configuration

#### system_config
```sql
CREATE TABLE system_config (
    id SERIAL PRIMARY KEY,
    config_key VARCHAR(100) UNIQUE NOT NULL,
    config_value TEXT NOT NULL,
    config_type VARCHAR(20) DEFAULT 'string' CHECK (config_type IN ('string', 'integer', 'decimal', 'boolean', 'json')),
    description TEXT,
    is_sensitive BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_system_config_key ON system_config(config_key);
```

#### audit_logs
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(100),
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);
```

## Redis Schema

### Real-time Market Data
```
# Market data snapshots (TTL: 1 hour)
market:SPY:current -> {price, bid, ask, volume, timestamp}
market:QQQ:current -> {price, bid, ask, volume, timestamp}
market:IWM:current -> {price, bid, ask, volume, timestamp}

# Options chain snapshots (TTL: 30 minutes)
options:SPY:20240115:calls -> {strike1: {bid, ask, iv, delta}, ...}
options:SPY:20240115:puts -> {strike1: {bid, ask, iv, delta}, ...}

# Correlation data (TTL: 5 minutes)
correlation:SPY_QQQ -> 0.85
correlation:SPY_IWM -> 0.72
correlation:QQQ_IWM -> 0.68

# VIX and regime data (TTL: 1 minute)
vix:current -> 18.5
regime:current -> {type: "normal", adaptation_factor: 1.0}
```

### Signal Cache
```
# Active signals (TTL: until expiration)
signals:active -> [signal_id1, signal_id2, ...]
signal:sig_123456 -> {full signal data}

# Signal performance cache (TTL: 1 hour)
signal_performance:SPY -> {accuracy, avg_return, count}
```

### Session Management
```
# User sessions (TTL: based on session duration)
session:token_hash -> {user_id, expires_at, permissions}

# Rate limiting (TTL: 1 minute)
rate_limit:user_123:api -> {count, reset_time}
```

### Trading State
```
# Active positions (TTL: until closed)
positions:user_123 -> [position_id1, position_id2, ...]
position:pos_123456 -> {full position data}

# Order status cache (TTL: 1 day)
order:ord_123456 -> {status, fill_data, timestamp}
```

## InfluxDB Schema

### Market Data Time Series
```
# Measurement: market_data
# Tags: symbol, exchange
# Fields: price, bid, ask, volume, change_percent
# Time: timestamp

market_data,symbol=SPY,exchange=ARCA price=445.67,bid=445.65,ask=445.69,volume=45678900 1642262400000000000

# Measurement: options_data
# Tags: symbol, underlying, option_type, strike, expiration
# Fields: bid, ask, last, volume, open_interest, iv, delta, gamma, theta, vega

options_data,symbol=SPY240115C445,underlying=SPY,option_type=call,strike=445,expiration=20240115 bid=5.80,ask=5.85,last=5.82,volume=1250,iv=0.18,delta=0.75 1642262400000000000
```

### Correlation Time Series
```
# Measurement: correlations
# Tags: pair
# Fields: correlation, rolling_30d, rolling_7d

correlations,pair=SPY_QQQ correlation=0.85,rolling_30d=0.82,rolling_7d=0.88 1642262400000000000
```

### Performance Metrics
```
# Measurement: portfolio_performance
# Tags: user_id, account_id, ticker
# Fields: pnl, unrealized_pnl, position_count, exposure

portfolio_performance,user_id=user_123,account_id=acc_456,ticker=SPY pnl=1250.50,unrealized_pnl=280.00,position_count=3,exposure=25000.00 1642262400000000000
```

### Risk Metrics
```
# Measurement: risk_metrics
# Tags: user_id, account_id, metric_type
# Fields: value, threshold, severity

risk_metrics,user_id=user_123,account_id=acc_456,metric_type=var_95 value=-2100.00,threshold=-2500.00,severity=medium 1642262400000000000
```

## Database Relationships

### Primary Relationships
- Users → Trading Accounts (1:N)
- Trading Accounts → Trades (1:N)
- Trades → Trade Legs (1:N)
- Trade Legs → Orders (1:N)
- Signals → Signal Legs (1:N)
- Signals → Trades (1:N, optional)
- Tickers → Market Data (1:N)
- Tickers → Options Chains (1:N)

### Performance Considerations

#### Indexing Strategy
- Primary keys: UUID with B-tree indexes
- Foreign keys: B-tree indexes for joins
- Timestamp fields: B-tree indexes for time-based queries
- Status fields: B-tree indexes for filtering
- Composite indexes for common query patterns

#### Partitioning Strategy
- Market data: Partition by date (monthly)
- Options chains: Partition by expiration date
- Audit logs: Partition by date (weekly)
- Performance metrics: Partition by date range

#### Data Retention
- Real-time cache: 1-24 hours
- Intraday data: 30 days
- Daily aggregates: 2 years
- Trade history: Permanent
- Audit logs: 7 years

This database schema provides a robust foundation for the Smart-0DTE-System, ensuring data integrity, performance, and scalability while supporting all required functionality for real-time options trading and analytics.

