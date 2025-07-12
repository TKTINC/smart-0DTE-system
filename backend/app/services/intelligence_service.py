"""
Smart-0DTE-System Intelligence Engine

This module implements the SmartCrossTickerEngine with Pearson correlation analysis,
VIX-based regime detection, and adaptive intelligence for signal generation.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
import math

import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from scipy.signal import find_peaks
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans

from app.core.config import settings
from app.core.redis_client import market_data_cache
from app.core.influxdb_client import market_data_influx
from app.models.market_data_models import CorrelationData, MarketRegime
from app.core.database import db_manager

logger = logging.getLogger(__name__)


class SmartCrossTickerEngine:
    """
    Smart Cross-Ticker Intelligence Engine
    
    Performs real-time Pearson correlation analysis, divergence detection,
    and cross-ticker signal generation for SPY, QQQ, and IWM.
    """
    
    def __init__(self):
        self.supported_symbols = settings.SUPPORTED_TICKERS
        self.correlation_pairs = [
            ('SPY', 'QQQ'),
            ('SPY', 'IWM'),
            ('QQQ', 'IWM')
        ]
        self.is_running = False
        
        # Historical data storage for correlation calculation
        self.price_history = {symbol: [] for symbol in self.supported_symbols}
        self.correlation_history = {}
        
        # Correlation thresholds
        self.correlation_thresholds = {
            'high_correlation': 0.8,
            'normal_correlation': 0.5,
            'low_correlation': 0.3,
            'negative_correlation': -0.3,
            'breakdown_threshold': settings.CORRELATION_BREAKDOWN_THRESHOLD
        }
        
        # Analysis parameters
        self.lookback_periods = {
            'short': 20,    # 20 data points (40 minutes at 2-min intervals)
            'medium': 60,   # 60 data points (2 hours)
            'long': 180     # 180 data points (6 hours)
        }
    
    async def initialize(self) -> None:
        """Initialize the Smart Cross-Ticker Engine."""
        try:
            # Load historical data for correlation baseline
            await self._load_historical_data()
            
            logger.info("SmartCrossTickerEngine initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SmartCrossTickerEngine: {e}")
            raise
    
    async def start_correlation_analysis(self) -> None:
        """Start real-time correlation analysis."""
        try:
            self.is_running = True
            
            # Start background tasks
            asyncio.create_task(self._update_price_history())
            asyncio.create_task(self._calculate_correlations())
            asyncio.create_task(self._detect_divergences())
            asyncio.create_task(self._generate_cross_ticker_signals())
            
            logger.info("Cross-ticker correlation analysis started")
            
        except Exception as e:
            logger.error(f"Failed to start correlation analysis: {e}")
            raise
    
    async def stop_correlation_analysis(self) -> None:
        """Stop correlation analysis."""
        try:
            self.is_running = False
            logger.info("Cross-ticker correlation analysis stopped")
        except Exception as e:
            logger.error(f"Error stopping correlation analysis: {e}")
    
    async def _load_historical_data(self) -> None:
        """Load historical price data for correlation baseline."""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(days=7)  # Load 7 days of data
            
            for symbol in self.supported_symbols:
                # Get historical data from InfluxDB
                historical_data = market_data_influx.get_market_data_history(
                    symbol, start_time, end_time, "2m"
                )
                
                if historical_data:
                    prices = [float(record.get('_value', 0)) for record in historical_data]
                    self.price_history[symbol] = prices[-self.lookback_periods['long']:]
                else:
                    # Initialize with mock data if no historical data
                    self.price_history[symbol] = []
            
            logger.info("Historical data loaded for correlation analysis")
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
    
    async def _update_price_history(self) -> None:
        """Update price history with real-time data."""
        while self.is_running:
            try:
                for symbol in self.supported_symbols:
                    # Get current market data
                    market_data = await market_data_cache.get_market_data(symbol)
                    
                    if market_data and 'price' in market_data:
                        price = float(market_data['price'])
                        
                        # Add to price history
                        self.price_history[symbol].append(price)
                        
                        # Keep only the required lookback period
                        max_length = self.lookback_periods['long']
                        if len(self.price_history[symbol]) > max_length:
                            self.price_history[symbol] = self.price_history[symbol][-max_length:]
                
                # Wait for next update
                await asyncio.sleep(settings.MARKET_DATA_REFRESH_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error updating price history: {e}")
                await asyncio.sleep(5)
    
    async def _calculate_correlations(self) -> None:
        """Calculate real-time correlations between ticker pairs."""
        while self.is_running:
            try:
                correlations = {}
                
                for symbol1, symbol2 in self.correlation_pairs:
                    pair_name = f"{symbol1}_{symbol2}"
                    
                    # Calculate correlations for different time periods
                    correlation_data = await self._calculate_pair_correlation(symbol1, symbol2)
                    
                    if correlation_data:
                        correlations[pair_name] = correlation_data
                        
                        # Cache correlation data
                        await market_data_cache.set_correlation(pair_name, correlation_data['current'])
                        
                        # Store in InfluxDB
                        market_data_influx.write_correlation_data(
                            pair=pair_name,
                            correlation=correlation_data['current'],
                            rolling_30d=correlation_data.get('long_term', 0),
                            rolling_7d=correlation_data.get('medium_term', 0)
                        )
                
                # Store complete correlation matrix
                await market_data_cache.redis.set(
                    'correlation_matrix',
                    correlations,
                    ttl=settings.CORRELATION_REFRESH_INTERVAL * 2
                )
                
                # Wait for next calculation
                await asyncio.sleep(settings.CORRELATION_REFRESH_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error calculating correlations: {e}")
                await asyncio.sleep(5)
    
    async def _calculate_pair_correlation(
        self,
        symbol1: str,
        symbol2: str
    ) -> Optional[Dict[str, float]]:
        """Calculate correlation between two symbols for different time periods."""
        try:
            prices1 = self.price_history.get(symbol1, [])
            prices2 = self.price_history.get(symbol2, [])
            
            if len(prices1) < 10 or len(prices2) < 10:
                return None
            
            # Ensure equal length
            min_length = min(len(prices1), len(prices2))
            prices1 = prices1[-min_length:]
            prices2 = prices2[-min_length:]
            
            correlations = {}
            
            # Calculate correlations for different periods
            for period_name, period_length in self.lookback_periods.items():
                if min_length >= period_length:
                    p1 = prices1[-period_length:]
                    p2 = prices2[-period_length:]
                    
                    # Calculate returns
                    returns1 = np.diff(p1) / p1[:-1]
                    returns2 = np.diff(p2) / p2[:-1]
                    
                    # Calculate Pearson correlation
                    if len(returns1) > 1 and len(returns2) > 1:
                        corr, p_value = pearsonr(returns1, returns2)
                        correlations[period_name] = float(corr) if not np.isnan(corr) else 0.0
                    else:
                        correlations[period_name] = 0.0
            
            # Current correlation (short-term)
            current_correlation = correlations.get('short', 0.0)
            
            # Calculate rolling correlations
            rolling_correlations = self._calculate_rolling_correlation(prices1, prices2)
            
            return {
                'current': current_correlation,
                'short_term': correlations.get('short', 0.0),
                'medium_term': correlations.get('medium', 0.0),
                'long_term': correlations.get('long', 0.0),
                'rolling_mean': np.mean(rolling_correlations) if rolling_correlations else 0.0,
                'rolling_std': np.std(rolling_correlations) if rolling_correlations else 0.0,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating correlation for {symbol1}-{symbol2}: {e}")
            return None
    
    def _calculate_rolling_correlation(
        self,
        prices1: List[float],
        prices2: List[float],
        window: int = 20
    ) -> List[float]:
        """Calculate rolling correlation with specified window."""
        try:
            if len(prices1) < window or len(prices2) < window:
                return []
            
            rolling_correlations = []
            
            for i in range(window, len(prices1)):
                p1_window = prices1[i-window:i]
                p2_window = prices2[i-window:i]
                
                returns1 = np.diff(p1_window) / p1_window[:-1]
                returns2 = np.diff(p2_window) / p2_window[:-1]
                
                if len(returns1) > 1 and len(returns2) > 1:
                    corr, _ = pearsonr(returns1, returns2)
                    if not np.isnan(corr):
                        rolling_correlations.append(corr)
            
            return rolling_correlations
            
        except Exception as e:
            logger.error(f"Error calculating rolling correlation: {e}")
            return []
    
    async def _detect_divergences(self) -> None:
        """Detect correlation divergences and anomalies."""
        while self.is_running:
            try:
                divergences = {}
                
                for symbol1, symbol2 in self.correlation_pairs:
                    pair_name = f"{symbol1}_{symbol2}"
                    
                    # Get current correlation
                    current_corr = await market_data_cache.get_correlation(pair_name)
                    
                    if current_corr is not None:
                        # Detect divergence patterns
                        divergence_analysis = await self._analyze_divergence(
                            symbol1, symbol2, current_corr
                        )
                        
                        if divergence_analysis:
                            divergences[pair_name] = divergence_analysis
                
                # Cache divergence analysis
                if divergences:
                    await market_data_cache.redis.set(
                        'divergence_analysis',
                        divergences,
                        ttl=300
                    )
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error detecting divergences: {e}")
                await asyncio.sleep(5)
    
    async def _analyze_divergence(
        self,
        symbol1: str,
        symbol2: str,
        current_correlation: float
    ) -> Optional[Dict[str, Any]]:
        """Analyze divergence for a specific pair."""
        try:
            pair_name = f"{symbol1}_{symbol2}"
            
            # Get historical correlation data
            historical_correlations = self.correlation_history.get(pair_name, [])
            
            if len(historical_correlations) < 10:
                return None
            
            # Calculate historical statistics
            hist_mean = np.mean(historical_correlations)
            hist_std = np.std(historical_correlations)
            
            # Calculate z-score
            z_score = (current_correlation - hist_mean) / hist_std if hist_std > 0 else 0
            
            # Determine divergence type
            divergence_type = 'normal'
            if abs(z_score) > 2:
                divergence_type = 'extreme'
            elif abs(z_score) > 1.5:
                divergence_type = 'significant'
            elif abs(z_score) > 1:
                divergence_type = 'moderate'
            
            # Check for correlation breakdown
            is_breakdown = current_correlation < self.correlation_thresholds['breakdown_threshold']
            
            # Calculate divergence strength
            divergence_strength = abs(current_correlation - hist_mean) / (hist_std + 0.01)
            
            # Get price movements
            price_divergence = await self._calculate_price_divergence(symbol1, symbol2)
            
            return {
                'current_correlation': current_correlation,
                'historical_mean': hist_mean,
                'historical_std': hist_std,
                'z_score': z_score,
                'divergence_type': divergence_type,
                'divergence_strength': divergence_strength,
                'is_breakdown': is_breakdown,
                'price_divergence': price_divergence,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing divergence for {symbol1}-{symbol2}: {e}")
            return None
    
    async def _calculate_price_divergence(
        self,
        symbol1: str,
        symbol2: str
    ) -> Dict[str, float]:
        """Calculate price movement divergence between two symbols."""
        try:
            prices1 = self.price_history.get(symbol1, [])
            prices2 = self.price_history.get(symbol2, [])
            
            if len(prices1) < 2 or len(prices2) < 2:
                return {'divergence': 0.0, 'symbol1_change': 0.0, 'symbol2_change': 0.0}
            
            # Calculate recent price changes (last 10 periods)
            lookback = min(10, len(prices1), len(prices2))
            
            change1 = (prices1[-1] - prices1[-lookback]) / prices1[-lookback] * 100
            change2 = (prices2[-1] - prices2[-lookback]) / prices2[-lookback] * 100
            
            # Calculate divergence (difference in percentage changes)
            divergence = abs(change1 - change2)
            
            return {
                'divergence': divergence,
                'symbol1_change': change1,
                'symbol2_change': change2
            }
            
        except Exception as e:
            logger.error(f"Error calculating price divergence: {e}")
            return {'divergence': 0.0, 'symbol1_change': 0.0, 'symbol2_change': 0.0}
    
    async def _generate_cross_ticker_signals(self) -> None:
        """Generate trading signals based on cross-ticker analysis."""
        while self.is_running:
            try:
                signals = []
                
                # Get current correlation matrix
                correlation_matrix = await market_data_cache.redis.get('correlation_matrix')
                
                if correlation_matrix:
                    # Analyze each pair for signal opportunities
                    for pair_name, correlation_data in correlation_matrix.items():
                        signal = await self._analyze_pair_for_signals(pair_name, correlation_data)
                        if signal:
                            signals.append(signal)
                
                # Cache generated signals
                if signals:
                    await market_data_cache.redis.set(
                        'cross_ticker_signals',
                        signals,
                        ttl=300
                    )
                
                await asyncio.sleep(60)  # Generate signals every minute
                
            except Exception as e:
                logger.error(f"Error generating cross-ticker signals: {e}")
                await asyncio.sleep(5)
    
    async def _analyze_pair_for_signals(
        self,
        pair_name: str,
        correlation_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Analyze a correlation pair for trading signals."""
        try:
            symbols = pair_name.split('_')
            if len(symbols) != 2:
                return None
            
            symbol1, symbol2 = symbols
            current_corr = correlation_data.get('current', 0)
            
            # Get divergence analysis
            divergence_data = await market_data_cache.redis.get('divergence_analysis')
            pair_divergence = divergence_data.get(pair_name, {}) if divergence_data else {}
            
            # Signal generation logic
            signal_type = None
            confidence = 0.0
            reasoning = []
            
            # Correlation breakdown signal
            if current_corr < self.correlation_thresholds['breakdown_threshold']:
                signal_type = 'correlation_breakdown'
                confidence += 0.3
                reasoning.append(f"Correlation breakdown detected: {current_corr:.3f}")
            
            # Extreme divergence signal
            if pair_divergence.get('divergence_type') == 'extreme':
                signal_type = 'extreme_divergence'
                confidence += 0.4
                reasoning.append(f"Extreme divergence: z-score {pair_divergence.get('z_score', 0):.2f}")
            
            # Price divergence signal
            price_div = pair_divergence.get('price_divergence', {})
            if price_div.get('divergence', 0) > 2.0:  # 2% price divergence
                signal_type = 'price_divergence'
                confidence += 0.2
                reasoning.append(f"Price divergence: {price_div.get('divergence', 0):.2f}%")
            
            # Mean reversion opportunity
            if abs(current_corr - correlation_data.get('rolling_mean', 0)) > 0.3:
                signal_type = 'mean_reversion'
                confidence += 0.25
                reasoning.append("Mean reversion opportunity detected")
            
            # Only generate signal if confidence is above threshold
            if confidence >= 0.5 and signal_type:
                # Determine which symbol to trade
                target_symbol = self._determine_target_symbol(symbol1, symbol2, pair_divergence)
                
                return {
                    'pair': pair_name,
                    'target_symbol': target_symbol,
                    'signal_type': signal_type,
                    'confidence': min(confidence, 1.0),
                    'correlation': current_corr,
                    'reasoning': reasoning,
                    'divergence_data': pair_divergence,
                    'timestamp': datetime.utcnow().isoformat()
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error analyzing pair {pair_name} for signals: {e}")
            return None
    
    def _determine_target_symbol(
        self,
        symbol1: str,
        symbol2: str,
        divergence_data: Dict[str, Any]
    ) -> str:
        """Determine which symbol to target for trading."""
        try:
            price_div = divergence_data.get('price_divergence', {})
            
            change1 = price_div.get('symbol1_change', 0)
            change2 = price_div.get('symbol2_change', 0)
            
            # Target the symbol with stronger recent movement
            if abs(change1) > abs(change2):
                return symbol1
            else:
                return symbol2
                
        except:
            return symbol1  # Default to first symbol
    
    async def get_correlation_matrix(self) -> Dict[str, Any]:
        """Get current correlation matrix."""
        try:
            correlation_matrix = await market_data_cache.redis.get('correlation_matrix')
            return correlation_matrix or {}
        except Exception as e:
            logger.error(f"Error getting correlation matrix: {e}")
            return {}
    
    async def get_divergence_analysis(self) -> Dict[str, Any]:
        """Get current divergence analysis."""
        try:
            divergence_analysis = await market_data_cache.redis.get('divergence_analysis')
            return divergence_analysis or {}
        except Exception as e:
            logger.error(f"Error getting divergence analysis: {e}")
            return {}
    
    async def get_cross_ticker_signals(self) -> List[Dict[str, Any]]:
        """Get current cross-ticker signals."""
        try:
            signals = await market_data_cache.redis.get('cross_ticker_signals')
            return signals or []
        except Exception as e:
            logger.error(f"Error getting cross-ticker signals: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check engine health."""
        try:
            if not self.is_running:
                return False
            
            # Check if we have recent correlation data
            correlation_matrix = await market_data_cache.redis.get('correlation_matrix')
            if not correlation_matrix:
                return False
            
            # Check if price history is being updated
            for symbol in self.supported_symbols:
                if len(self.price_history.get(symbol, [])) < 10:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"SmartCrossTickerEngine health check failed: {e}")
            return False


class VIXRegimeDetector:
    """
    VIX-based Market Regime Detection Engine
    
    Detects market regimes based on VIX levels and adapts trading parameters accordingly.
    """
    
    def __init__(self):
        self.is_running = False
        self.vix_history = []
        self.regime_history = []
        
        # VIX regime thresholds
        self.vix_thresholds = {
            'low': 15.0,
            'normal': 25.0,
            'high': 35.0,
            'extreme': settings.VIX_EMERGENCY_THRESHOLD
        }
        
        # Adaptation factors for different regimes
        self.adaptation_factors = {
            'low': 1.2,      # Increase position size in low vol
            'normal': 1.0,   # Normal position size
            'high': 0.7,     # Reduce position size in high vol
            'extreme': 0.5   # Significantly reduce in extreme vol
        }
    
    async def initialize(self) -> None:
        """Initialize VIX regime detector."""
        try:
            # Load historical VIX data
            await self._load_vix_history()
            
            logger.info("VIXRegimeDetector initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize VIXRegimeDetector: {e}")
            raise
    
    async def start_regime_detection(self) -> None:
        """Start VIX-based regime detection."""
        try:
            self.is_running = True
            
            # Start background tasks
            asyncio.create_task(self._monitor_vix())
            asyncio.create_task(self._detect_regime_changes())
            asyncio.create_task(self._update_adaptation_factors())
            
            logger.info("VIX regime detection started")
            
        except Exception as e:
            logger.error(f"Failed to start regime detection: {e}")
            raise
    
    async def stop_regime_detection(self) -> None:
        """Stop regime detection."""
        try:
            self.is_running = False
            logger.info("VIX regime detection stopped")
        except Exception as e:
            logger.error(f"Error stopping regime detection: {e}")
    
    async def _load_vix_history(self) -> None:
        """Load historical VIX data."""
        try:
            # Get VIX data from cache or generate mock data
            vix_value = await market_data_cache.get_vix_data()
            
            if vix_value:
                self.vix_history = [vix_value] * 50  # Initialize with current value
            else:
                self.vix_history = [18.5] * 50  # Default VIX level
            
            logger.info("VIX history loaded")
            
        except Exception as e:
            logger.error(f"Error loading VIX history: {e}")
    
    async def _monitor_vix(self) -> None:
        """Monitor VIX levels and update history."""
        while self.is_running:
            try:
                # Get current VIX value
                vix_value = await market_data_cache.get_vix_data()
                
                if vix_value:
                    # Add to history
                    self.vix_history.append(vix_value)
                    
                    # Keep only last 200 values (about 6-7 hours of data)
                    if len(self.vix_history) > 200:
                        self.vix_history = self.vix_history[-200:]
                
                await asyncio.sleep(settings.VIX_REFRESH_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error monitoring VIX: {e}")
                await asyncio.sleep(5)
    
    async def _detect_regime_changes(self) -> None:
        """Detect market regime changes based on VIX."""
        while self.is_running:
            try:
                if len(self.vix_history) < 10:
                    await asyncio.sleep(10)
                    continue
                
                current_vix = self.vix_history[-1]
                
                # Determine current regime
                current_regime = self._classify_regime(current_vix)
                
                # Calculate regime confidence
                confidence = self._calculate_regime_confidence(current_vix)
                
                # Detect regime transitions
                regime_change = await self._detect_regime_transition(current_regime)
                
                # Calculate adaptation factor
                adaptation_factor = self._calculate_adaptation_factor(current_vix, current_regime)
                
                # Prepare regime data
                regime_data = {
                    'regime_type': current_regime,
                    'vix_level': current_vix,
                    'confidence': confidence,
                    'adaptation_factor': adaptation_factor,
                    'regime_change': regime_change,
                    'vix_trend': self._calculate_vix_trend(),
                    'volatility_percentile': self._calculate_vix_percentile(current_vix),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                # Cache regime data
                await market_data_cache.redis.set('market_regime', regime_data, ttl=300)
                
                # Add to regime history
                self.regime_history.append({
                    'regime': current_regime,
                    'vix': current_vix,
                    'timestamp': datetime.utcnow()
                })
                
                # Keep only last 100 regime records
                if len(self.regime_history) > 100:
                    self.regime_history = self.regime_history[-100:]
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error detecting regime changes: {e}")
                await asyncio.sleep(5)
    
    def _classify_regime(self, vix_value: float) -> str:
        """Classify market regime based on VIX value."""
        if vix_value < self.vix_thresholds['low']:
            return 'low_volatility'
        elif vix_value < self.vix_thresholds['normal']:
            return 'normal_volatility'
        elif vix_value < self.vix_thresholds['high']:
            return 'high_volatility'
        else:
            return 'extreme_volatility'
    
    def _calculate_regime_confidence(self, vix_value: float) -> float:
        """Calculate confidence in regime classification."""
        try:
            # Calculate distance from regime boundaries
            thresholds = list(self.vix_thresholds.values())
            
            # Find closest thresholds
            distances = [abs(vix_value - threshold) for threshold in thresholds]
            min_distance = min(distances)
            
            # Convert distance to confidence (higher distance = higher confidence)
            confidence = min(1.0, min_distance / 5.0)  # Normalize by 5 VIX points
            
            return confidence
            
        except:
            return 0.5  # Default confidence
    
    async def _detect_regime_transition(self, current_regime: str) -> bool:
        """Detect if regime has changed."""
        try:
            if len(self.regime_history) < 5:
                return False
            
            # Check last 5 regime classifications
            recent_regimes = [r['regime'] for r in self.regime_history[-5:]]
            
            # If current regime is different from recent consensus, it's a transition
            regime_counts = {}
            for regime in recent_regimes:
                regime_counts[regime] = regime_counts.get(regime, 0) + 1
            
            most_common_regime = max(regime_counts, key=regime_counts.get)
            
            return current_regime != most_common_regime
            
        except:
            return False
    
    def _calculate_adaptation_factor(self, vix_value: float, regime: str) -> float:
        """Calculate risk adaptation factor."""
        try:
            base_factor = self.adaptation_factors.get(regime.split('_')[0], 1.0)
            
            # Fine-tune based on exact VIX level
            if vix_value > 40:
                base_factor *= 0.8  # Further reduce in extreme conditions
            elif vix_value < 12:
                base_factor *= 1.1  # Slightly increase in very low vol
            
            return round(base_factor, 2)
            
        except:
            return 1.0
    
    def _calculate_vix_trend(self) -> str:
        """Calculate VIX trend direction."""
        try:
            if len(self.vix_history) < 10:
                return 'neutral'
            
            recent_vix = self.vix_history[-10:]
            
            # Calculate linear trend
            x = np.arange(len(recent_vix))
            slope = np.polyfit(x, recent_vix, 1)[0]
            
            if slope > 0.5:
                return 'rising'
            elif slope < -0.5:
                return 'falling'
            else:
                return 'neutral'
                
        except:
            return 'neutral'
    
    def _calculate_vix_percentile(self, current_vix: float) -> float:
        """Calculate VIX percentile relative to recent history."""
        try:
            if len(self.vix_history) < 20:
                return 50.0
            
            # Calculate percentile relative to last 100 observations
            recent_history = self.vix_history[-100:]
            percentile = (sum(1 for v in recent_history if v <= current_vix) / len(recent_history)) * 100
            
            return round(percentile, 1)
            
        except:
            return 50.0
    
    async def _update_adaptation_factors(self) -> None:
        """Update system-wide adaptation factors based on regime."""
        while self.is_running:
            try:
                regime_data = await market_data_cache.redis.get('market_regime')
                
                if regime_data:
                    adaptation_factor = regime_data.get('adaptation_factor', 1.0)
                    
                    # Update trading parameters based on adaptation factor
                    adapted_params = {
                        'position_size_multiplier': adaptation_factor,
                        'confidence_threshold_adjustment': 0.05 if adaptation_factor < 0.8 else 0.0,
                        'stop_loss_tightening': 0.02 if adaptation_factor < 0.7 else 0.0,
                        'profit_target_adjustment': 0.02 if adaptation_factor > 1.1 else 0.0
                    }
                    
                    # Cache adapted parameters
                    await market_data_cache.redis.set(
                        'adapted_trading_params',
                        adapted_params,
                        ttl=300
                    )
                
                await asyncio.sleep(60)  # Update every minute
                
            except Exception as e:
                logger.error(f"Error updating adaptation factors: {e}")
                await asyncio.sleep(5)
    
    async def get_current_regime(self) -> Dict[str, Any]:
        """Get current market regime data."""
        try:
            regime_data = await market_data_cache.redis.get('market_regime')
            return regime_data or {}
        except Exception as e:
            logger.error(f"Error getting current regime: {e}")
            return {}
    
    async def get_adapted_parameters(self) -> Dict[str, Any]:
        """Get current adapted trading parameters."""
        try:
            adapted_params = await market_data_cache.redis.get('adapted_trading_params')
            return adapted_params or {}
        except Exception as e:
            logger.error(f"Error getting adapted parameters: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check regime detector health."""
        try:
            if not self.is_running:
                return False
            
            # Check if we have recent VIX data
            if len(self.vix_history) < 5:
                return False
            
            # Check if regime data is being updated
            regime_data = await market_data_cache.redis.get('market_regime')
            if not regime_data:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"VIXRegimeDetector health check failed: {e}")
            return False


# Global intelligence service instances
smart_cross_ticker_engine = SmartCrossTickerEngine()
vix_regime_detector = VIXRegimeDetector()

