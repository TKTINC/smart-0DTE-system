"""
Risk Management Service for Smart-0DTE-System
Implements comprehensive risk management with enhanced bet sizing requirements.

Account Size: $60,000
Minimum Bet Size: $12,000 (20% of account)
Maximum Bet Size: Variable based on signal strength, up to $24,000 (40% of account)
"""

import logging
import math
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskLimits:
    """Risk limits configuration."""
    def __init__(self, account_size: float = 60000.0):
        # Base parameters on account size
        self.account_size = account_size
        self.max_daily_loss = account_size * 0.10  # 10% of account
        self.max_position_size = account_size * 0.40  # 40% of account
        self.min_position_size = account_size * 0.20  # 20% of account
        self.max_positions_per_symbol = 2
        self.max_total_positions = 5
        self.max_portfolio_delta = account_size * 0.10  # 10% of account
        self.max_portfolio_gamma = account_size * 0.05  # 5% of account
        self.max_vix_threshold = 30.0
        self.min_confidence_threshold = 0.65
        self.max_correlation_risk = 0.8
        self.emergency_halt_loss = account_size * 0.20  # 20% of account


class PositionSizing:
    """Position sizing parameters."""
    def __init__(self, account_size: float = 60000.0):
        # Base parameters on account size
        self.account_size = account_size
        self.min_position_size = account_size * 0.20  # 20% of account = $12,000
        self.base_position_size = self.min_position_size  # Start with minimum
        self.vix_adjustment_factor = 0.5
        self.confidence_adjustment_factor = 0.3
        self.correlation_adjustment_factor = 0.2
        self.max_size_multiplier = 2.0  # Up to 2x minimum = $24,000
        self.min_size_multiplier = 1.0  # Never go below minimum


class TakeProfitTier:
    """Defines a tier in the take-profit strategy."""
    def __init__(self, percentage: float, position_percentage: float):
        self.percentage = percentage  # Profit percentage
        self.position_percentage = position_percentage  # Percentage of position to close
        self.triggered = False  # Whether this tier has been triggered


class TieredTakeProfitStrategy:
    """Implements a tiered take-profit strategy."""
    
    def __init__(self, position_id: int, entry_price: float, position_size: float):
        self.position_id = position_id
        self.entry_price = entry_price
        self.position_size = position_size
        self.remaining_size = position_size
        
        # Define tiers based on time of day
        current_hour = datetime.utcnow().hour
        
        if current_hour < 11:  # Morning entries (before 11 AM)
            self.tiers = [
                TakeProfitTier(0.05, 0.33),  # 5% profit, close 33% of position
                TakeProfitTier(0.10, 0.33),  # 10% profit, close 33% of position
                TakeProfitTier(0.15, 0.34)   # 15% profit, close remaining 34%
            ]
        elif current_hour < 14:  # Midday entries (11 AM - 2 PM)
            self.tiers = [
                TakeProfitTier(0.03, 0.33),  # 3% profit, close 33% of position
                TakeProfitTier(0.07, 0.33),  # 7% profit, close 33% of position
                TakeProfitTier(0.12, 0.34)   # 12% profit, close remaining 34%
            ]
        else:  # Late day entries (after 2 PM)
            self.tiers = [
                TakeProfitTier(0.05, 1.0)    # 5% profit, close entire position
            ]
    
    def check_take_profit(self, current_price: float) -> Dict[str, Any]:
        """
        Check if any take-profit tiers have been triggered.
        
        Returns:
            Dictionary with action details if a tier is triggered, None otherwise
        """
        if self.remaining_size <= 0:
            return None  # No position remaining
        
        current_profit_pct = (current_price - self.entry_price) / self.entry_price
        
        for tier in self.tiers:
            if not tier.triggered and current_profit_pct >= tier.percentage:
                # Mark tier as triggered
                tier.triggered = True
                
                # Calculate size to close
                size_to_close = self.position_size * tier.position_percentage
                
                # Update remaining size
                self.remaining_size -= size_to_close
                
                return {
                    "action": "partial_close",
                    "position_id": self.position_id,
                    "size_to_close": size_to_close,
                    "percentage_to_close": tier.position_percentage,
                    "profit_percentage": current_profit_pct,
                    "tier_target": tier.percentage,
                    "remaining_size": self.remaining_size
                }
        
        return None  # No tiers triggered


