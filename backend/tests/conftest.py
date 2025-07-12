"""
Smart-0DTE-System Test Configuration

This module provides pytest configuration, fixtures, and test utilities
for comprehensive testing of the Smart-0DTE-System.
"""

import pytest
import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Generator
from unittest.mock import Mock, AsyncMock, patch
import pandas as pd
import numpy as np

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'app'))

from app.core.config import settings
from app.core.database import get_db_session
from app.core.redis_client import market_data_cache
from app.services.market_data_service import market_data_service
from app.services.intelligence_service import intelligence_service
from app.services.trading_strategy_service import trading_strategy_service
from app.services.risk_management_service import risk_management_service
from app.services.monitoring_service import monitoring_service
from app.services.ai_learning_service import ai_learning_service


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_settings():
    """Test configuration settings."""
    return {
        'database_url': 'sqlite:///test.db',
        'redis_url': 'redis://localhost:6379/1',
        'environment': 'test',
        'debug': True,
        'testing': True
    }


@pytest.fixture
async def mock_redis():
    """Mock Redis client for testing."""
    mock_redis = AsyncMock()
    
    # Mock data storage
    mock_data = {}
    
    async def mock_get(key):
        return mock_data.get(key)
    
    async def mock_set(key, value, ttl=None):
        mock_data[key] = value
        return True
    
    async def mock_delete(key):
        if key in mock_data:
            del mock_data[key]
        return True
    
    mock_redis.get = mock_get
    mock_redis.set = mock_set
    mock_redis.delete = mock_delete
    
    return mock_redis


@pytest.fixture
async def mock_database():
    """Mock database session for testing."""
    mock_db = AsyncMock()
    
    # Mock query results
    mock_db.execute = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_db.close = AsyncMock()
    
    return mock_db


@pytest.fixture
def sample_market_data():
    """Sample market data for testing."""
    return {
        'SPY': {
            'symbol': 'SPY',
            'price': 485.67,
            'change': 2.34,
            'change_percent': 0.48,
            'volume': 45678900,
            'bid': 485.65,
            'ask': 485.69,
            'timestamp': datetime.utcnow().isoformat()
        },
        'QQQ': {
            'symbol': 'QQQ',
            'price': 412.89,
            'change': -1.23,
            'change_percent': -0.30,
            'volume': 32145600,
            'bid': 412.87,
            'ask': 412.91,
            'timestamp': datetime.utcnow().isoformat()
        },
        'IWM': {
            'symbol': 'IWM',
            'price': 218.45,
            'change': 0.87,
            'change_percent': 0.40,
            'volume': 18923400,
            'bid': 218.43,
            'ask': 218.47,
            'timestamp': datetime.utcnow().isoformat()
        }
    }


