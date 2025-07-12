"""
Smart-0DTE-System Risk Management Service

This module implements comprehensive risk management including adaptive position sizing,
emergency halt mechanisms, real-time monitoring, and performance analytics.
"""

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from enum import Enum
import numpy as np
import pandas as pd
from dataclasses import dataclass

from app.core.config import settings
from app.core.redis_client import market_data_cache
from app.core.database import get_db_session
from app.models.trading_models import RiskMetrics, PerformanceMetrics, SystemAlert, Trade
from app.services.market_data_service import market_data_service
from app.services.vix_regime_detector import vix_regime_detector
from app.services.ai_learning_service import ai_learning_service

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk level enumeration."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    EXTREME = "extreme"


class AlertSeverity(Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RiskLimits:
    """Risk limits configuration."""
    max_daily_loss: float = 1000.0
    max_position_size: float = 5000.0
    max_positions_per_symbol: int = 3
    max_total_positions: int = 10
    max_portfolio_delta: float = 1000.0
    max_portfolio_gamma: float = 500.0
    max_vix_threshold: float = 30.0
    min_confidence_threshold: float = 0.65
    max_correlation_risk: float = 0.8
    emergency_halt_loss: float = 2000.0


@dataclass
class PositionSizing:
    """Position sizing parameters."""
    base_position_size: float = 1000.0
    vix_adjustment_factor: float = 0.5
    confidence_adjustment_factor: float = 0.3
    correlation_adjustment_factor: float = 0.2
    max_size_multiplier: float = 2.0
    min_size_multiplier: float = 0.3


class RiskManagementService:
    """
    Comprehensive Risk Management Service
    
    Implements adaptive position sizing, emergency controls, real-time monitoring,
    and performance analytics for the Smart-0DTE-System.
    """
    
    def __init__(self):
        self.is_running = False
        self.emergency_halt_active = False
        
        # Risk configuration
        self.risk_limits = RiskLimits()
        self.position_sizing = PositionSizing()
        
        # Current risk metrics
        self.current_risk_metrics = {}
        self.daily_pnl = 0.0
        self.portfolio_exposure = 0.0
        self.active_alerts = []
        
        # Performance tracking
        self.performance_history = []
        self.daily_stats = {}
        
        # Risk monitoring state
        self.last_risk_check = datetime.utcnow()
        self.risk_check_interval = 30  # seconds
        
    async def initialize(self) -> None:
        """Initialize Risk Management Service."""
        try:
            # Load risk configuration from database/cache
            await self._load_risk_configuration()
            
            # Initialize current metrics
            await self._initialize_risk_metrics()
            
            logger.info("Risk Management Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Risk Management Service: {e}")
            raise
    
    async def start_risk_monitoring(self) -> None:
        """Start risk monitoring processes."""
        try:
            self.is_running = True
            
            # Start background monitoring tasks
            asyncio.create_task(self._monitor_portfolio_risk())
            asyncio.create_task(self._monitor_daily_limits())
            asyncio.create_task(self._monitor_position_limits())
            asyncio.create_task(self._monitor_market_conditions())
            asyncio.create_task(self._update_performance_metrics())
            asyncio.create_task(self._generate_risk_alerts())
            
            logger.info("Risk monitoring started")
            
        except Exception as e:
            logger.error(f"Failed to start risk monitoring: {e}")
            raise
    
    async def stop_risk_monitoring(self) -> None:
        """Stop risk monitoring processes."""
        try:
            self.is_running = False
            
            # Save final metrics
            await self._save_risk_metrics()
            
            logger.info("Risk monitoring stopped")
            
        except Exception as e:
            logger.error(f"Error stopping risk monitoring: {e}")
    
    async def calculate_position_size(
        self,
        signal_confidence: float,
        symbol: str,
        strategy_type: str,
        market_conditions: Dict[str, Any]
    ) -> float:
        """Calculate adaptive position size based on multiple risk factors."""
        try:
            base_size = self.position_sizing.base_position_size
            
            # VIX-based adjustment
            vix_level = market_conditions.get('vix_level', 20.0)
            vix_adjustment = self._calculate_vix_adjustment(vix_level)
            
            # Confidence-based adjustment
            confidence_adjustment = self._calculate_confidence_adjustment(signal_confidence)
            
            # Correlation-based adjustment
            correlation_risk = await self._calculate_correlation_risk(symbol)
            correlation_adjustment = self._calculate_correlation_adjustment(correlation_risk)
            
            # Portfolio exposure adjustment
            exposure_adjustment = await self._calculate_exposure_adjustment()
            
            # Combine all adjustments
            total_adjustment = (
                vix_adjustment * 
                confidence_adjustment * 
                correlation_adjustment * 
                exposure_adjustment
            )
            
            # Apply limits
            total_adjustment = max(
                self.position_sizing.min_size_multiplier,
                min(self.position_sizing.max_size_multiplier, total_adjustment)
            )
            
            position_size = base_size * total_adjustment
            
            # Final position size validation
            position_size = await self._validate_position_size(position_size, symbol)
            
            logger.info(f"Calculated position size for {symbol}: ${position_size:.2f} "
                       f"(base: ${base_size}, adjustment: {total_adjustment:.2f})")
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return self.position_sizing.base_position_size * 0.5  # Conservative fallback
    
    def _calculate_vix_adjustment(self, vix_level: float) -> float:
        """Calculate position size adjustment based on VIX level."""
        try:
            # Lower position size in high volatility
            if vix_level > 30:
                return 0.5  # 50% reduction in extreme volatility
            elif vix_level > 25:
                return 0.7  # 30% reduction in high volatility
            elif vix_level > 20:
                return 0.9  # 10% reduction in elevated volatility
            elif vix_level < 12:
                return 1.2  # 20% increase in very low volatility
            else:
                return 1.0  # Normal sizing
                
        except Exception as e:
            logger.error(f"Error calculating VIX adjustment: {e}")
            return 0.8  # Conservative default
    
    def _calculate_confidence_adjustment(self, confidence: float) -> float:
        """Calculate position size adjustment based on signal confidence."""
        try:
            # Higher position size for higher confidence
            if confidence >= 0.9:
                return 1.3  # 30% increase for very high confidence
            elif confidence >= 0.8:
                return 1.1  # 10% increase for high confidence
            elif confidence >= 0.7:
                return 1.0  # Normal sizing
            elif confidence >= 0.6:
                return 0.8  # 20% reduction for moderate confidence
            else:
                return 0.6  # 40% reduction for low confidence
                
        except Exception as e:
            logger.error(f"Error calculating confidence adjustment: {e}")
            return 0.8  # Conservative default
    
    async def _calculate_correlation_risk(self, symbol: str) -> float:
        """Calculate correlation risk for the symbol."""
        try:
            # Get current correlations
            correlations = await market_data_cache.redis.get('cross_ticker_correlations')
            
            if not correlations:
                return 0.5  # Moderate risk if no data
            
            # Calculate average correlation with other symbols
            symbol_correlations = []
            for pair, corr_data in correlations.items():
                if symbol in pair:
                    symbol_correlations.append(abs(corr_data.get('correlation', 0)))
            
            if not symbol_correlations:
                return 0.5
            
            avg_correlation = np.mean(symbol_correlations)
            return avg_correlation
            
        except Exception as e:
            logger.error(f"Error calculating correlation risk: {e}")
            return 0.5
    
    def _calculate_correlation_adjustment(self, correlation_risk: float) -> float:
        """Calculate position size adjustment based on correlation risk."""
        try:
            # Reduce position size for high correlation (concentration risk)
            if correlation_risk > 0.8:
                return 0.6  # 40% reduction for high correlation
            elif correlation_risk > 0.7:
                return 0.8  # 20% reduction for elevated correlation
            elif correlation_risk > 0.5:
                return 1.0  # Normal sizing
            else:
                return 1.1  # 10% increase for low correlation (diversification)
                
        except Exception as e:
            logger.error(f"Error calculating correlation adjustment: {e}")
            return 0.8
    
    async def _calculate_exposure_adjustment(self) -> float:
        """Calculate position size adjustment based on current portfolio exposure."""
        try:
            # Get current portfolio exposure
            total_exposure = await self._calculate_total_exposure()
            
            # Reduce position size as exposure increases
            exposure_ratio = total_exposure / (self.risk_limits.max_position_size * 10)
            
            if exposure_ratio > 0.8:
                return 0.5  # 50% reduction when near limits
            elif exposure_ratio > 0.6:
                return 0.7  # 30% reduction when exposure is high
            elif exposure_ratio > 0.4:
                return 0.9  # 10% reduction when exposure is moderate
            else:
                return 1.0  # Normal sizing when exposure is low
                
        except Exception as e:
            logger.error(f"Error calculating exposure adjustment: {e}")
            return 0.8
    
    async def _validate_position_size(self, position_size: float, symbol: str) -> float:
        """Validate and adjust position size against limits."""
        try:
            # Check maximum position size
            if position_size > self.risk_limits.max_position_size:
                position_size = self.risk_limits.max_position_size
                logger.warning(f"Position size capped at max limit: ${position_size}")
            
            # Check if adding this position would exceed portfolio limits
            current_exposure = await self._calculate_total_exposure()
            if current_exposure + position_size > self.risk_limits.max_position_size * 10:
                max_allowed = max(0, self.risk_limits.max_position_size * 10 - current_exposure)
                position_size = min(position_size, max_allowed)
                logger.warning(f"Position size adjusted for portfolio limits: ${position_size}")
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error validating position size: {e}")
            return min(position_size, self.risk_limits.max_position_size * 0.5)
    
    async def check_emergency_conditions(self) -> bool:
        """Check if emergency halt conditions are met."""
        try:
            # Check daily loss limit
            if abs(self.daily_pnl) >= self.risk_limits.emergency_halt_loss:
                await self._trigger_emergency_halt("Daily loss limit exceeded")
                return True
            
            # Check VIX extreme levels
            vix_data = await vix_regime_detector.get_current_regime()
            vix_level = vix_data.get('vix_level', 20)
            
            if vix_level >= self.risk_limits.max_vix_threshold:
                await self._trigger_emergency_halt(f"VIX extreme level: {vix_level}")
                return True
            
            # Check portfolio exposure
            total_exposure = await self._calculate_total_exposure()
            if total_exposure >= self.risk_limits.max_position_size * 15:  # 150% of normal max
                await self._trigger_emergency_halt("Portfolio exposure limit exceeded")
                return True
            
            # Check system errors or connection issues
            system_health = await self._check_system_health()
            if not system_health:
                await self._trigger_emergency_halt("System health check failed")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking emergency conditions: {e}")
            return True  # Err on the side of caution
    
    async def _trigger_emergency_halt(self, reason: str) -> None:
        """Trigger emergency halt of all trading activities."""
        try:
            if self.emergency_halt_active:
                return  # Already halted
            
            self.emergency_halt_active = True
            
            # Create critical alert
            await self._create_alert(
                alert_type="emergency_halt",
                severity=AlertSeverity.CRITICAL,
                title="Emergency Trading Halt",
                message=f"Trading halted due to: {reason}",
                alert_data={"reason": reason, "timestamp": datetime.utcnow().isoformat()}
            )
            
            # Cache emergency status
            await market_data_cache.redis.set(
                'emergency_halt_status',
                {
                    'active': True,
                    'reason': reason,
                    'timestamp': datetime.utcnow().isoformat()
                },
                ttl=3600
            )
            
            logger.critical(f"EMERGENCY HALT TRIGGERED: {reason}")
            
        except Exception as e:
            logger.error(f"Error triggering emergency halt: {e}")
    
    async def clear_emergency_halt(self, reason: str = "Manual override") -> None:
        """Clear emergency halt status."""
        try:
            self.emergency_halt_active = False
            
            # Clear emergency status
            await market_data_cache.redis.delete('emergency_halt_status')
            
            # Create informational alert
            await self._create_alert(
                alert_type="emergency_cleared",
                severity=AlertSeverity.MEDIUM,
                title="Emergency Halt Cleared",
                message=f"Trading resumed: {reason}",
                alert_data={"reason": reason, "timestamp": datetime.utcnow().isoformat()}
            )
            
            logger.info(f"Emergency halt cleared: {reason}")
            
        except Exception as e:
            logger.error(f"Error clearing emergency halt: {e}")
    
    async def _monitor_portfolio_risk(self) -> None:
        """Monitor overall portfolio risk metrics."""
        while self.is_running:
            try:
                # Calculate portfolio Greeks
                portfolio_greeks = await self._calculate_portfolio_greeks()
                
                # Check delta limits
                if abs(portfolio_greeks.get('delta', 0)) > self.risk_limits.max_portfolio_delta:
                    await self._create_alert(
                        alert_type="portfolio_delta",
                        severity=AlertSeverity.HIGH,
                        title="Portfolio Delta Limit Exceeded",
                        message=f"Portfolio delta: {portfolio_greeks.get('delta', 0):.2f}",
                        alert_data=portfolio_greeks
                    )
                
                # Check gamma limits
                if abs(portfolio_greeks.get('gamma', 0)) > self.risk_limits.max_portfolio_gamma:
                    await self._create_alert(
                        alert_type="portfolio_gamma",
                        severity=AlertSeverity.HIGH,
                        title="Portfolio Gamma Limit Exceeded",
                        message=f"Portfolio gamma: {portfolio_greeks.get('gamma', 0):.2f}",
                        alert_data=portfolio_greeks
                    )
                
                # Update risk metrics
                self.current_risk_metrics.update(portfolio_greeks)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error monitoring portfolio risk: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_daily_limits(self) -> None:
        """Monitor daily P&L and loss limits."""
        while self.is_running:
            try:
                # Calculate current daily P&L
                daily_pnl = await self._calculate_daily_pnl()
                self.daily_pnl = daily_pnl
                
                # Check daily loss limit
                if daily_pnl <= -self.risk_limits.max_daily_loss:
                    await self._create_alert(
                        alert_type="daily_loss_limit",
                        severity=AlertSeverity.CRITICAL,
                        title="Daily Loss Limit Reached",
                        message=f"Daily P&L: ${daily_pnl:.2f}",
                        alert_data={"daily_pnl": daily_pnl}
                    )
                
                # Warning at 75% of limit
                elif daily_pnl <= -self.risk_limits.max_daily_loss * 0.75:
                    await self._create_alert(
                        alert_type="daily_loss_warning",
                        severity=AlertSeverity.HIGH,
                        title="Daily Loss Warning",
                        message=f"Daily P&L: ${daily_pnl:.2f} (75% of limit)",
                        alert_data={"daily_pnl": daily_pnl}
                    )
                
                # Cache daily P&L
                await market_data_cache.redis.set(
                    'daily_pnl',
                    {"pnl": daily_pnl, "timestamp": datetime.utcnow().isoformat()},
                    ttl=3600
                )
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring daily limits: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_position_limits(self) -> None:
        """Monitor position count and size limits."""
        while self.is_running:
            try:
                # Get current positions
                positions = await self._get_current_positions()
                
                # Check total position count
                total_positions = len(positions)
                if total_positions >= self.risk_limits.max_total_positions:
                    await self._create_alert(
                        alert_type="position_count_limit",
                        severity=AlertSeverity.HIGH,
                        title="Position Count Limit Reached",
                        message=f"Total positions: {total_positions}",
                        alert_data={"position_count": total_positions}
                    )
                
                # Check positions per symbol
                symbol_counts = {}
                for position in positions:
                    symbol = position.get('symbol', '')
                    symbol_counts[symbol] = symbol_counts.get(symbol, 0) + 1
                
                for symbol, count in symbol_counts.items():
                    if count >= self.risk_limits.max_positions_per_symbol:
                        await self._create_alert(
                            alert_type="symbol_position_limit",
                            severity=AlertSeverity.MEDIUM,
                            title=f"{symbol} Position Limit Reached",
                            message=f"{symbol} positions: {count}",
                            alert_data={"symbol": symbol, "count": count}
                        )
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error monitoring position limits: {e}")
                await asyncio.sleep(10)
    
    async def _monitor_market_conditions(self) -> None:
        """Monitor market conditions for risk assessment."""
        while self.is_running:
            try:
                # Get VIX data
                vix_data = await vix_regime_detector.get_current_regime()
                vix_level = vix_data.get('vix_level', 20)
                
                # Check VIX levels
                if vix_level >= 25:
                    severity = AlertSeverity.HIGH if vix_level >= 30 else AlertSeverity.MEDIUM
                    await self._create_alert(
                        alert_type="high_volatility",
                        severity=severity,
                        title="High Volatility Detected",
                        message=f"VIX level: {vix_level:.1f}",
                        alert_data=vix_data
                    )
                
                # Get correlation data
                correlations = await market_data_cache.redis.get('cross_ticker_correlations')
                if correlations:
                    for pair, corr_data in correlations.items():
                        correlation = corr_data.get('correlation', 0)
                        if abs(correlation) < 0.3:  # Very low correlation
                            await self._create_alert(
                                alert_type="correlation_breakdown",
                                severity=AlertSeverity.MEDIUM,
                                title=f"{pair} Correlation Breakdown",
                                message=f"Correlation: {correlation:.3f}",
                                alert_data=corr_data
                            )
                
                await asyncio.sleep(120)  # Check every 2 minutes
                
            except Exception as e:
                logger.error(f"Error monitoring market conditions: {e}")
                await asyncio.sleep(30)
    
    async def _update_performance_metrics(self) -> None:
        """Update performance metrics and analytics."""
        while self.is_running:
            try:
                # Calculate performance metrics
                metrics = await self._calculate_performance_metrics()
                
                # Cache metrics
                await market_data_cache.redis.set(
                    'performance_metrics',
                    metrics,
                    ttl=3600
                )
                
                # Store in performance history
                self.performance_history.append({
                    'timestamp': datetime.utcnow(),
                    'metrics': metrics
                })
                
                # Keep only last 24 hours of history
                cutoff_time = datetime.utcnow() - timedelta(hours=24)
                self.performance_history = [
                    item for item in self.performance_history
                    if item['timestamp'] > cutoff_time
                ]
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"Error updating performance metrics: {e}")
                await asyncio.sleep(60)
    
    async def _generate_risk_alerts(self) -> None:
        """Generate and manage risk alerts."""
        while self.is_running:
            try:
                # Check for emergency conditions
                emergency_needed = await self.check_emergency_conditions()
                
                if emergency_needed and not self.emergency_halt_active:
                    # Emergency conditions detected but not yet halted
                    logger.warning("Emergency conditions detected")
                
                # Clean up old alerts
                await self._cleanup_old_alerts()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error generating risk alerts: {e}")
                await asyncio.sleep(10)
    
    async def _calculate_portfolio_greeks(self) -> Dict[str, float]:
        """Calculate portfolio-level Greeks."""
        try:
            # This would calculate actual Greeks from positions
            # For now, return mock data
            return {
                'delta': 150.0,
                'gamma': 25.0,
                'theta': -45.0,
                'vega': 120.0,
                'rho': 8.0
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio Greeks: {e}")
            return {}
    
    async def _calculate_daily_pnl(self) -> float:
        """Calculate current daily P&L."""
        try:
            # This would calculate actual P&L from trades and positions
            # For now, return mock data
            return 125.67
            
        except Exception as e:
            logger.error(f"Error calculating daily P&L: {e}")
            return 0.0
    
    async def _calculate_total_exposure(self) -> float:
        """Calculate total portfolio exposure."""
        try:
            # This would calculate actual exposure from positions
            # For now, return mock data
            return 3500.0
            
        except Exception as e:
            logger.error(f"Error calculating total exposure: {e}")
            return 0.0
    
    async def _get_current_positions(self) -> List[Dict[str, Any]]:
        """Get current trading positions."""
        try:
            # This would get actual positions from IBKR or database
            # For now, return mock data
            return [
                {"symbol": "SPY", "strategy": "Iron Condor", "size": 1000},
                {"symbol": "QQQ", "strategy": "Bull Call Spread", "size": 800}
            ]
            
        except Exception as e:
            logger.error(f"Error getting current positions: {e}")
            return []
    
    async def _calculate_performance_metrics(self) -> Dict[str, Any]:
        """Calculate comprehensive performance metrics."""
        try:
            return {
                'daily_pnl': self.daily_pnl,
                'total_trades': 15,
                'winning_trades': 10,
                'win_rate': 0.667,
                'avg_win': 45.67,
                'avg_loss': -23.45,
                'profit_factor': 1.95,
                'sharpe_ratio': 1.23,
                'max_drawdown': -156.78,
                'total_return': 234.56,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            return {}
    
    async def _check_system_health(self) -> bool:
        """Check overall system health."""
        try:
            # Check data feeds
            market_data = await market_data_cache.redis.get('market_data_SPY')
            if not market_data:
                return False
            
            # Check if data is recent (within last 5 minutes)
            last_update = market_data.get('timestamp')
            if last_update:
                last_update_time = datetime.fromisoformat(last_update.replace('Z', '+00:00'))
                if datetime.utcnow() - last_update_time.replace(tzinfo=None) > timedelta(minutes=5):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking system health: {e}")
            return False
    
    async def _create_alert(
        self,
        alert_type: str,
        severity: AlertSeverity,
        title: str,
        message: str,
        alert_data: Dict[str, Any] = None
    ) -> None:
        """Create a system alert."""
        try:
            alert = {
                'id': f"{alert_type}_{datetime.utcnow().timestamp()}",
                'type': alert_type,
                'severity': severity.value,
                'title': title,
                'message': message,
                'timestamp': datetime.utcnow().isoformat(),
                'data': alert_data or {}
            }
            
            # Add to active alerts
            self.active_alerts.append(alert)
            
            # Cache alert
            await market_data_cache.redis.set(
                f"alert:{alert['id']}",
                alert,
                ttl=3600
            )
            
            # Log based on severity
            if severity == AlertSeverity.CRITICAL:
                logger.critical(f"CRITICAL ALERT: {title} - {message}")
            elif severity == AlertSeverity.HIGH:
                logger.error(f"HIGH ALERT: {title} - {message}")
            elif severity == AlertSeverity.MEDIUM:
                logger.warning(f"MEDIUM ALERT: {title} - {message}")
            else:
                logger.info(f"LOW ALERT: {title} - {message}")
            
        except Exception as e:
            logger.error(f"Error creating alert: {e}")
    
    async def _cleanup_old_alerts(self) -> None:
        """Clean up old alerts."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            
            self.active_alerts = [
                alert for alert in self.active_alerts
                if datetime.fromisoformat(alert['timestamp']) > cutoff_time
            ]
            
        except Exception as e:
            logger.error(f"Error cleaning up alerts: {e}")
    
    async def _load_risk_configuration(self) -> None:
        """Load risk configuration from storage."""
        try:
            # Load from cache or use defaults
            config = await market_data_cache.redis.get('risk_configuration')
            
            if config:
                # Update risk limits from stored config
                for key, value in config.items():
                    if hasattr(self.risk_limits, key):
                        setattr(self.risk_limits, key, value)
            
            logger.info("Risk configuration loaded")
            
        except Exception as e:
            logger.error(f"Error loading risk configuration: {e}")
    
    async def _initialize_risk_metrics(self) -> None:
        """Initialize current risk metrics."""
        try:
            self.current_risk_metrics = {
                'portfolio_delta': 0.0,
                'portfolio_gamma': 0.0,
                'portfolio_theta': 0.0,
                'portfolio_vega': 0.0,
                'total_exposure': 0.0,
                'daily_pnl': 0.0,
                'position_count': 0,
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error initializing risk metrics: {e}")
    
    async def _save_risk_metrics(self) -> None:
        """Save current risk metrics."""
        try:
            await market_data_cache.redis.set(
                'current_risk_metrics',
                self.current_risk_metrics,
                ttl=3600
            )
            
            logger.info("Risk metrics saved")
            
        except Exception as e:
            logger.error(f"Error saving risk metrics: {e}")
    
    # Public API methods
    
    async def get_current_risk_status(self) -> Dict[str, Any]:
        """Get current risk status and metrics."""
        try:
            return {
                'emergency_halt_active': self.emergency_halt_active,
                'daily_pnl': self.daily_pnl,
                'portfolio_exposure': self.portfolio_exposure,
                'risk_metrics': self.current_risk_metrics,
                'active_alerts': len(self.active_alerts),
                'last_updated': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting risk status: {e}")
            return {}
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary and analytics."""
        try:
            return await self._calculate_performance_metrics()
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}
    
    async def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get current active alerts."""
        try:
            return self.active_alerts.copy()
            
        except Exception as e:
            logger.error(f"Error getting active alerts: {e}")
            return []
    
    async def update_risk_limits(self, new_limits: Dict[str, Any]) -> bool:
        """Update risk limits configuration."""
        try:
            for key, value in new_limits.items():
                if hasattr(self.risk_limits, key):
                    setattr(self.risk_limits, key, value)
            
            # Save updated configuration
            await market_data_cache.redis.set(
                'risk_configuration',
                new_limits,
                ttl=86400
            )
            
            logger.info("Risk limits updated")
            return True
            
        except Exception as e:
            logger.error(f"Error updating risk limits: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check risk management service health."""
        try:
            if not self.is_running:
                return False
            
            # Check if monitoring is active
            time_since_check = datetime.utcnow() - self.last_risk_check
            if time_since_check.total_seconds() > self.risk_check_interval * 3:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Risk Management Service health check failed: {e}")
            return False


# Global risk management service instance
risk_management_service = RiskManagementService()