class RiskManagementService:
    """
    Comprehensive Risk Management Service for Smart-0DTE-System
    """
    
    def __init__(self, account_size: float = 60000.0):
        self.is_running = False
        self.emergency_halt_active = False
        self.account_size = account_size
        
        # Risk configuration
        self.risk_limits = RiskLimits(account_size)
        self.position_sizing = PositionSizing(account_size)
        
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
        
        # Take-profit strategies
        self.take_profit_strategies = {}
        
        logger.info(f"Risk Management Service initialized with account size: ${account_size}")
        logger.info(f"Minimum position size: ${self.position_sizing.min_position_size}")
        logger.info(f"Maximum position size: ${self.risk_limits.max_position_size}")
    
    async def start(self):
        """Start the risk management service."""
        if self.is_running:
            logger.warning("Risk Management Service is already running")
            return
        
        self.is_running = True
        logger.info("Risk Management Service started")
        
        # Start background risk monitoring
        asyncio.create_task(self._monitor_risk())
    
    async def stop(self):
        """Stop the risk management service."""
        if not self.is_running:
            logger.warning("Risk Management Service is not running")
            return
        
        self.is_running = False
        logger.info("Risk Management Service stopped")
    
    async def _monitor_risk(self):
        """Background task to monitor risk metrics."""
        while self.is_running:
            try:
                # Check if it's time to perform a risk check
                now = datetime.utcnow()
                if (now - self.last_risk_check).total_seconds() >= self.risk_check_interval:
                    await self._perform_risk_check()
                    self.last_risk_check = now
                
                # Sleep to avoid high CPU usage
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error in risk monitoring: {e}")
                await asyncio.sleep(5)  # Sleep longer on error
    
    async def _perform_risk_check(self):
        """Perform a comprehensive risk check."""
        try:
            # Check daily loss limit
            if self.daily_pnl <= -self.risk_limits.max_daily_loss:
                self._trigger_emergency_halt("Daily loss limit exceeded")
                return
            
            # Check portfolio exposure
            if self.portfolio_exposure > self.account_size * 0.8:
                self._add_alert("High portfolio exposure", "warning")
            
            # Check VIX level
            vix_level = await self._get_current_vix()
            if vix_level > self.risk_limits.max_vix_threshold:
                self._add_alert(f"VIX above threshold: {vix_level}", "warning")
            
            # Check correlation risk
            correlation_risk = await self._calculate_portfolio_correlation()
            if correlation_risk > self.risk_limits.max_correlation_risk:
                self._add_alert(f"High correlation risk: {correlation_risk}", "warning")
            
            # Update risk metrics
            self.current_risk_metrics = {
                "daily_pnl": self.daily_pnl,
                "portfolio_exposure": self.portfolio_exposure,
                "vix_level": vix_level,
                "correlation_risk": correlation_risk,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error performing risk check: {e}")
    
    def _trigger_emergency_halt(self, reason: str):
        """Trigger an emergency halt to trading."""
        if not self.emergency_halt_active:
            self.emergency_halt_active = True
            logger.critical(f"EMERGENCY HALT TRIGGERED: {reason}")
            self._add_alert(f"EMERGENCY HALT: {reason}", "critical")
            
            # Additional actions could be taken here, such as:
            # - Close all open positions
            # - Notify administrators
            # - Log detailed state for post-mortem
    
    def _add_alert(self, message: str, level: str = "info"):
        """Add a risk alert."""
        alert = {
            "message": message,
            "level": level,
            "timestamp": datetime.utcnow().isoformat()
        }
        self.active_alerts.append(alert)
        
        # Log based on level
        if level == "critical":
            logger.critical(message)
        elif level == "warning":
            logger.warning(message)
        else:
            logger.info(message)
    
    async def _get_current_vix(self) -> float:
        """Get the current VIX level."""
        # In a real implementation, this would fetch the actual VIX value
        # For this example, we'll return a simulated value
        return 20.0  # Simulated moderate VIX level
    
    async def _calculate_portfolio_correlation(self) -> float:
        """Calculate the correlation risk of the current portfolio."""
        # In a real implementation, this would calculate actual correlations
        # For this example, we'll return a simulated value
        return 0.6  # Simulated moderate correlation
    
    async def _calculate_total_exposure(self) -> float:
        """Calculate the total portfolio exposure."""
        # In a real implementation, this would sum all position values
        # For this example, we'll return a simulated value
        return self.portfolio_exposure
    
    async def calculate_position_size(
        self,
        signal_confidence: float,
        symbol: str,
        strategy_type: str,
        market_conditions: Dict[str, Any]
    ) -> float:
        """Calculate adaptive position size based on multiple risk factors."""
        try:
            # Start with minimum position size
            min_position_size = self.position_sizing.min_position_size
            
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
            
            # Calculate position size, never below minimum
            position_size = max(min_position_size, min_position_size * total_adjustment)
            
            # Final position size validation
            position_size = await self._validate_position_size(position_size, symbol)
            
            logger.info(f"Calculated position size for {symbol}: ${position_size:.2f} "
                       f"(base: ${min_position_size}, adjustment: {total_adjustment:.2f})")
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return self.position_sizing.min_position_size  # Conservative fallback to minimum
    
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
                return 1.1  # 10% increase in very low volatility
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
                return 2.0  # 200% of minimum position size for very high confidence
            elif confidence >= 0.8:
                return 1.5  # 150% of minimum for high confidence
            elif confidence >= 0.7:
                return 1.25  # 125% of minimum for good confidence
            else:
                return 1.0  # Minimum position size for base confidence
                
        except Exception as e:
            logger.error(f"Error calculating confidence adjustment: {e}")
            return 1.0  # Default to minimum position size
    
    def _calculate_correlation_adjustment(self, correlation_risk: float) -> float:
        """Calculate position size adjustment based on correlation risk."""
        try:
            # Lower position size for higher correlation risk
            if correlation_risk > 0.8:
                return 0.7  # 30% reduction for high correlation
            elif correlation_risk > 0.6:
                return 0.9  # 10% reduction for moderate correlation
            else:
                return 1.0  # No adjustment for low correlation
                
        except Exception as e:
            logger.error(f"Error calculating correlation adjustment: {e}")
            return 0.9  # Conservative default
    
    async def _calculate_correlation_risk(self, symbol: str) -> float:
        """Calculate correlation risk for a specific symbol."""
        # In a real implementation, this would calculate actual correlations
        # For this example, we'll return a simulated value
        return 0.5  # Simulated moderate correlation risk
    
    async def _calculate_exposure_adjustment(self) -> float:
        """Calculate position size adjustment based on current portfolio exposure."""
        try:
            # Get current exposure
            current_exposure = await self._calculate_total_exposure()
            
            # Calculate exposure ratio
            exposure_ratio = current_exposure / self.account_size
            
            # Adjust position size based on exposure
            if exposure_ratio > 0.7:
                return 0.5  # 50% reduction for high exposure
            elif exposure_ratio > 0.5:
                return 0.7  # 30% reduction for moderate exposure
            elif exposure_ratio > 0.3:
                return 0.9  # 10% reduction for elevated exposure
            else:
                return 1.0  # No adjustment for low exposure
                
        except Exception as e:
            logger.error(f"Error calculating exposure adjustment: {e}")
            return 0.8  # Conservative default
    
    async def _validate_position_size(self, position_size: float, symbol: str) -> float:
        """Validate and adjust position size against limits."""
        try:
            # Ensure minimum position size
            if position_size < self.position_sizing.min_position_size:
                position_size = self.position_sizing.min_position_size
                logger.info(f"Position size adjusted to minimum: ${position_size}")
            
            # Check maximum position size
            if position_size > self.risk_limits.max_position_size:
                position_size = self.risk_limits.max_position_size
                logger.warning(f"Position size capped at max limit: ${position_size}")
            
            # Check if adding this position would exceed portfolio limits
            current_exposure = await self._calculate_total_exposure()
            max_portfolio_exposure = self.account_size * 0.8  # 80% max exposure
            
            if current_exposure + position_size > max_portfolio_exposure:
                max_allowed = max(0, max_portfolio_exposure - current_exposure)
                
                # If we can't meet minimum position size, don't trade
                if max_allowed < self.position_sizing.min_position_size:
                    logger.warning(f"Insufficient capital for minimum position size")
                    return 0
                
                position_size = min(position_size, max_allowed)
                logger.warning(f"Position size adjusted for portfolio limits: ${position_size}")
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error validating position size: {e}")
            return self.position_sizing.min_position_size  # Default to minimum
    
    def create_take_profit_strategy(self, position_id: int, entry_price: float, position_size: float) -> Dict[str, Any]:
        """Create a tiered take-profit strategy for a position."""
        try:
            strategy = TieredTakeProfitStrategy(position_id, entry_price, position_size)
            self.take_profit_strategies[position_id] = strategy
            
            # Return strategy details
            return {
                "position_id": position_id,
                "entry_price": entry_price,
                "position_size": position_size,
                "tiers": [
                    {"percentage": tier.percentage, "position_percentage": tier.position_percentage}
                    for tier in strategy.tiers
                ]
            }
            
        except Exception as e:
            logger.error(f"Error creating take-profit strategy: {e}")
            return {"error": str(e)}
    
    def check_take_profit(self, position_id: int, current_price: float) -> Dict[str, Any]:
        """Check if any take-profit tiers have been triggered for a position."""
        try:
            strategy = self.take_profit_strategies.get(position_id)
            if not strategy:
                return {"error": "No take-profit strategy found for this position"}
            
            result = strategy.check_take_profit(current_price)
            return result if result else {"action": "hold"}
            
        except Exception as e:
            logger.error(f"Error checking take-profit: {e}")
            return {"error": str(e)}
    
    def adjust_take_profit_for_time_decay(self, 
                                         position_id: int, 
                                         entry_time: datetime,
                                         current_time: datetime) -> Dict[str, Any]:
        """
        Adjust take-profit levels based on time decay for 0DTE options.
        
        As the day progresses, take-profit levels should be adjusted to account
        for accelerating theta decay and reduced time for price movement.
        """
        try:
            # Get position details
            strategy = self.take_profit_strategies.get(position_id)
            if not strategy:
                return {"error": "No take-profit strategy found for this position"}
            
            # Calculate time elapsed since entry (in hours)
            time_elapsed = (current_time - entry_time).total_seconds() / 3600
            
            # Calculate time remaining until market close (assuming 4 PM ET close)
            market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
            if current_time > market_close:
                market_close += timedelta(days=1)  # Next day's close
            
            time_remaining = (market_close - current_time).total_seconds() / 3600
            
            # Base take-profit tiers
            base_tiers = [tier.percentage for tier in strategy.tiers]
            
            # Adjust based on time remaining
            if time_remaining < 1:  # Less than 1 hour to close
                adjusted_tiers = [t * 0.5 for t in base_tiers]  # Reduce targets by 50%
            elif time_remaining < 2:  # Less than 2 hours to close
                adjusted_tiers = [t * 0.7 for t in base_tiers]  # Reduce targets by 30%
            elif time_remaining < 3:  # Less than 3 hours to close
                adjusted_tiers = [t * 0.8 for t in base_tiers]  # Reduce targets by 20%
            else:
                adjusted_tiers = base_tiers  # No adjustment
            
            # Adjust based on time elapsed since entry
            if time_elapsed > 3:  # Position open for more than 3 hours
                adjusted_tiers = [t * 0.9 for t in adjusted_tiers]  # Reduce by additional 10%
            
            # Update strategy tiers
            for i, tier in enumerate(strategy.tiers):
                if not tier.triggered:  # Only adjust untriggered tiers
                    tier.percentage = adjusted_tiers[i]
            
            return {
                "position_id": position_id,
                "original_tiers": base_tiers,
                "adjusted_tiers": adjusted_tiers,
                "time_elapsed": time_elapsed,
                "time_remaining": time_remaining
            }
            
        except Exception as e:
            logger.error(f"Error adjusting take-profit for time decay: {e}")
            return {"error": str(e)}
    
    def calculate_stop_loss(self, entry_price: float, position_size: float, risk_level: str = "normal") -> float:
        """Calculate stop-loss price based on risk level."""
        try:
            # Define risk levels
            risk_levels = {
                "low": 0.05,      # 5% loss
                "normal": 0.10,   # 10% loss
                "high": 0.15      # 15% loss
            }
            
            # Get risk percentage
            risk_pct = risk_levels.get(risk_level, 0.10)
            
            # Calculate stop-loss price for long positions
            stop_loss_price = entry_price * (1 - risk_pct)
            
            # Calculate dollar risk
            dollar_risk = position_size * risk_pct
            
            return {
                "stop_loss_price": stop_loss_price,
                "risk_percentage": risk_pct,
                "dollar_risk": dollar_risk
            }
            
        except Exception as e:
            logger.error(f"Error calculating stop-loss: {e}")
            return {"error": str(e)}
    
    def update_daily_pnl(self, pnl: float):
        """Update the daily P&L tracking."""
        self.daily_pnl = pnl
        
        # Check if we've exceeded the daily loss limit
        if self.daily_pnl <= -self.risk_limits.max_daily_loss:
            self._trigger_emergency_halt("Daily loss limit exceeded")
    
    def update_portfolio_exposure(self, exposure: float):
        """Update the portfolio exposure tracking."""
        self.portfolio_exposure = exposure
    
    def get_risk_metrics(self) -> Dict[str, Any]:
        """Get current risk metrics."""
        return self.current_risk_metrics
    
    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get active risk alerts."""
        return self.active_alerts
    
    def clear_alerts(self):
        """Clear all active alerts."""
        self.active_alerts = []
    
    def reset_daily_stats(self):
        """Reset daily statistics (typically called at market open)."""
        self.daily_pnl = 0.0
        self.daily_stats = {}
        self.emergency_halt_active = False
        logger.info("Daily statistics reset")