@pytest.fixture
def sample_vix_data():
    """Sample VIX data for testing."""
    return {
        'level': 16.8,
        'change': -0.45,
        'change_percent': -2.61,
        'regime': 'Low Volatility',
        'percentile': 25,
        'timestamp': datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_options_data():
    """Sample options chain data for testing."""
    return {
        'SPY': {
            'underlying_price': 485.67,
            'expiration': datetime.utcnow().date().isoformat(),
            'calls': [
                {
                    'strike': 480.0,
                    'bid': 6.20,
                    'ask': 6.30,
                    'last': 6.25,
                    'volume': 1250,
                    'open_interest': 5600,
                    'implied_volatility': 0.18,
                    'delta': 0.65,
                    'gamma': 0.08,
                    'theta': -0.12,
                    'vega': 0.25
                },
                {
                    'strike': 485.0,
                    'bid': 3.80,
                    'ask': 3.90,
                    'last': 3.85,
                    'volume': 2100,
                    'open_interest': 8900,
                    'implied_volatility': 0.16,
                    'delta': 0.52,
                    'gamma': 0.12,
                    'theta': -0.15,
                    'vega': 0.28
                }
            ],
            'puts': [
                {
                    'strike': 485.0,
                    'bid': 3.70,
                    'ask': 3.80,
                    'last': 3.75,
                    'volume': 1800,
                    'open_interest': 7200,
                    'implied_volatility': 0.17,
                    'delta': -0.48,
                    'gamma': 0.12,
                    'theta': -0.14,
                    'vega': 0.27
                },
                {
                    'strike': 490.0,
                    'bid': 6.10,
                    'ask': 6.20,
                    'last': 6.15,
                    'volume': 950,
                    'open_interest': 4300,
                    'implied_volatility': 0.19,
                    'delta': -0.65,
                    'gamma': 0.08,
                    'theta': -0.11,
                    'vega': 0.24
                }
            ]
        }
    }


@pytest.fixture
def sample_correlation_data():
    """Sample correlation data for testing."""
    return {
        'SPY-QQQ': {
            'correlation': 0.65,
            'change': -0.15,
            'status': 'breakdown',
            'confidence': 0.85,
            'timestamp': datetime.utcnow().isoformat()
        },
        'SPY-IWM': {
            'correlation': 0.78,
            'change': 0.02,
            'status': 'normal',
            'confidence': 0.92,
            'timestamp': datetime.utcnow().isoformat()
        },
        'QQQ-IWM': {
            'correlation': 0.72,
            'change': -0.08,
            'status': 'weakening',
            'confidence': 0.88,
            'timestamp': datetime.utcnow().isoformat()
        }
    }


@pytest.fixture
def sample_signals():
    """Sample trading signals for testing."""
    return [
        {
            'id': 'signal_1',
            'symbol': 'SPY',
            'type': 'correlation_breakdown',
            'strength': 'STRONG',
            'confidence': 0.85,
            'direction': 'bullish',
            'reasoning': ['SPY-QQQ correlation dropped to 0.65', 'Divergence detected in momentum'],
            'timestamp': datetime.utcnow().isoformat()
        },
        {
            'id': 'signal_2',
            'symbol': 'QQQ',
            'type': 'ai_prediction',
            'strength': 'MODERATE',
            'confidence': 0.72,
            'direction': 'bearish',
            'reasoning': ['AI model confidence: 72%', 'Volatility expansion predicted'],
            'timestamp': datetime.utcnow().isoformat()
        }
    ]


@pytest.fixture
def sample_strategies():
    """Sample trading strategies for testing."""
    return [
        {
            'id': 'strategy_1',
            'symbol': 'SPY',
            'type': 'iron_condor',
            'status': 'active',
            'entry_price': 485.67,
            'target_profit': 120.00,
            'max_loss': 380.00,
            'current_pnl': 45.67,
            'confidence': 0.85,
            'legs': [
                {'type': 'call', 'strike': 490, 'action': 'sell'},
                {'type': 'call', 'strike': 495, 'action': 'buy'},
                {'type': 'put', 'strike': 480, 'action': 'sell'},
                {'type': 'put', 'strike': 475, 'action': 'buy'}
            ],
            'timestamp': datetime.utcnow().isoformat()
        },
        {
            'id': 'strategy_2',
            'symbol': 'QQQ',
            'type': 'bull_call_spread',
            'status': 'active',
            'entry_price': 412.89,
            'target_profit': 200.00,
            'max_loss': 300.00,
            'current_pnl': -23.45,
            'confidence': 0.72,
            'legs': [
                {'type': 'call', 'strike': 415, 'action': 'buy'},
                {'type': 'call', 'strike': 420, 'action': 'sell'}
            ],
            'timestamp': datetime.utcnow().isoformat()
        }
    ]


@pytest.fixture
def sample_risk_metrics():
    """Sample risk metrics for testing."""
    return {
        'portfolio_delta': 150.0,
        'portfolio_gamma': 25.0,
        'portfolio_theta': -45.0,
        'portfolio_vega': 120.0,
        'portfolio_rho': 8.0,
        'total_exposure': 3500.0,
        'daily_pnl': 125.67,
        'position_count': 2,
        'max_daily_loss': 1000.0,
        'emergency_halt_active': False,
        'timestamp': datetime.utcnow().isoformat()
    }


@pytest.fixture
def sample_performance_metrics():
    """Sample performance metrics for testing."""
    return {
        'daily_pnl': 125.67,
        'total_trades': 15,
        'winning_trades': 10,
        'losing_trades': 5,
        'win_rate': 0.667,
        'avg_win': 45.67,
        'avg_loss': -23.45,
        'profit_factor': 1.95,
        'sharpe_ratio': 1.23,
        'max_drawdown': -156.78,
        'total_return': 234.56,
        'timestamp': datetime.utcnow().isoformat()
    }


@pytest.fixture
async def mock_market_data_service(mock_redis, sample_market_data, sample_vix_data):
    """Mock market data service for testing."""
    with patch('app.services.market_data_service.market_data_cache.redis', mock_redis):
        # Pre-populate with sample data
        for symbol, data in sample_market_data.items():
            await mock_redis.set(f'market_data_{symbol}', data)
        
        await mock_redis.set('vix_data', sample_vix_data)
        
        yield market_data_service


@pytest.fixture
async def mock_intelligence_service(mock_redis, sample_correlation_data, sample_signals):
    """Mock intelligence service for testing."""
    with patch('app.services.intelligence_service.market_data_cache.redis', mock_redis):
        # Pre-populate with sample data
        await mock_redis.set('cross_ticker_correlations', sample_correlation_data)
        await mock_redis.set('active_signals', sample_signals)
        
        yield intelligence_service


@pytest.fixture
async def mock_trading_service(mock_redis, sample_strategies):
    """Mock trading strategy service for testing."""
    with patch('app.services.trading_strategy_service.market_data_cache.redis', mock_redis):
        # Pre-populate with sample data
        await mock_redis.set('active_strategies', sample_strategies)
        
        yield trading_strategy_service


@pytest.fixture
async def mock_risk_service(mock_redis, sample_risk_metrics):
    """Mock risk management service for testing."""
    with patch('app.services.risk_management_service.market_data_cache.redis', mock_redis):
        # Pre-populate with sample data
        await mock_redis.set('current_risk_metrics', sample_risk_metrics)
        
        yield risk_management_service


@pytest.fixture
async def mock_monitoring_service(mock_redis):
    """Mock monitoring service for testing."""
    with patch('app.services.monitoring_service.market_data_cache.redis', mock_redis):
        yield monitoring_service


@pytest.fixture
async def mock_ai_service(mock_redis):
    """Mock AI learning service for testing."""
    with patch('app.services.ai_learning_service.market_data_cache.redis', mock_redis):
        yield ai_learning_service


@pytest.fixture
def mock_ibkr_client():
    """Mock IBKR client for testing."""
    mock_client = Mock()
    
    # Mock connection methods
    mock_client.connect = Mock(return_value=True)
    mock_client.disconnect = Mock()
    mock_client.is_connected = Mock(return_value=True)
    
    # Mock account methods
    mock_client.get_account_value = Mock(return_value=50000.0)
    mock_client.get_positions = Mock(return_value=[])
    
    # Mock order methods
    mock_client.place_order = Mock(return_value={'order_id': 12345, 'status': 'submitted'})
    mock_client.cancel_order = Mock(return_value=True)
    mock_client.get_order_status = Mock(return_value={'status': 'filled', 'filled_qty': 1})
    
    # Mock market data methods
    mock_client.get_market_data = Mock(return_value={'price': 485.67, 'volume': 1000})
    mock_client.get_options_chain = Mock(return_value={'calls': [], 'puts': []})
    
    return mock_client


@pytest.fixture
def sample_time_series_data():
    """Sample time series data for testing."""
    dates = pd.date_range(start='2024-01-01', end='2024-12-07', freq='D')
    
    # Generate realistic price data
    np.random.seed(42)  # For reproducible tests
    
    spy_prices = 400 + np.cumsum(np.random.normal(0, 2, len(dates)))
    qqq_prices = 350 + np.cumsum(np.random.normal(0, 1.8, len(dates)))
    iwm_prices = 180 + np.cumsum(np.random.normal(0, 1.5, len(dates)))
    vix_levels = 15 + np.abs(np.random.normal(0, 5, len(dates)))
    
    return pd.DataFrame({
        'date': dates,
        'SPY': spy_prices,
        'QQQ': qqq_prices,
        'IWM': iwm_prices,
        'VIX': vix_levels
    })


@pytest.fixture
def test_config():
    """Test configuration dictionary."""
    return {
        'symbols': ['SPY', 'QQQ', 'IWM'],
        'confidence_threshold': 0.65,
        'max_positions': 3,
        'profit_target': 0.10,
        'stop_loss': 0.10,
        'vix_threshold': 30.0,
        'correlation_threshold': 0.3,
        'position_size': 1000.0
    }


# Test utilities

def create_mock_signal(symbol: str = 'SPY', confidence: float = 0.8, signal_type: str = 'correlation_breakdown') -> Dict[str, Any]:
    """Create a mock trading signal for testing."""
    return {
        'id': f'test_signal_{symbol}_{int(datetime.utcnow().timestamp())}',
        'symbol': symbol,
        'type': signal_type,
        'strength': 'STRONG' if confidence > 0.8 else 'MODERATE',
        'confidence': confidence,
        'direction': 'bullish',
        'reasoning': [f'Test signal for {symbol}'],
        'timestamp': datetime.utcnow().isoformat()
    }


def create_mock_strategy(symbol: str = 'SPY', strategy_type: str = 'iron_condor') -> Dict[str, Any]:
    """Create a mock trading strategy for testing."""
    return {
        'id': f'test_strategy_{symbol}_{int(datetime.utcnow().timestamp())}',
        'symbol': symbol,
        'type': strategy_type,
        'status': 'active',
        'entry_price': 485.67,
        'target_profit': 120.00,
        'max_loss': 380.00,
        'current_pnl': 0.0,
        'confidence': 0.85,
        'timestamp': datetime.utcnow().isoformat()
    }


def assert_signal_valid(signal: Dict[str, Any]) -> None:
    """Assert that a signal has all required fields."""
    required_fields = ['id', 'symbol', 'type', 'strength', 'confidence', 'timestamp']
    for field in required_fields:
        assert field in signal, f"Signal missing required field: {field}"
    
    assert signal['confidence'] >= 0.0 and signal['confidence'] <= 1.0, "Confidence must be between 0 and 1"
    assert signal['strength'] in ['WEAK', 'MODERATE', 'STRONG'], "Invalid signal strength"


def assert_strategy_valid(strategy: Dict[str, Any]) -> None:
    """Assert that a strategy has all required fields."""
    required_fields = ['id', 'symbol', 'type', 'status', 'confidence', 'timestamp']
    for field in required_fields:
        assert field in strategy, f"Strategy missing required field: {field}"
    
    assert strategy['confidence'] >= 0.0 and strategy['confidence'] <= 1.0, "Confidence must be between 0 and 1"
    assert strategy['status'] in ['active', 'closed', 'pending'], "Invalid strategy status"


def assert_risk_metrics_valid(metrics: Dict[str, Any]) -> None:
    """Assert that risk metrics have all required fields."""
    required_fields = ['portfolio_delta', 'portfolio_gamma', 'total_exposure', 'daily_pnl', 'timestamp']
    for field in required_fields:
        assert field in metrics, f"Risk metrics missing required field: {field}"


# Async test helpers

async def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1) -> bool:
    """Wait for a condition to become true with timeout."""
    start_time = datetime.utcnow()
    
    while (datetime.utcnow() - start_time).total_seconds() < timeout:
        if await condition_func() if asyncio.iscoroutinefunction(condition_func) else condition_func():
            return True
        await asyncio.sleep(interval)
    
    return False


# Pytest configuration

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "requires_redis: mark test as requiring Redis")
    config.addinivalue_line("markers", "requires_db: mark test as requiring database")
    config.addinivalue_line("markers", "requires_ibkr: mark test as requiring IBKR connection")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on test location."""
    for item in items:
        # Add markers based on test file location
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        
        # Add slow marker for tests that might take longer
        if any(keyword in item.name.lower() for keyword in ['performance', 'load', 'stress']):
            item.add_marker(pytest.mark.slow)

