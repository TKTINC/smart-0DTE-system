"""
Unit Tests for Risk Management Service

Tests comprehensive risk management including adaptive position sizing,
emergency halt mechanisms, and real-time monitoring.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import numpy as np

from app.services.risk_management_service import (
    risk_management_service, RiskLevel, AlertSeverity, RiskLimits, PositionSizing
)
from tests.conftest import (
    assert_risk_metrics_valid, wait_for_condition
)


class TestRiskLimits:
    """Test risk limits configuration and validation."""
    
    @pytest.mark.unit
    def test_risk_limits_initialization(self):
        """Test risk limits initialization with default values."""
        limits = RiskLimits()
        
        assert limits.max_daily_loss == 1000.0
        assert limits.max_position_size == 5000.0
        assert limits.max_positions_per_symbol == 3
        assert limits.max_total_positions == 10
        assert limits.max_vix_threshold == 30.0
        assert limits.min_confidence_threshold == 0.65
    
    @pytest.mark.unit
    def test_risk_limits_customization(self):
        """Test custom risk limits configuration."""
        custom_limits = RiskLimits(
            max_daily_loss=2000.0,
            max_position_size=10000.0,
            max_positions_per_symbol=5
        )
        
        assert custom_limits.max_daily_loss == 2000.0
        assert custom_limits.max_position_size == 10000.0
        assert custom_limits.max_positions_per_symbol == 5


class TestPositionSizing:
    """Test adaptive position sizing calculations."""
    
    @pytest.mark.unit
    async def test_vix_adjustment_calculation(self, mock_risk_service):
        """Test VIX-based position size adjustment."""
        # Test extreme volatility (VIX > 30)
        extreme_adjustment = mock_risk_service._calculate_vix_adjustment(35.0)
        assert extreme_adjustment == 0.5  # 50% reduction
        
        # Test high volatility (VIX 25-30)
        high_adjustment = mock_risk_service._calculate_vix_adjustment(28.0)
        assert high_adjustment == 0.7  # 30% reduction
        
        # Test elevated volatility (VIX 20-25)
        elevated_adjustment = mock_risk_service._calculate_vix_adjustment(22.0)
        assert elevated_adjustment == 0.9  # 10% reduction
        
        # Test normal volatility (VIX 12-20)
        normal_adjustment = mock_risk_service._calculate_vix_adjustment(16.0)
        assert normal_adjustment == 1.0  # No adjustment
        
        # Test very low volatility (VIX < 12)
        low_adjustment = mock_risk_service._calculate_vix_adjustment(10.0)
        assert low_adjustment == 1.2  # 20% increase
    
    @pytest.mark.unit
    async def test_confidence_adjustment_calculation(self, mock_risk_service):
        """Test confidence-based position size adjustment."""
        # Test very high confidence (>= 0.9)
        very_high_adjustment = mock_risk_service._calculate_confidence_adjustment(0.95)
        assert very_high_adjustment == 1.3  # 30% increase
        
        # Test high confidence (>= 0.8)
        high_adjustment = mock_risk_service._calculate_confidence_adjustment(0.85)
        assert high_adjustment == 1.1  # 10% increase
        
        # Test normal confidence (>= 0.7)
        normal_adjustment = mock_risk_service._calculate_confidence_adjustment(0.75)
        assert normal_adjustment == 1.0  # No adjustment
        
        # Test moderate confidence (>= 0.6)
        moderate_adjustment = mock_risk_service._calculate_confidence_adjustment(0.65)
        assert moderate_adjustment == 0.8  # 20% reduction
        
        # Test low confidence (< 0.6)
        low_adjustment = mock_risk_service._calculate_confidence_adjustment(0.55)
        assert low_adjustment == 0.6  # 40% reduction
    
    @pytest.mark.unit
    async def test_correlation_adjustment_calculation(self, mock_risk_service):
        """Test correlation-based position size adjustment."""
        # Test high correlation risk (> 0.8)
        high_corr_adjustment = mock_risk_service._calculate_correlation_adjustment(0.85)
        assert high_corr_adjustment == 0.6  # 40% reduction
        
        # Test elevated correlation (> 0.7)
        elevated_corr_adjustment = mock_risk_service._calculate_correlation_adjustment(0.75)
        assert elevated_corr_adjustment == 0.8  # 20% reduction
        
        # Test moderate correlation (> 0.5)
        moderate_corr_adjustment = mock_risk_service._calculate_correlation_adjustment(0.6)
        assert moderate_corr_adjustment == 1.0  # No adjustment
        
        # Test low correlation (diversification benefit)
        low_corr_adjustment = mock_risk_service._calculate_correlation_adjustment(0.3)
        assert low_corr_adjustment == 1.1  # 10% increase
    
    @pytest.mark.unit
    async def test_position_size_calculation(self, mock_risk_service):
        """Test complete position size calculation."""
        market_conditions = {
            'vix_level': 20.0,
            'correlation_risk': 0.6,
            'portfolio_exposure': 2000.0
        }
        
        position_size = await mock_risk_service.calculate_position_size(
            signal_confidence=0.8,
            symbol='SPY',
            strategy_type='iron_condor',
            market_conditions=market_conditions
        )
        
        assert isinstance(position_size, float)
        assert position_size > 0
        assert position_size <= mock_risk_service.risk_limits.max_position_size
    
    @pytest.mark.unit
    async def test_position_size_limits(self, mock_risk_service):
        """Test position size limit enforcement."""
        # Test maximum position size limit
        large_size = await mock_risk_service._validate_position_size(10000.0, 'SPY')
        assert large_size <= mock_risk_service.risk_limits.max_position_size
        
        # Test minimum position size
        small_size = await mock_risk_service._validate_position_size(100.0, 'SPY')
        assert small_size >= 100.0  # Should not be reduced if within limits


class TestEmergencyHalt:
    """Test emergency halt mechanisms."""
    
    @pytest.mark.unit
    async def test_daily_loss_limit_trigger(self, mock_risk_service, mock_redis):
        """Test emergency halt trigger on daily loss limit."""
        # Set daily P&L to exceed limit
        mock_risk_service.daily_pnl = -2500.0  # Exceeds $2000 limit
        
        emergency_needed = await mock_risk_service.check_emergency_conditions()
        assert emergency_needed is True
        assert mock_risk_service.emergency_halt_active is True
    
    @pytest.mark.unit
    async def test_vix_extreme_level_trigger(self, mock_risk_service, mock_redis):
        """Test emergency halt trigger on extreme VIX levels."""
        # Mock VIX data with extreme level
        with patch('app.services.risk_management_service.vix_regime_detector.get_current_regime') as mock_vix:
            mock_vix.return_value = {'vix_level': 35.0}  # Exceeds 30.0 threshold
            
            emergency_needed = await mock_risk_service.check_emergency_conditions()
            assert emergency_needed is True
    
    @pytest.mark.unit
    async def test_portfolio_exposure_trigger(self, mock_risk_service, mock_redis):
        """Test emergency halt trigger on excessive portfolio exposure."""
        # Mock high portfolio exposure
        with patch.object(mock_risk_service, '_calculate_total_exposure') as mock_exposure:
            mock_exposure.return_value = 80000.0  # Exceeds 150% of normal max
            
            emergency_needed = await mock_risk_service.check_emergency_conditions()
            assert emergency_needed is True
    
    @pytest.mark.unit
    async def test_system_health_trigger(self, mock_risk_service, mock_redis):
        """Test emergency halt trigger on system health failure."""
        # Mock system health failure
        with patch.object(mock_risk_service, '_check_system_health') as mock_health:
            mock_health.return_value = False
            
            emergency_needed = await mock_risk_service.check_emergency_conditions()
            assert emergency_needed is True
    
    @pytest.mark.unit
    async def test_emergency_halt_clearing(self, mock_risk_service, mock_redis):
        """Test clearing of emergency halt status."""
        # Set emergency halt
        mock_risk_service.emergency_halt_active = True
        
        # Clear emergency halt
        await mock_risk_service.clear_emergency_halt("Manual override")
        
        assert mock_risk_service.emergency_halt_active is False


class TestRiskMonitoring:
    """Test real-time risk monitoring."""
    
    @pytest.mark.unit
    async def test_portfolio_greeks_calculation(self, mock_risk_service):
        """Test portfolio Greeks calculation."""
        greeks = await mock_risk_service._calculate_portfolio_greeks()
        
        assert isinstance(greeks, dict)
        assert 'delta' in greeks
        assert 'gamma' in greeks
        assert 'theta' in greeks
        assert 'vega' in greeks
        assert 'rho' in greeks
        
        # All Greeks should be numeric
        for greek_name, greek_value in greeks.items():
            assert isinstance(greek_value, (int, float))
    
    @pytest.mark.unit
    async def test_daily_pnl_calculation(self, mock_risk_service):
        """Test daily P&L calculation."""
        daily_pnl = await mock_risk_service._calculate_daily_pnl()
        
        assert isinstance(daily_pnl, (int, float))
    
    @pytest.mark.unit
    async def test_total_exposure_calculation(self, mock_risk_service):
        """Test total portfolio exposure calculation."""
        exposure = await mock_risk_service._calculate_total_exposure()
        
        assert isinstance(exposure, (int, float))
        assert exposure >= 0
    
    @pytest.mark.unit
    async def test_position_limits_monitoring(self, mock_risk_service):
        """Test position limits monitoring."""
        # Mock current positions
        mock_positions = [
            {"symbol": "SPY", "strategy": "Iron Condor", "size": 1000},
            {"symbol": "SPY", "strategy": "Bull Call Spread", "size": 800},
            {"symbol": "SPY", "strategy": "Straddle", "size": 1200},  # 3rd position for SPY
            {"symbol": "QQQ", "strategy": "Iron Condor", "size": 900}
        ]
        
        with patch.object(mock_risk_service, '_get_current_positions') as mock_get_positions:
            mock_get_positions.return_value = mock_positions
            
            # This would trigger position limit alerts in real monitoring
            positions = await mock_risk_service._get_current_positions()
            
            # Count positions per symbol
            symbol_counts = {}
            for position in positions:
                symbol = position.get('symbol', '')
                symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
            
            # SPY should have 3 positions (at limit)
            assert symbol_counts.get('SPY', 0) == 3
    
    @pytest.mark.unit
    async def test_correlation_risk_calculation(self, mock_risk_service, mock_redis):
        """Test correlation risk calculation."""
        # Mock correlation data
        correlations = {
            'SPY-QQQ': {'correlation': 0.85},
            'SPY-IWM': {'correlation': 0.72}
        }
        
        await mock_redis.set('cross_ticker_correlations', correlations)
        
        correlation_risk = await mock_risk_service._calculate_correlation_risk('SPY')
        
        assert isinstance(correlation_risk, float)
        assert 0.0 <= correlation_risk <= 1.0


class TestPerformanceMetrics:
    """Test performance metrics calculation and tracking."""
    
    @pytest.mark.unit
    async def test_performance_metrics_calculation(self, mock_risk_service):
        """Test comprehensive performance metrics calculation."""
        metrics = await mock_risk_service._calculate_performance_metrics()
        
        assert isinstance(metrics, dict)
        
        required_fields = [
            'daily_pnl', 'total_trades', 'winning_trades', 'win_rate',
            'avg_win', 'avg_loss', 'profit_factor', 'sharpe_ratio',
            'max_drawdown', 'total_return', 'timestamp'
        ]
        
        for field in required_fields:
            assert field in metrics
        
        # Validate metric ranges
        assert 0.0 <= metrics['win_rate'] <= 1.0
        assert metrics['profit_factor'] >= 0.0
        assert metrics['total_trades'] >= 0
        assert metrics['winning_trades'] <= metrics['total_trades']
    
    @pytest.mark.unit
    async def test_risk_status_summary(self, mock_risk_service):
        """Test current risk status summary."""
        status = await mock_risk_service.get_current_risk_status()
        
        assert isinstance(status, dict)
        assert 'emergency_halt_active' in status
        assert 'daily_pnl' in status
        assert 'portfolio_exposure' in status
        assert 'risk_metrics' in status
        assert 'last_updated' in status
    
    @pytest.mark.unit
    async def test_performance_summary(self, mock_risk_service):
        """Test performance summary generation."""
        summary = await mock_risk_service.get_performance_summary()
        
        assert isinstance(summary, dict)
        # Should contain performance metrics
        if summary:  # May be empty in mock
            assert 'timestamp' in summary


class TestAlertManagement:
    """Test alert creation and management."""
    
    @pytest.mark.unit
    async def test_alert_creation(self, mock_risk_service, mock_redis):
        """Test creation of risk alerts."""
        await mock_risk_service._create_alert(
            alert_type="test_alert",
            severity=AlertSeverity.HIGH,
            title="Test Alert",
            message="This is a test alert",
            alert_data={"test_value": 123}
        )
        
        # Alert should be added to active alerts
        assert len(mock_risk_service.active_alerts) > 0
        
        latest_alert = mock_risk_service.active_alerts[-1]
        assert latest_alert['type'] == 'test_alert'
        assert latest_alert['severity'] == 'high'
        assert latest_alert['title'] == 'Test Alert'
    
    @pytest.mark.unit
    async def test_alert_cleanup(self, mock_risk_service):
        """Test cleanup of old alerts."""
        # Add old alert
        old_alert = {
            'id': 'old_alert',
            'timestamp': (datetime.utcnow() - timedelta(hours=2)).isoformat(),
            'type': 'test',
            'severity': 'low',
            'title': 'Old Alert',
            'message': 'This is an old alert'
        }
        
        mock_risk_service.active_alerts.append(old_alert)
        
        # Run cleanup
        await mock_risk_service._cleanup_old_alerts()
        
        # Old alert should be removed
        remaining_alerts = [a for a in mock_risk_service.active_alerts if a['id'] == 'old_alert']
        assert len(remaining_alerts) == 0
    
    @pytest.mark.unit
    async def test_get_active_alerts(self, mock_risk_service):
        """Test retrieval of active alerts."""
        alerts = await mock_risk_service.get_active_alerts()
        
        assert isinstance(alerts, list)


class TestRiskConfiguration:
    """Test risk configuration management."""
    
    @pytest.mark.unit
    async def test_risk_limits_update(self, mock_risk_service, mock_redis):
        """Test updating risk limits configuration."""
        new_limits = {
            'max_daily_loss': 1500.0,
            'max_position_size': 7500.0,
            'max_positions_per_symbol': 4
        }
        
        success = await mock_risk_service.update_risk_limits(new_limits)
        
        assert success is True
        assert mock_risk_service.risk_limits.max_daily_loss == 1500.0
        assert mock_risk_service.risk_limits.max_position_size == 7500.0
        assert mock_risk_service.risk_limits.max_positions_per_symbol == 4
    
    @pytest.mark.unit
    async def test_invalid_risk_limits_update(self, mock_risk_service):
        """Test handling of invalid risk limits."""
        invalid_limits = {
            'invalid_field': 123,
            'max_daily_loss': 'invalid_value'
        }
        
        # Should handle invalid updates gracefully
        success = await mock_risk_service.update_risk_limits(invalid_limits)
        
        # Should not fail completely, but may not update invalid fields
        assert isinstance(success, bool)


class TestSystemHealth:
    """Test system health monitoring."""
    
    @pytest.mark.unit
    async def test_system_health_check(self, mock_risk_service, mock_redis):
        """Test system health check functionality."""
        # Mock healthy market data
        healthy_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'price': 485.67
        }
        
        await mock_redis.set('market_data_SPY', healthy_data)
        
        health = await mock_risk_service._check_system_health()
        assert health is True
    
    @pytest.mark.unit
    async def test_stale_data_detection(self, mock_risk_service, mock_redis):
        """Test detection of stale market data."""
        # Mock stale market data
        stale_data = {
            'timestamp': (datetime.utcnow() - timedelta(minutes=10)).isoformat(),
            'price': 485.67
        }
        
        await mock_redis.set('market_data_SPY', stale_data)
        
        health = await mock_risk_service._check_system_health()
        assert health is False
    
    @pytest.mark.unit
    async def test_missing_data_detection(self, mock_risk_service, mock_redis):
        """Test detection of missing market data."""
        # No market data available
        health = await mock_risk_service._check_system_health()
        assert health is False
    
    @pytest.mark.unit
    async def test_service_health_check(self, mock_risk_service):
        """Test risk management service health check."""
        # Service should be healthy when running
        mock_risk_service.is_running = True
        mock_risk_service.last_risk_check = datetime.utcnow()
        
        health = await mock_risk_service.health_check()
        assert health is True
        
        # Service should be unhealthy when not running
        mock_risk_service.is_running = False
        
        health = await mock_risk_service.health_check()
        assert health is False


@pytest.mark.integration
class TestRiskManagementIntegration:
    """Integration tests for Risk Management Service."""
    
    async def test_service_initialization_and_startup(self, mock_risk_service, mock_redis):
        """Test complete service initialization and startup."""
        # Initialize service
        await mock_risk_service.initialize()
        
        # Start risk monitoring
        await mock_risk_service.start_risk_monitoring()
        
        # Service should be running
        assert mock_risk_service.is_running is True
        
        # Stop monitoring
        await mock_risk_service.stop_risk_monitoring()
        assert mock_risk_service.is_running is False
    
    async def test_real_time_monitoring_workflow(self, mock_risk_service, mock_redis):
        """Test real-time monitoring workflow."""
        # Start monitoring
        await mock_risk_service.start_risk_monitoring()
        
        # Let monitoring run briefly
        await asyncio.sleep(0.1)
        
        # Check that monitoring is active
        assert mock_risk_service.is_running is True
        
        # Stop monitoring
        await mock_risk_service.stop_risk_monitoring()
    
    async def test_emergency_halt_workflow(self, mock_risk_service, mock_redis):
        """Test complete emergency halt workflow."""
        # Trigger emergency conditions
        mock_risk_service.daily_pnl = -2500.0  # Exceeds limit
        
        # Check emergency conditions
        emergency_needed = await mock_risk_service.check_emergency_conditions()
        assert emergency_needed is True
        assert mock_risk_service.emergency_halt_active is True
        
        # Clear emergency halt
        await mock_risk_service.clear_emergency_halt("Test completed")
        assert mock_risk_service.emergency_halt_active is False
    
    async def test_position_sizing_workflow(self, mock_risk_service, mock_redis):
        """Test complete position sizing workflow."""
        # Set up market conditions
        market_conditions = {
            'vix_level': 25.0,  # High volatility
            'correlation_risk': 0.7,
            'portfolio_exposure': 3000.0
        }
        
        # Calculate position size
        position_size = await mock_risk_service.calculate_position_size(
            signal_confidence=0.8,
            symbol='SPY',
            strategy_type='iron_condor',
            market_conditions=market_conditions
        )
        
        # Position size should be adjusted for high volatility
        base_size = mock_risk_service.position_sizing.base_position_size
        assert position_size < base_size  # Should be reduced due to high VIX

