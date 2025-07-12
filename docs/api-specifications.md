# Smart-0DTE-System API Specifications

## Overview

The Smart-0DTE-System API provides comprehensive endpoints for real-time options trading, market data access, signal generation, and portfolio management. The API follows RESTful principles with WebSocket support for real-time data streaming.

## Base Configuration

- **Base URL**: `https://api.smart0dte.com/v1`
- **Authentication**: JWT Bearer tokens
- **Content-Type**: `application/json`
- **Rate Limiting**: 1000 requests per minute per user
- **WebSocket URL**: `wss://ws.smart0dte.com/v1`

## Authentication

### POST /auth/login
Authenticate user and receive JWT token.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access_token": "string",
  "refresh_token": "string",
  "expires_in": 3600,
  "user_id": "string",
  "permissions": ["trader", "admin"]
}
```

### POST /auth/refresh
Refresh expired JWT token.

**Request Body:**
```json
{
  "refresh_token": "string"
}
```

## Market Data Endpoints

### GET /market/tickers
Get supported ticker information.

**Response:**
```json
{
  "tickers": [
    {
      "symbol": "SPY",
      "name": "SPDR S&P 500 ETF Trust",
      "exchange": "ARCA",
      "active": true,
      "options_available": true
    }
  ]
}
```

### GET /market/data/{symbol}
Get real-time market data for a specific symbol.

**Parameters:**
- `symbol`: Ticker symbol (SPY, QQQ, IWM)
- `include_options`: Boolean (default: false)

**Response:**
```json
{
  "symbol": "SPY",
  "price": 445.67,
  "change": 2.34,
  "change_percent": 0.53,
  "volume": 45678900,
  "bid": 445.65,
  "ask": 445.69,
  "last_updated": "2024-01-15T14:30:00Z",
  "options_chain": {
    "expiration": "2024-01-15",
    "calls": [...],
    "puts": [...]
  }
}
```

### GET /market/options/{symbol}
Get options chain data for a specific symbol.

**Parameters:**
- `symbol`: Underlying symbol
- `expiration`: Expiration date (YYYY-MM-DD)
- `strikes`: Number of strikes around ATM (default: 10)

**Response:**
```json
{
  "symbol": "SPY",
  "underlying_price": 445.67,
  "expiration": "2024-01-15",
  "time_to_expiration": 0.25,
  "calls": [
    {
      "strike": 440.0,
      "bid": 5.80,
      "ask": 5.85,
      "last": 5.82,
      "volume": 1250,
      "open_interest": 5670,
      "implied_volatility": 0.18,
      "delta": 0.75,
      "gamma": 0.02,
      "theta": -0.15,
      "vega": 0.08
    }
  ],
  "puts": [...]
}
```

### GET /market/correlation
Get real-time correlation matrix for tracked tickers.

**Response:**
```json
{
  "timestamp": "2024-01-15T14:30:00Z",
  "correlations": {
    "SPY_QQQ": 0.85,
    "SPY_IWM": 0.72,
    "QQQ_IWM": 0.68
  },
  "regime": "normal",
  "vix_level": 18.5
}
```

## Signal Generation Endpoints

### GET /signals/active
Get currently active trading signals.

**Parameters:**
- `symbol`: Filter by symbol (optional)
- `confidence_min`: Minimum confidence level (0-1)
- `strategy_type`: Filter by strategy type

**Response:**
```json
{
  "signals": [
    {
      "id": "sig_123456",
      "symbol": "SPY",
      "signal_type": "bullish",
      "strategy": "bull_call_spread",
      "confidence": 0.78,
      "generated_at": "2024-01-15T14:25:00Z",
      "expires_at": "2024-01-15T16:00:00Z",
      "entry_criteria": {
        "long_strike": 445,
        "short_strike": 450,
        "max_cost": 2.50,
        "target_profit": 0.25,
        "stop_loss": 0.75
      },
      "risk_metrics": {
        "max_loss": 225,
        "max_profit": 25,
        "probability_profit": 0.65,
        "break_even": 447.50
      }
    }
  ]
}
```

### POST /signals/generate
Manually trigger signal generation.

**Request Body:**
```json
{
  "symbols": ["SPY", "QQQ", "IWM"],
  "force_refresh": true,
  "min_confidence": 0.6
}
```

### GET /signals/{signal_id}
Get detailed information about a specific signal.

**Response:**
```json
{
  "id": "sig_123456",
  "symbol": "SPY",
  "signal_type": "bullish",
  "strategy": "bull_call_spread",
  "confidence": 0.78,
  "generated_at": "2024-01-15T14:25:00Z",
  "analysis": {
    "technical_factors": {
      "price_momentum": 0.8,
      "volume_profile": 0.7,
      "volatility_skew": 0.6
    },
    "correlation_factors": {
      "cross_ticker_strength": 0.75,
      "divergence_score": 0.3
    },
    "market_regime": {
      "vix_level": 18.5,
      "regime_type": "normal",
      "adaptation_factor": 1.0
    }
  },
  "execution_plan": {
    "legs": [
      {
        "action": "buy",
        "option_type": "call",
        "strike": 445,
        "quantity": 1,
        "estimated_price": 5.80
      },
      {
        "action": "sell",
        "option_type": "call",
        "strike": 450,
        "quantity": 1,
        "estimated_price": 3.30
      }
    ]
  }
}
```

## Trading Endpoints

### GET /trading/config
Get current trading configuration.

**Response:**
```json
{
  "trading_mode": "paper",
  "position_size": 24000,
  "profit_target": 0.10,
  "stop_loss": 0.10,
  "confidence_threshold": 0.65,
  "auto_execute": false,
  "max_positions": 10,
  "daily_loss_limit": 2400
}
```

### PUT /trading/config
Update trading configuration.

**Request Body:**
```json
{
  "trading_mode": "live",
  "position_size": 30000,
  "profit_target": 0.12,
  "stop_loss": 0.08,
  "confidence_threshold": 0.70,
  "auto_execute": true
}
```

### POST /trading/execute
Execute a trading signal.

**Request Body:**
```json
{
  "signal_id": "sig_123456",
  "position_size": 25000,
  "override_params": {
    "profit_target": 0.15,
    "stop_loss": 0.05
  }
}
```

**Response:**
```json
{
  "trade_id": "trade_789012",
  "status": "submitted",
  "orders": [
    {
      "order_id": "ord_345678",
      "symbol": "SPY240115C445",
      "action": "buy",
      "quantity": 10,
      "order_type": "limit",
      "limit_price": 5.80,
      "status": "submitted"
    }
  ]
}
```

### GET /trading/positions
Get current trading positions.

**Response:**
```json
{
  "positions": [
    {
      "position_id": "pos_123456",
      "symbol": "SPY",
      "strategy": "bull_call_spread",
      "opened_at": "2024-01-15T14:30:00Z",
      "legs": [
        {
          "symbol": "SPY240115C445",
          "quantity": 10,
          "avg_price": 5.82,
          "current_price": 6.10,
          "unrealized_pnl": 280
        }
      ],
      "total_cost": 2500,
      "current_value": 2780,
      "unrealized_pnl": 280,
      "unrealized_pnl_percent": 0.112,
      "target_profit": 250,
      "stop_loss": 250
    }
  ]
}
```

### POST /trading/close/{position_id}
Close a specific position.

**Request Body:**
```json
{
  "close_type": "market",
  "partial_quantity": null
}
```

## Risk Management Endpoints

### GET /risk/metrics
Get current risk metrics.

**Response:**
```json
{
  "portfolio_value": 98500,
  "daily_pnl": 1250,
  "daily_pnl_percent": 0.0127,
  "max_drawdown": -850,
  "var_95": -2100,
  "position_concentration": {
    "SPY": 0.45,
    "QQQ": 0.35,
    "IWM": 0.20
  },
  "risk_limits": {
    "daily_loss_limit": 2400,
    "position_limit": 24000,
    "max_positions": 10
  },
  "emergency_status": false
}
```

### POST /risk/emergency
Trigger emergency halt.

**Request Body:**
```json
{
  "reason": "manual_halt",
  "close_positions": true
}
```

### GET /risk/regime
Get current market regime information.

**Response:**
```json
{
  "regime_type": "high_volatility",
  "vix_level": 28.5,
  "adaptation_factor": 0.7,
  "risk_adjustments": {
    "position_size_multiplier": 0.8,
    "confidence_threshold_adjustment": 0.05,
    "stop_loss_tightening": 0.02
  },
  "emergency_thresholds": {
    "vix_emergency": 35.0,
    "correlation_breakdown": 0.3,
    "volume_spike": 3.0
  }
}
```

## Analytics Endpoints

### GET /analytics/performance
Get performance analytics.

**Parameters:**
- `start_date`: Start date (YYYY-MM-DD)
- `end_date`: End date (YYYY-MM-DD)
- `symbol`: Filter by symbol (optional)

**Response:**
```json
{
  "period": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-15",
    "trading_days": 11
  },
  "overall_performance": {
    "total_return": 0.125,
    "total_trades": 45,
    "win_rate": 0.67,
    "avg_win": 0.089,
    "avg_loss": -0.045,
    "profit_factor": 1.85,
    "sharpe_ratio": 2.1,
    "max_drawdown": -0.032
  },
  "by_symbol": {
    "SPY": {
      "trades": 18,
      "win_rate": 0.72,
      "total_return": 0.078
    }
  },
  "by_strategy": {
    "bull_call_spread": {
      "trades": 12,
      "win_rate": 0.75,
      "avg_return": 0.095
    }
  }
}
```

### GET /analytics/signals
Get signal performance analytics.

**Response:**
```json
{
  "signal_performance": {
    "total_signals": 156,
    "executed_signals": 45,
    "execution_rate": 0.29,
    "avg_confidence": 0.72,
    "confidence_accuracy": {
      "0.6-0.7": 0.58,
      "0.7-0.8": 0.71,
      "0.8-0.9": 0.84,
      "0.9-1.0": 0.92
    }
  },
  "strategy_effectiveness": {
    "bull_call_spread": {
      "signals": 34,
      "success_rate": 0.74,
      "avg_return": 0.089
    }
  }
}
```

## WebSocket Endpoints

### Real-time Market Data
**Channel**: `/ws/market/{symbol}`

**Message Format:**
```json
{
  "type": "market_update",
  "symbol": "SPY",
  "data": {
    "price": 445.67,
    "change": 2.34,
    "volume": 45678900,
    "timestamp": "2024-01-15T14:30:00Z"
  }
}
```

### Real-time Signals
**Channel**: `/ws/signals`

**Message Format:**
```json
{
  "type": "new_signal",
  "data": {
    "id": "sig_123456",
    "symbol": "SPY",
    "confidence": 0.78,
    "strategy": "bull_call_spread",
    "generated_at": "2024-01-15T14:25:00Z"
  }
}
```

### Position Updates
**Channel**: `/ws/positions`

**Message Format:**
```json
{
  "type": "position_update",
  "data": {
    "position_id": "pos_123456",
    "unrealized_pnl": 280,
    "unrealized_pnl_percent": 0.112,
    "current_value": 2780
  }
}
```

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "INVALID_SYMBOL",
    "message": "The specified symbol is not supported",
    "details": {
      "symbol": "INVALID",
      "supported_symbols": ["SPY", "QQQ", "IWM"]
    },
    "timestamp": "2024-01-15T14:30:00Z",
    "request_id": "req_123456"
  }
}
```

