"""
Unit Tests for Intelligence Service

Tests the Smart Intelligence Engine including correlation analysis,
signal generation, and AI-enhanced decision making.
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import numpy as np
import pandas as pd

from app.services.intelligence_service import intelligence_service, SmartCrossTickerEngine
from tests.conftest import (
    assert_signal_valid, create_mock_signal, wait_for_condition
)


class TestSmartCrossTickerEngine:
    """Test the Smart Cross-Ticker Engine component."""
    
    @pytest.mark.unit
    async def test_correlation_calculation(self, sample_time_series_data):
        """Test correlation calculation between symbols."""
        engine = SmartCrossTickerEngine()
        
        # Calculate correlation
        correlation = await engine._calculate_correlation(
            sample_time_series_data['SPY'].values,
            sample_time_series_data['QQQ'].values
        )
        
        assert isinstance(correlation, float)
        assert -1.0 <= correlation <= 1.0
        
        # Test with identical series (should be 1.0)
        perfect_correlation = await engine._calculate_correlation(
            sample_time_series_data['SPY'].values,
            sample_time_series_data['SPY'].values
        )
        
        assert abs(perfect_correlation - 1.0) < 0.001
    
    @pytest.mark.unit
    async def test_correlation_breakdown_detection(self, mock_redis):
        """Test detection of correlation breakdowns."""
        engine = SmartCrossTickerEngine()
        
        # Mock historical correlation data
        historical_correlations = [0.85, 0.82, 0.78, 0.75, 0.72, 0.68, 0.65]
        current_correlation = 0.45  # Significant breakdown
        
        breakdown_detected = await engine._detect_correlation_breakdown(
            'SPY-QQQ',
            current_correlation,
            historical_correlations
        )
        
        assert breakdown_detected is True
        
        # Test with normal correlation
        normal_correlation = 0.75
        normal_detected = await engine._detect_correlation_breakdown(
            'SPY-QQQ',
            normal_correlation,
            historical_correlations
        )
        
        assert normal_detected is False
    
    @pytest.mark.unit
    async def test_divergence_analysis(self, sample_time_series_data):
        """Test price movement divergence analysis."""
        engine = SmartCrossTickerEngine()
        
        # Create divergent price movements
        spy_returns = np.diff(sample_time_series_data['SPY'].values[-10:])
        qqq_returns = -spy_returns  # Opposite movements
        
        divergence_score = await engine._analyze_divergence(spy_returns, qqq_returns)
        
        assert isinstance(divergence_score, float)
        assert divergence_score > 0.5  # Should detect strong divergence
    
    @pytest.mark.unit
    async def test_signal_generation(self, mock_intelligence_service, sample_correlation_data):
        """Test signal generation from correlation analysis."""
        # Test correlation breakdown signal
        signals = await mock_intelligence_service.generate_correlation_signals()
        
        assert isinstance(signals, list)
        
        if signals:
            for signal in signals:
                assert_signal_valid(signal)
                assert signal['type'] == 'correlation_breakdown'
    
    @pytest.mark.unit
    async def test_confidence_calculation(self):
        """Test signal confidence calculation."""
        engine = SmartCrossTickerEngine()
        
        # Test high confidence scenario
        high_confidence = await engine._calculate_signal_confidence(
            correlation_change=-0.25,  # Large change
            statistical_significance=0.95,  # High significance
            historical_volatility=0.15  # Low volatility
        )
        
        assert 0.8 <= high_confidence <= 1.0
        
        # Test low confidence scenario
        low_confidence = await engine._calculate_signal_confidence(
            correlation_change=-0.05,  # Small change
            statistical_significance=0.60,  # Low significance
            historical_volatility=0.35  # High volatility
        )
        
        assert 0.0 <= low_confidence <= 0.6


class TestVixRegimeDetector:
    """Test VIX-based regime detection."""
    
    @pytest.mark.unit
    async def test_regime_classification(self, mock_intelligence_service, sample_vix_data):
        """Test VIX regime classification."""
        # Test low volatility regime
        low_vix_regime = await mock_intelligence_service._classify_vix_regime(12.5)
        assert low_vix_regime == 'Low Volatility'
        
        # Test normal volatility regime
        normal_vix_regime = await mock_intelligence_service._classify_vix_regime(18.0)
        assert normal_vix_regime == 'Normal Volatility'
        
        # Test high volatility regime
        high_vix_regime = await mock_intelligence_service._classify_vix_regime(28.0)
        assert high_vix_regime == 'High Volatility'
        
        # Test extreme volatility regime
        extreme_vix_regime = await mock_intelligence_service._classify_vix_regime(45.0)
        assert extreme_vix_regime == 'Extreme Volatility'
    
    @pytest.mark.unit
    async def test_adaptation_factors(self, mock_intelligence_service):
        """Test adaptation factor calculation based on VIX regime."""
        # Test low volatility adaptation
        low_vol_factors = await mock_intelligence_service._calculate_adaptation_factors('Low Volatility')
        assert low_vol_factors['position_size_multiplier'] > 1.0
        assert low_vol_factors['confidence_threshold'] < 0.65
        
        # Test extreme volatility adaptation
        extreme_vol_factors = await mock_intelligence_service._calculate_adaptation_factors('Extreme Volatility')
        assert extreme_vol_factors['position_size_multiplier'] < 1.0
        assert extreme_vol_factors['confidence_threshold'] > 0.65
    
    @pytest.mark.unit
    async def test_regime_transition_detection(self, mock_intelligence_service):
        """Test detection of regime transitions."""
        # Mock historical VIX data showing transition
        historical_vix = [15.2, 16.1, 17.8, 22.5, 28.9]  # Transition from low to high
        current_vix = 31.2
        
        transition = await mock_intelligence_service._detect_regime_transition(
            current_vix, historical_vix
        )
        
        assert transition is not None
        assert transition['from_regime'] == 'Normal Volatility'
        assert transition['to_regime'] == 'Extreme Volatility'


class TestIntelligenceService:
    """Test the main Intelligence Service."""
    
    @pytest.mark.unit
    async def test_service_initialization(self, mock_intelligence_service):
        """Test intelligence service initialization."""
        await mock_intelligence_service.initialize()
        
        # Service should be properly initialized
        assert hasattr(mock_intelligence_service, 'cross_ticker_engine')
        assert hasattr(mock_intelligence_service, 'vix_regime_detector')
    
    @pytest.mark.unit
    async def test_market_summary_generation(self, mock_intelligence_service, sample_market_data, sample_vix_data):
        """Test market summary generation."""
        summary = await mock_intelligence_service.generate_market_summary()
        
        assert isinstance(summary, dict)
        assert 'market_data' in summary
        assert 'vix_data' in summary
        assert 'correlations' in summary
        assert 'regime' in summary
        assert 'timestamp' in summary
    
    @pytest.mark.unit
    async def test_signal_processing(self, mock_intelligence_service):
        """Test signal processing and validation."""
        # Create test signals
        test_signals = [
            create_mock_signal('SPY', 0.85, 'correlation_breakdown'),
            create_mock_signal('QQQ', 0.65, 'momentum_signal'),
            create_mock_signal('IWM', 0.45, 'volatility_signal')  # Below threshold
        ]
        
        # Process signals
        processed_signals = await mock_intelligence_service._process_signals(test_signals)
        
        # Should filter out low confidence signals
        assert len(processed_signals) <= len(test_signals)
        
        for signal in processed_signals:
            assert signal['confidence'] >= 0.65  # Default threshold
            assert_signal_valid(signal)
    
    @pytest.mark.unit
    async def test_confidence_threshold_adaptation(self, mock_intelligence_service):
        """Test adaptive confidence threshold based on market conditions."""
        # Test normal market conditions
        normal_threshold = await mock_intelligence_service._adapt_confidence_threshold(
            vix_level=18.0,
            market_stress=False
        )
        assert normal_threshold == 0.65  # Default threshold
        
        # Test high volatility conditions
        high_vol_threshold = await mock_intelligence_service._adapt_confidence_threshold(
            vix_level=32.0,
            market_stress=True
        )
        assert high_vol_threshold > 0.65  # Should increase threshold
    
    @pytest.mark.unit
    async def test_signal_deduplication(self, mock_intelligence_service):
        """Test signal deduplication logic."""
        # Create duplicate signals
        duplicate_signals = [
            create_mock_signal('SPY', 0.85, 'correlation_breakdown'),
            create_mock_signal('SPY', 0.82, 'correlation_breakdown'),  # Similar signal
            create_mock_signal('QQQ', 0.75, 'momentum_signal')
        ]
        
        deduplicated = await mock_intelligence_service._deduplicate_signals(duplicate_signals)
        
        # Should remove duplicates
        assert len(deduplicated) <= len(duplicate_signals)
        
        # Should keep highest confidence signal for each symbol/type combination
        spy_signals = [s for s in deduplicated if s['symbol'] == 'SPY' and s['type'] == 'correlation_breakdown']
        if spy_signals:
            assert len(spy_signals) == 1
            assert spy_signals[0]['confidence'] == 0.85  # Highest confidence
    
    @pytest.mark.unit
    async def test_emergency_signal_detection(self, mock_intelligence_service):
        """Test detection of emergency market conditions."""
        # Test extreme VIX spike
        emergency_conditions = await mock_intelligence_service._detect_emergency_conditions(
            vix_level=45.0,
            correlation_breakdown_count=3,
            market_gap=0.05  # 5% gap
        )
        
        assert emergency_conditions is True
        
        # Test normal conditions
        normal_conditions = await mock_intelligence_service._detect_emergency_conditions(
            vix_level=18.0,
            correlation_breakdown_count=0,
            market_gap=0.001
        )
        
        assert normal_conditions is False
    
    @pytest.mark.unit
    async def test_performance_tracking(self, mock_intelligence_service):
        """Test signal performance tracking."""
        # Mock signal performance data
        signal_performance = {
            'correlation_breakdown': {'accuracy': 0.75, 'count': 20},
            'momentum_signal': {'accuracy': 0.68, 'count': 15},
            'volatility_signal': {'accuracy': 0.82, 'count': 10}
        }
        
        # Update performance metrics
        await mock_intelligence_service._update_signal_performance(signal_performance)
        
        # Get performance summary
        performance = await mock_intelligence_service.get_signal_performance()
        
        assert isinstance(performance, dict)
        assert 'overall_accuracy' in performance
        assert 'signal_types' in performance
    
    @pytest.mark.unit
    async def test_health_check(self, mock_intelligence_service):
        """Test intelligence service health check."""
        # Service should be healthy after initialization
        health = await mock_intelligence_service.health_check()
        assert health is True
    
    @pytest.mark.unit
    async def test_error_handling(self, mock_intelligence_service):
        """Test error handling in intelligence service."""
        # Test with invalid data
        with patch('app.services.intelligence_service.market_data_cache.redis.get', side_effect=Exception("Redis error")):
            # Should handle errors gracefully
            summary = await mock_intelligence_service.generate_market_summary()
            assert isinstance(summary, dict)  # Should return empty dict or default values
    
    @pytest.mark.unit
    async def test_concurrent_signal_generation(self, mock_intelligence_service):
        """Test concurrent signal generation."""
        # Generate signals concurrently
        tasks = [
            mock_intelligence_service.generate_correlation_signals(),
            mock_intelligence_service.generate_momentum_signals(),
            mock_intelligence_service.generate_volatility_signals()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # All tasks should complete without exceptions
        for result in results:
            assert not isinstance(result, Exception)
            assert isinstance(result, list)


class TestSignalValidation:
    """Test signal validation and quality checks."""
    
    @pytest.mark.unit
    async def test_signal_quality_scoring(self, mock_intelligence_service):
        """Test signal quality scoring algorithm."""
        # High quality signal
        high_quality_signal = create_mock_signal('SPY', 0.95, 'correlation_breakdown')
        high_score = await mock_intelligence_service._calculate_signal_quality(high_quality_signal)
        
        assert high_score >= 0.8
        
        # Low quality signal
        low_quality_signal = create_mock_signal('SPY', 0.55, 'weak_signal')
        low_score = await mock_intelligence_service._calculate_signal_quality(low_quality_signal)
        
        assert low_score <= 0.6
    
    @pytest.mark.unit
    async def test_signal_timing_validation(self, mock_intelligence_service):
        """Test signal timing validation."""
        # Recent signal (valid)
        recent_signal = create_mock_signal('SPY', 0.85, 'correlation_breakdown')
        recent_valid = await mock_intelligence_service._validate_signal_timing(recent_signal)
        
        assert recent_valid is True
        
        # Old signal (invalid)
        old_signal = create_mock_signal('SPY', 0.85, 'correlation_breakdown')
        old_signal['timestamp'] = (datetime.utcnow() - timedelta(hours=2)).isoformat()
        old_valid = await mock_intelligence_service._validate_signal_timing(old_signal)
        
        assert old_valid is False
    
    @pytest.mark.unit
    async def test_signal_consistency_check(self, mock_intelligence_service):
        """Test signal consistency across timeframes."""
        # Consistent signals
        consistent_signals = [
            create_mock_signal('SPY', 0.85, 'correlation_breakdown'),
            create_mock_signal('SPY', 0.82, 'momentum_signal')  # Supporting signal
        ]
        
        consistency = await mock_intelligence_service._check_signal_consistency(consistent_signals)
        assert consistency >= 0.7
        
        # Conflicting signals
        conflicting_signals = [
            create_mock_signal('SPY', 0.85, 'bullish_signal'),
            create_mock_signal('SPY', 0.80, 'bearish_signal')  # Conflicting
        ]
        
        conflict = await mock_intelligence_service._check_signal_consistency(conflicting_signals)
        assert conflict <= 0.5


@pytest.mark.integration
class TestIntelligenceServiceIntegration:
    """Integration tests for Intelligence Service."""
    
    async def test_full_analysis_pipeline(self, mock_intelligence_service, sample_market_data, sample_vix_data):
        """Test the complete analysis pipeline."""
        # Run full analysis
        analysis = await mock_intelligence_service.run_full_analysis()
        
        assert isinstance(analysis, dict)
        assert 'signals' in analysis
        assert 'market_summary' in analysis
        assert 'risk_assessment' in analysis
        assert 'recommendations' in analysis
    
    async def test_real_time_processing(self, mock_intelligence_service):
        """Test real-time signal processing."""
        # Start real-time processing
        await mock_intelligence_service.start_real_time_processing()
        
        # Wait for processing to begin
        await asyncio.sleep(0.1)
        
        # Check that processing is active
        assert mock_intelligence_service.is_processing is True
        
        # Stop processing
        await mock_intelligence_service.stop_real_time_processing()
        assert mock_intelligence_service.is_processing is False