### Error Codes
- `AUTHENTICATION_FAILED`: Invalid credentials
- `INSUFFICIENT_PERMISSIONS`: User lacks required permissions
- `RATE_LIMIT_EXCEEDED`: Too many requests
- `INVALID_SYMBOL`: Unsupported ticker symbol
- `MARKET_CLOSED`: Trading outside market hours
- `INSUFFICIENT_FUNDS`: Not enough buying power
- `POSITION_LIMIT_EXCEEDED`: Too many open positions
- `EMERGENCY_HALT_ACTIVE`: Trading halted due to emergency
- `INVALID_STRATEGY`: Unsupported options strategy
- `DATA_UNAVAILABLE`: Market data temporarily unavailable

## Rate Limiting

### Limits by Endpoint Type
- **Authentication**: 10 requests per minute
- **Market Data**: 100 requests per minute
- **Trading**: 50 requests per minute
- **Analytics**: 20 requests per minute
- **WebSocket**: 1000 messages per minute

### Rate Limit Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642262400
```

## Pagination

### Standard Pagination Parameters
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 50, max: 200)
- `sort`: Sort field
- `order`: Sort order (asc/desc)

### Pagination Response
```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "limit": 50,
    "total_pages": 10,
    "total_items": 500,
    "has_next": true,
    "has_prev": false
  }
}
```

## API Versioning

### Version Strategy
- **Current Version**: v1
- **Deprecation Policy**: 6 months notice
- **Backward Compatibility**: Maintained within major versions
- **Version Header**: `API-Version: v1`

### Version-specific Endpoints
- **v1**: Current stable version
- **v2**: Future version (in development)
- **beta**: Experimental features

This API specification provides comprehensive access to all Smart-0DTE-System functionality while maintaining security, performance, and reliability standards required for professional trading applications.

