# Bet Sizing Implementation Strategy for 0DTE and 7DTE Systems

## Executive Summary

This document outlines a comprehensive implementation strategy for configuring the Smart-0DTE-System and Mag7-7DTE-System to operate with specific account sizes ($60,000 for 0DTE and $100,000+ for 7DTE) and minimum bet sizes ($12,000 for 0DTE and $33,000 for 7DTE). The strategy includes detailed code modifications, configuration changes, testing procedures, and deployment plans to ensure successful implementation while maintaining system integrity and risk management capabilities.

## Table of Contents

1. [Implementation Requirements](#implementation-requirements)
2. [System Architecture Modifications](#system-architecture-modifications)
3. [Risk Management Service Updates](#risk-management-service-updates)
4. [Position Sizing Algorithm Enhancements](#position-sizing-algorithm-enhancements)
5. [Take-Profit Strategy Optimization](#take-profit-strategy-optimization)
6. [Testing and Validation Framework](#testing-and-validation-framework)
7. [Deployment Plan](#deployment-plan)
8. [Monitoring and Optimization](#monitoring-and-optimization)

## Implementation Requirements

### Core Requirements

| Requirement | Smart-0DTE-System | Mag7-7DTE-System |
|-------------|-------------------|------------------|
| Account Size | $60,000 | $100,000+ |
| Minimum Bet Size | $12,000 (20% of account) | $33,000 (33% of account) |
| Maximum Bet Size | Up to $24,000 (40% of account) | Up to $66,000 (66% of account) |
| Scaling Mechanism | Signal confidence based | Signal confidence + fundamental factors |
| Take-Profit Strategy | Tiered approach | Dynamic risk-reward based |
| Risk Management | Enhanced stop-loss and circuit breakers | Partial profit taking and correlation monitoring |

### Technical Requirements

1. **Configuration Updates:**
   - Risk parameters in configuration files
   - Position sizing constants
   - Take-profit and stop-loss thresholds

2. **Code Modifications:**
   - Risk management services
   - Position sizing algorithms
   - Trade management functions
   - Monitoring and alert systems

3. **Database Schema Updates:**
   - Risk profile tables
   - Position tracking tables
   - Performance metrics tables

4. **UI Enhancements:**
   - Position sizing controls
   - Risk visualization dashboards
   - Performance tracking displays

## System Architecture Modifications

### Smart-0DTE-System Architecture Updates

The Smart-0DTE-System requires the following architectural modifications:

1. **Risk Management Service:**
   - Update `PositionSizing` class with new base position size
   - Modify `RiskLimits` class with adjusted parameters
   - Enhance `calculate_position_size` method to enforce minimum bet size

2. **Trade Execution Service:**
   - Update order sizing logic to handle larger positions
   - Implement smart order routing for better execution
   - Add liquidity checks for larger positions

3. **Monitoring Service:**
   - Enhance real-time position monitoring
   - Add intraday circuit breakers
   - Implement enhanced alerting for large positions

4. **Database Updates:**
   - Add fields for minimum position size
   - Update risk profile schema
   - Add tracking for scaled positions

### Mag7-7DTE-System Architecture Updates

The Mag7-7DTE-System requires the following architectural modifications:

1. **Risk Management Service:**
   - Update `calculate_position_size` method to enforce minimum bet size
   - Enhance `calculate_stop_loss_take_profit` for larger positions
   - Modify correlation risk calculations for concentrated positions

2. **Signal Generation Service:**
   - Update confidence scoring to support position scaling
   - Enhance fundamental analysis integration
   - Add correlation-aware signal generation

3. **Portfolio Management Service:**
   - Implement partial position management
   - Add dynamic risk-reward calculations
   - Enhance overnight risk monitoring

4. **Database Updates:**
   - Add minimum position size parameters
   - Update risk profile schema
   - Add fields for partial position tracking

## Risk Management Service Updates

### Smart-0DTE-System Risk Management Updates

The following code modifications are required for the Smart-0DTE-System risk management service:

```python
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


class RiskManagementService:
    """
    Comprehensive Risk Management Service
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
```

### Mag7-7DTE-System Risk Management Updates

The following code modifications are required for the Mag7-7DTE-System risk management service:

```python
class RiskManagementService:
    """
    Service for managing risk in the Mag7-7DTE-System.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_position_size(self, 
                               user_id: int, 
                               instrument_id: int, 
                               signal_confidence: float,
                               option_price: float) -> Dict[str, Any]:
        """
        Calculate the recommended position size based on user's risk profile,
        portfolio value, and signal confidence.
        """
        try:
            # Get user's risk profile
            user = self.db.query(User).filter(User.id == user_id).first()
            if not user or not user.risk_profile:
                logger.warning(f"User {user_id} not found or has no risk profile")
                return {
                    "contracts": 0,
                    "max_capital": 0,
                    "risk_per_trade": 0,
                    "error": "User not found or has no risk profile"
                }
            
            # Get user's portfolio
            portfolio = self.db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
            if not portfolio:
                logger.warning(f"Portfolio not found for user {user_id}")
                return {
                    "contracts": 0,
                    "max_capital": 0,
                    "risk_per_trade": 0,
                    "error": "Portfolio not found"
                }
            
            # Get instrument
            instrument = self.db.query(Instrument).filter(Instrument.id == instrument_id).first()
            if not instrument:
                logger.warning(f"Instrument {instrument_id} not found")
                return {
                    "contracts": 0,
                    "max_capital": 0,
                    "risk_per_trade": 0,
                    "error": "Instrument not found"
                }
            
            # Calculate risk per trade based on risk profile
            max_portfolio_risk = user.risk_profile.max_portfolio_risk
            portfolio_value = portfolio.total_value
            
            # Base risk per trade
            risk_per_trade = portfolio_value * (max_portfolio_risk / 100)
            
            # Adjust risk based on signal confidence
            confidence_multiplier = 0.5 + signal_confidence
            adjusted_risk = risk_per_trade * confidence_multiplier
            
            # Calculate max capital to allocate
            max_capital = adjusted_risk
            
            # Enforce minimum position size of $33,000 or 33% of portfolio
            min_position_size = max(33000.0, portfolio_value * 0.33)
            
            # Calculate number of contracts
            contract_value = option_price * 100
            min_contracts = math.ceil(min_position_size / contract_value)
            
            # Apply confidence-based scaling
            if signal_confidence >= 0.9:
                # Very high confidence - up to 200% of minimum
                max_scaling = 2.0
            elif signal_confidence >= 0.8:
                # High confidence - up to 150% of minimum
                max_scaling = 1.5
            elif signal_confidence >= 0.7:
                # Good confidence - up to 125% of minimum
                max_scaling = 1.25
            else:
                # Base confidence - minimum bet size
                max_scaling = 1.0
            
            # Calculate scaled contracts
            scaled_contracts = min(
                int(min_contracts * max_scaling),
                int(max_capital / contract_value)
            )
            
            # Ensure we never go below minimum
            contracts = max(min_contracts, scaled_contracts)
            
            # Check if this exceeds max allocation per stock
            max_stock_allocation = user.risk_profile.max_stock_allocation
            max_stock_capital = portfolio_value * (max_stock_allocation / 100)
            
            # Get current allocation to this stock
            current_positions = self.db.query(Position).filter(
                Position.portfolio_id == portfolio.id,
                Position.instrument_id == instrument_id,
                Position.status == 'ACTIVE'
            ).all()
            
            current_allocation = sum(p.current_value for p in current_positions)
            
            # Adjust if needed
            available_allocation = max_stock_capital - current_allocation
            if available_allocation <= 0:
                logger.warning(f"Maximum allocation reached for instrument {instrument.symbol}")
                return {
                    "contracts": 0,
                    "max_capital": 0,
                    "risk_per_trade": 0,
                    "error": f"Maximum allocation reached for {instrument.symbol}"
                }
            
            # Final position size calculation
            position_value = contracts * contract_value
            
            # If position value exceeds available allocation, adjust
            if position_value > available_allocation:
                contracts = int(available_allocation / contract_value)
                position_value = contracts * contract_value
            
            # Final check to ensure minimum position size
            if position_value < min_position_size and available_allocation >= min_position_size:
                contracts = math.ceil(min_position_size / contract_value)
                position_value = contracts * contract_value
            
            return {
                "contracts": contracts,
                "min_contracts": min_contracts,
                "max_contracts": scaled_contracts,
                "position_value": position_value,
                "min_position_size": min_position_size,
                "max_capital": max_capital,
                "risk_per_trade": adjusted_risk,
                "contract_value": contract_value,
                "portfolio_value": portfolio_value,
                "current_allocation": current_allocation,
                "available_allocation": available_allocation,
                "confidence_multiplier": confidence_multiplier,
                "max_scaling": max_scaling
            }
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return {
                "contracts": 0,
                "max_capital": 0,
                "risk_per_trade": 0,
                "error": str(e)
            }
```

## Position Sizing Algorithm Enhancements

### Smart-0DTE-System Position Sizing Enhancements

The Smart-0DTE-System requires the following enhancements to its position sizing algorithm:

1. **Confidence-Based Scaling:**

```python
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
```

2. **VIX-Based Adjustment:**

```python
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
```

3. **Position Validation:**

```python
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
```

### Mag7-7DTE-System Position Sizing Enhancements

The Mag7-7DTE-System requires the following enhancements to its position sizing algorithm:

1. **Fundamental Factor Integration:**

```python
def calculate_fundamental_adjustment(self, 
                                    instrument_id: int, 
                                    signal_confidence: float) -> float:
    """
    Calculate position size adjustment based on fundamental factors.
    """
    try:
        # Get instrument
        instrument = self.db.query(Instrument).filter(Instrument.id == instrument_id).first()
        if not instrument:
            return 1.0  # Default to no adjustment
        
        # Get fundamental data
        fundamental_data = self.db.query(FundamentalData).filter(
            FundamentalData.instrument_id == instrument_id
        ).order_by(FundamentalData.date.desc()).first()
        
        if not fundamental_data:
            return 1.0  # Default to no adjustment
        
        # Calculate fundamental score (0.0 to 1.0)
        fundamental_score = 0.5  # Default neutral score
        
        # Earnings surprise factor
        if fundamental_data.earnings_surprise_pct > 10:
            fundamental_score += 0.2  # Significant positive surprise
        elif fundamental_data.earnings_surprise_pct > 5:
            fundamental_score += 0.1  # Moderate positive surprise
        elif fundamental_data.earnings_surprise_pct < -10:
            fundamental_score -= 0.2  # Significant negative surprise
        elif fundamental_data.earnings_surprise_pct < -5:
            fundamental_score -= 0.1  # Moderate negative surprise
        
        # Analyst rating factor
        if fundamental_data.analyst_rating_buy > 70:
            fundamental_score += 0.1  # Strong buy consensus
        elif fundamental_data.analyst_rating_sell > 50:
            fundamental_score -= 0.1  # Strong sell consensus
        
        # Valuation factor
        if fundamental_data.pe_ratio < fundamental_data.sector_avg_pe * 0.7:
            fundamental_score += 0.1  # Significantly undervalued
        elif fundamental_data.pe_ratio > fundamental_data.sector_avg_pe * 1.5:
            fundamental_score -= 0.1  # Significantly overvalued
        
        # Clamp score between 0.0 and 1.0
        fundamental_score = max(0.0, min(1.0, fundamental_score))
        
        # Calculate adjustment factor (0.5 to 1.5)
        adjustment_factor = 0.5 + fundamental_score
        
        # Combine with signal confidence
        combined_factor = (adjustment_factor + signal_confidence) / 2
        
        # Scale to desired range (1.0 to 2.0)
        scaling_factor = 1.0 + combined_factor
        
        return scaling_factor
        
    except Exception as e:
        logger.error(f"Error calculating fundamental adjustment: {e}")
        return 1.0  # Default to no adjustment
```

2. **Correlation-Aware Position Sizing:**

```python
def calculate_correlation_adjustment(self, 
                                    instrument_id: int, 
                                    portfolio_id: int) -> float:
    """
    Calculate position size adjustment based on correlation with existing positions.
    """
    try:
        # Get active positions in portfolio
        active_positions = self.db.query(Position).filter(
            Position.portfolio_id == portfolio_id,
            Position.status == 'ACTIVE'
        ).all()
        
        if not active_positions:
            return 1.0  # No existing positions, no correlation
        
        # Get correlation matrix
        correlation_matrix = self.calculate_correlation_matrix()
        if correlation_matrix is None:
            return 0.8  # Conservative default if no correlation data
        
        # Get instrument symbol
        instrument = self.db.query(Instrument).filter(Instrument.id == instrument_id).first()
        if not instrument:
            return 0.8  # Conservative default if instrument not found
        
        # Calculate average correlation with existing positions
        correlations = []
        for position in active_positions:
            position_instrument = self.db.query(Instrument).filter(
                Instrument.id == position.instrument_id
            ).first()
            
            if position_instrument and position_instrument.symbol in correlation_matrix.index:
                if instrument.symbol in correlation_matrix.columns:
                    correlation = correlation_matrix.loc[position_instrument.symbol, instrument.symbol]
                    correlations.append(abs(correlation))
        
        if not correlations:
            return 1.0  # No correlation data found
        
        avg_correlation = sum(correlations) / len(correlations)
        
        # Adjust position size based on correlation
        if avg_correlation > 0.8:
            return 0.5  # High correlation, reduce position size
        elif avg_correlation > 0.6:
            return 0.75  # Moderate correlation, slightly reduce position
        elif avg_correlation < 0.3:
            return 1.2  # Low correlation, increase position size
        else:
            return 1.0  # Normal correlation, no adjustment
        
    except Exception as e:
        logger.error(f"Error calculating correlation adjustment: {e}")
        return 0.8  # Conservative default
```

3. **Dynamic Position Sizing Integration:**

```python
def calculate_position_size(self, 
                           user_id: int, 
                           instrument_id: int, 
                           signal_confidence: float,
                           option_price: float) -> Dict[str, Any]:
    """
    Calculate the recommended position size with enhanced algorithms.
    """
    try:
        # [Existing code for basic position sizing...]
        
        # Get portfolio
        portfolio = self.db.query(Portfolio).filter(Portfolio.user_id == user_id).first()
        
        # Calculate fundamental adjustment
        fundamental_adjustment = self.calculate_fundamental_adjustment(
            instrument_id, signal_confidence
        )
        
        # Calculate correlation adjustment
        correlation_adjustment = self.calculate_correlation_adjustment(
            instrument_id, portfolio.id
        )
        
        # Combine adjustments
        combined_adjustment = fundamental_adjustment * correlation_adjustment
        
        # Apply minimum position size
        min_position_size = max(33000.0, portfolio.total_value * 0.33)
        
        # Calculate contract value
        contract_value = option_price * 100
        
        # Calculate base contracts
        base_contracts = math.ceil(min_position_size / contract_value)
        
        # Apply adjustments to get final contracts
        adjusted_contracts = int(base_contracts * combined_adjustment)
        
        # Ensure minimum is maintained
        final_contracts = max(base_contracts, adjusted_contracts)
        
        # Calculate position value
        position_value = final_contracts * contract_value
        
        # [Remaining validation code...]
        
        return {
            "contracts": final_contracts,
            "base_contracts": base_contracts,
            "position_value": position_value,
            "min_position_size": min_position_size,
            "fundamental_adjustment": fundamental_adjustment,
            "correlation_adjustment": correlation_adjustment,
            "combined_adjustment": combined_adjustment,
            "contract_value": contract_value
        }
        
    except Exception as e:
        logger.error(f"Error calculating position size: {e}")
        return {
            "contracts": 0,
            "error": str(e)
        }
```

## Take-Profit Strategy Optimization

### Smart-0DTE-System Take-Profit Optimization

The Smart-0DTE-System requires the following take-profit strategy optimizations:

1. **Tiered Take-Profit Implementation:**

```python
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
```

2. **Time-Based Take-Profit Adjustments:**

```python
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
        position = self.get_position(position_id)
        if not position:
            return {"error": "Position not found"}
        
        # Calculate time elapsed since entry (in hours)
        time_elapsed = (current_time - entry_time).total_seconds() / 3600
        
        # Calculate time remaining until market close (assuming 4 PM ET close)
        market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
        if current_time > market_close:
            market_close += timedelta(days=1)  # Next day's close
        
        time_remaining = (market_close - current_time).total_seconds() / 3600
        
        # Base take-profit tiers
        base_tiers = [0.05, 0.10, 0.15]  # 5%, 10%, 15%
        
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
```

### Mag7-7DTE-System Take-Profit Optimization

The Mag7-7DTE-System requires the following take-profit strategy optimizations:

1. **Dynamic Risk-Reward Based Take-Profit:**

```python
def calculate_dynamic_take_profit(self, 
                                 position_id: int, 
                                 current_profit_pct: float = 0.0) -> Dict[str, Any]:
    """
    Calculate dynamic take-profit levels based on current profit and risk-reward.
    
    As a position moves into profit, the risk-reward ratio is adjusted to
    allow for greater upside potential while protecting gains.
    """
    try:
        # Get position
        position = self.db.query(Position).filter(Position.id == position_id).first()
        if not position:
            return {"error": "Position not found"}
        
        # Get initial stop-loss
        initial_stop_loss = position.stop_loss_price
        if not initial_stop_loss:
            # Calculate default stop-loss if not set
            initial_stop_loss = position.entry_price * 0.8  # 20% stop-loss
        
        # Calculate initial risk
        initial_risk = abs(position.entry_price - initial_stop_loss)
        
        # Base risk-reward ratios
        if current_profit_pct < 0.15:
            # Initial stage: 1:1.5 risk-reward
            risk_reward_ratio = 1.5
        elif current_profit_pct < 0.30:
            # Intermediate stage: 1:2 risk-reward
            risk_reward_ratio = 2.0
        else:
            # Advanced stage: 1:3 risk-reward
            risk_reward_ratio = 3.0
        
        # Calculate take-profit price
        take_profit_price = position.entry_price + (initial_risk * risk_reward_ratio)
        
        # Calculate trailing stop based on current profit
        if current_profit_pct > 0.30:
            # Lock in 50% of gains
            trailing_stop = position.entry_price + (position.current_price - position.entry_price) * 0.5
        elif current_profit_pct > 0.15:
            # Lock in 25% of gains
            trailing_stop = position.entry_price + (position.current_price - position.entry_price) * 0.25
        else:
            # Use initial stop-loss
            trailing_stop = initial_stop_loss
        
        # Use the higher of initial stop-loss or trailing stop
        adjusted_stop_loss = max(initial_stop_loss, trailing_stop)
        
        return {
            "position_id": position_id,
            "entry_price": position.entry_price,
            "current_price": position.current_price,
            "current_profit_pct": current_profit_pct,
            "initial_stop_loss": initial_stop_loss,
            "adjusted_stop_loss": adjusted_stop_loss,
            "take_profit_price": take_profit_price,
            "risk_reward_ratio": risk_reward_ratio,
            "initial_risk": initial_risk
        }
        
    except Exception as e:
        logger.error(f"Error calculating dynamic take-profit: {e}")
        return {"error": str(e)}
```

2. **Partial Profit Taking Implementation:**

```python
def implement_partial_profit_taking(self, 
                                   position_id: int, 
                                   current_profit_pct: float) -> Dict[str, Any]:
    """
    Implement partial profit taking strategy based on profit thresholds.
    
    Returns the percentage of position to close and updates position tracking.
    """
    try:
        # Get position
        position = self.db.query(Position).filter(Position.id == position_id).first()
        if not position:
            return {"error": "Position not found"}
        
        # Get partial profit taking history
        profit_taking_history = self.db.query(PartialProfitTaking).filter(
            PartialProfitTaking.position_id == position_id
        ).all()
        
        # Calculate total percentage already taken
        total_pct_taken = sum(ppt.percentage_closed for ppt in profit_taking_history)
        
        # Define profit taking thresholds
        thresholds = [
            {"profit_pct": 0.20, "take_pct": 0.25},  # At 20% profit, take 25% off
            {"profit_pct": 0.35, "take_pct": 0.25},  # At 35% profit, take another 25% off
            {"profit_pct": 0.50, "take_pct": 0.25}   # At 50% profit, take another 25% off
        ]
        
        # Check if any threshold is triggered
        for threshold in thresholds:
            # Check if we've hit this profit level and haven't taken this much off yet
            if current_profit_pct >= threshold["profit_pct"] and total_pct_taken < sum(t["take_pct"] for t in thresholds if t["profit_pct"] <= threshold["profit_pct"]):
                # Calculate how much to take off now
                target_total_pct = sum(t["take_pct"] for t in thresholds if t["profit_pct"] <= threshold["profit_pct"])
                pct_to_take_now = target_total_pct - total_pct_taken
                
                # Ensure we don't take more than what's left
                pct_to_take_now = min(pct_to_take_now, 1.0 - total_pct_taken)
                
                if pct_to_take_now > 0:
                    # Record this partial profit taking
                    new_profit_taking = PartialProfitTaking(
                        position_id=position_id,
                        percentage_closed=pct_to_take_now,
                        price=position.current_price,
                        profit_percentage=current_profit_pct,
                        timestamp=datetime.utcnow()
                    )
                    self.db.add(new_profit_taking)
                    self.db.commit()
                    
                    return {
                        "action": "partial_close",
                        "position_id": position_id,
                        "percentage_to_close": pct_to_take_now,
                        "contracts_to_close": int(position.quantity * pct_to_take_now),
                        "profit_percentage": current_profit_pct,
                        "threshold_triggered": threshold["profit_pct"],
                        "total_percentage_closed": total_pct_taken + pct_to_take_now
                    }
        
        return {
            "action": "hold",
            "position_id": position_id,
            "profit_percentage": current_profit_pct,
            "total_percentage_closed": total_pct_taken
        }
        
    except Exception as e:
        logger.error(f"Error implementing partial profit taking: {e}")
        return {"error": str(e)}
```

3. **Time-Decay Adjusted Take-Profit:**

```python
def adjust_take_profit_for_dte(self, 
                              position_id: int) -> Dict[str, Any]:
    """
    Adjust take-profit levels based on days to expiration.
    
    As expiration approaches, take-profit levels are adjusted to account
    for accelerating theta decay and reduced time for price movement.
    """
    try:
        # Get position
        position = self.db.query(Position).filter(Position.id == position_id).first()
        if not position:
            return {"error": "Position not found"}
        
        # Calculate days to expiration
        days_to_expiration = (position.expiration_date - datetime.utcnow().date()).days
        
        # Base profit taking thresholds
        base_thresholds = [
            {"profit_pct": 0.20, "take_pct": 0.25},
            {"profit_pct": 0.35, "take_pct": 0.25},
            {"profit_pct": 0.50, "take_pct": 0.25}
        ]
        
        # Adjust thresholds based on DTE
        adjusted_thresholds = []
        
        for threshold in base_thresholds:
            adjusted_threshold = threshold.copy()
            
            if days_to_expiration <= 1:
                # 1 DTE: Reduce profit targets by 60%
                adjusted_threshold["profit_pct"] = threshold["profit_pct"] * 0.4
            elif days_to_expiration <= 2:
                # 2 DTE: Reduce profit targets by 40%
                adjusted_threshold["profit_pct"] = threshold["profit_pct"] * 0.6
            elif days_to_expiration <= 3:
                # 3 DTE: Reduce profit targets by 25%
                adjusted_threshold["profit_pct"] = threshold["profit_pct"] * 0.75
            elif days_to_expiration <= 5:
                # 4-5 DTE: Reduce profit targets by 10%
                adjusted_threshold["profit_pct"] = threshold["profit_pct"] * 0.9
            
            adjusted_thresholds.append(adjusted_threshold)
        
        return {
            "position_id": position_id,
            "days_to_expiration": days_to_expiration,
            "base_thresholds": base_thresholds,
            "adjusted_thresholds": adjusted_thresholds
        }
        
    except Exception as e:
        logger.error(f"Error adjusting take-profit for DTE: {e}")
        return {"error": str(e)}
```

## Testing and Validation Framework

### Test Cases for Smart-0DTE-System

The following test cases should be implemented to validate the Smart-0DTE-System modifications:

1. **Minimum Bet Size Enforcement:**

```python
async def test_minimum_bet_size_enforcement():
    """Test that the system enforces the minimum bet size of $12,000."""
    # Initialize risk management service with $60,000 account
    risk_service = RiskManagementService(account_size=60000.0)
    
    # Test with various confidence levels
    test_cases = [
        {"confidence": 0.6, "expected_min": 12000.0},
        {"confidence": 0.7, "expected_min": 12000.0},
        {"confidence": 0.8, "expected_min": 12000.0},
        {"confidence": 0.9, "expected_min": 12000.0}
    ]
    
    for tc in test_cases:
        position_size = await risk_service.calculate_position_size(
            signal_confidence=tc["confidence"],
            symbol="SPY",
            strategy_type="LONG_CALL",
            market_conditions={"vix_level": 20.0}
        )
        
        assert position_size >= tc["expected_min"], f"Position size {position_size} is below minimum {tc['expected_min']}"
        print(f"Test passed: Confidence {tc['confidence']} -> Position size ${position_size}")
```

2. **Scaling Based on Signal Confidence:**

```python
async def test_position_scaling_with_confidence():
    """Test that position size scales appropriately with signal confidence."""
    # Initialize risk management service with $60,000 account
    risk_service = RiskManagementService(account_size=60000.0)
    
    # Test with various confidence levels
    test_cases = [
        {"confidence": 0.6, "expected_range": (12000.0, 12000.0)},  # Minimum only
        {"confidence": 0.7, "expected_range": (12000.0, 15000.0)},  # Up to 125%
        {"confidence": 0.8, "expected_range": (15000.0, 18000.0)},  # Up to 150%
        {"confidence": 0.9, "expected_range": (18000.0, 24000.0)}   # Up to 200%
    ]
    
    for tc in test_cases:
        position_size = await risk_service.calculate_position_size(
            signal_confidence=tc["confidence"],
            symbol="SPY",
            strategy_type="LONG_CALL",
            market_conditions={"vix_level": 20.0}
        )
        
        assert tc["expected_range"][0] <= position_size <= tc["expected_range"][1], \
            f"Position size ${position_size} outside expected range {tc['expected_range']}"
        print(f"Test passed: Confidence {tc['confidence']} -> Position size ${position_size}")
```

3. **Take-Profit Strategy Testing:**

```python
def test_tiered_take_profit_strategy():
    """Test the tiered take-profit strategy implementation."""
    # Create a test position
    entry_price = 10.0
    position_size = 12000.0
    position_id = 1
    
    # Create strategy
    strategy = TieredTakeProfitStrategy(position_id, entry_price, position_size)
    
    # Test price points
    test_cases = [
        {"price": 10.3, "expected_action": None},  # 3% profit, no tier triggered
        {"price": 10.5, "expected_action": "partial_close"},  # 5% profit, first tier
        {"price": 10.8, "expected_action": None},  # 8% profit, first tier already triggered
        {"price": 11.0, "expected_action": "partial_close"},  # 10% profit, second tier
        {"price": 11.5, "expected_action": "partial_close"},  # 15% profit, third tier
        {"price": 12.0, "expected_action": None}   # 20% profit, all tiers triggered
    ]
    
    for tc in test_cases:
        result = strategy.check_take_profit(tc["price"])
        
        if tc["expected_action"] is None:
            assert result is None, f"Expected no action at price {tc['price']}, got {result}"
        else:
            assert result is not None and result["action"] == tc["expected_action"], \
                f"Expected {tc['expected_action']} at price {tc['price']}, got {result}"
        
        print(f"Test passed: Price {tc['price']} -> Action {result['action'] if result else None}")
```

### Test Cases for Mag7-7DTE-System

The following test cases should be implemented to validate the Mag7-7DTE-System modifications:

1. **Minimum Bet Size Enforcement:**

```python
def test_minimum_bet_size_enforcement():
    """Test that the system enforces the minimum bet size of $33,000."""
    # Mock database session
    db_session = MockDbSession()
    
    # Initialize risk management service
    risk_service = RiskManagementService(db_session)
    
    # Mock user with $100,000 portfolio
    user = MockUser(id=1, risk_profile=MockRiskProfile(max_portfolio_risk=2.0, max_stock_allocation=20.0))
    portfolio = MockPortfolio(id=1, user_id=1, total_value=100000.0)
    instrument = MockInstrument(id=1, symbol="AAPL")
    
    # Add mocks to session
    db_session.add_mock(user)
    db_session.add_mock(portfolio)
    db_session.add_mock(instrument)
    
    # Test with various option prices and confidence levels
    test_cases = [
        {"option_price": 5.0, "confidence": 0.6, "expected_min_value": 33000.0},
        {"option_price": 10.0, "confidence": 0.7, "expected_min_value": 33000.0},
        {"option_price": 15.0, "confidence": 0.8, "expected_min_value": 33000.0},
        {"option_price": 20.0, "confidence": 0.9, "expected_min_value": 33000.0}
    ]
    
    for tc in test_cases:
        result = risk_service.calculate_position_size(
            user_id=1,
            instrument_id=1,
            signal_confidence=tc["confidence"],
            option_price=tc["option_price"]
        )
        
        position_value = result["contracts"] * result["contract_value"]
        
        assert position_value >= tc["expected_min_value"], \
            f"Position value {position_value} is below minimum {tc['expected_min_value']}"
        print(f"Test passed: Option price {tc['option_price']}, Confidence {tc['confidence']} -> Position value ${position_value}")
```

2. **Scaling Based on Signal Confidence:**

```python
def test_position_scaling_with_confidence():
    """Test that position size scales appropriately with signal confidence."""
    # Mock database session
    db_session = MockDbSession()
    
    # Initialize risk management service
    risk_service = RiskManagementService(db_session)
    
    # Mock user with $100,000 portfolio
    user = MockUser(id=1, risk_profile=MockRiskProfile(max_portfolio_risk=2.0, max_stock_allocation=50.0))
    portfolio = MockPortfolio(id=1, user_id=1, total_value=100000.0)
    instrument = MockInstrument(id=1, symbol="AAPL")
    
    # Add mocks to session
    db_session.add_mock(user)
    db_session.add_mock(portfolio)
    db_session.add_mock(instrument)
    
    # Test with fixed option price and various confidence levels
    option_price = 10.0  # $10 per share, $1,000 per contract
    
    test_cases = [
        {"confidence": 0.6, "expected_range": (33000.0, 33000.0)},  # Minimum only
        {"confidence": 0.7, "expected_range": (33000.0, 41250.0)},  # Up to 125%
        {"confidence": 0.8, "expected_range": (41250.0, 49500.0)},  # Up to 150%
        {"confidence": 0.9, "expected_range": (49500.0, 66000.0)}   # Up to 200%
    ]
    
    for tc in test_cases:
        result = risk_service.calculate_position_size(
            user_id=1,
            instrument_id=1,
            signal_confidence=tc["confidence"],
            option_price=option_price
        )
        
        position_value = result["contracts"] * result["contract_value"]
        
        assert tc["expected_range"][0] <= position_value <= tc["expected_range"][1], \
            f"Position value ${position_value} outside expected range {tc['expected_range']}"
        print(f"Test passed: Confidence {tc['confidence']} -> Position value ${position_value}")
```

3. **Partial Profit Taking Testing:**

```python
def test_partial_profit_taking():
    """Test the partial profit taking implementation."""
    # Mock database session
    db_session = MockDbSession()
    
    # Initialize risk management service
    risk_service = RiskManagementService(db_session)
    
    # Mock position
    position = MockPosition(
        id=1,
        portfolio_id=1,
        instrument_id=1,
        entry_price=100.0,
        current_price=100.0,
        quantity=33,  # 33 contracts at $100 per share = $330,000 position
        status="ACTIVE"
    )
    
    # Add mock to session
    db_session.add_mock(position)
    
    # Test with various profit levels
    test_cases = [
        {"profit_pct": 0.10, "expected_action": "hold"},  # 10% profit, no action
        {"profit_pct": 0.20, "expected_action": "partial_close", "expected_pct": 0.25},  # 20% profit, close 25%
        {"profit_pct": 0.30, "expected_action": "hold"},  # 30% profit, no additional action
        {"profit_pct": 0.35, "expected_action": "partial_close", "expected_pct": 0.25},  # 35% profit, close another 25%
        {"profit_pct": 0.50, "expected_action": "partial_close", "expected_pct": 0.25},  # 50% profit, close another 25%
        {"profit_pct": 0.60, "expected_action": "hold"}   # 60% profit, no additional action
    ]
    
    for tc in test_cases:
        # Update current price to reflect profit percentage
        position.current_price = position.entry_price * (1 + tc["profit_pct"])
        
        result = risk_service.implement_partial_profit_taking(
            position_id=1,
            current_profit_pct=tc["profit_pct"]
        )
        
        assert result["action"] == tc["expected_action"], \
            f"Expected {tc['expected_action']} at profit {tc['profit_pct']}, got {result['action']}"
        
        if tc["expected_action"] == "partial_close":
            assert abs(result["percentage_to_close"] - tc["expected_pct"]) < 0.01, \
                f"Expected to close {tc['expected_pct']} at profit {tc['profit_pct']}, got {result['percentage_to_close']}"
        
        print(f"Test passed: Profit {tc['profit_pct']} -> Action {result['action']}")
```

## Deployment Plan

The implementation of the bet sizing requirements should follow a phased deployment approach:

### Phase 1: Configuration Updates (Week 1)

1. **Update Configuration Files:**
   - Update risk parameters in configuration files
   - Set minimum and maximum position sizes
   - Configure take-profit and stop-loss thresholds

2. **Database Schema Updates:**
   - Add fields for minimum position size
   - Update risk profile schema
   - Add tables for partial profit taking

3. **Documentation Updates:**
   - Update system documentation with new parameters
   - Create user guides for new position sizing
   - Document take-profit strategies

### Phase 2: Code Implementation (Weeks 2-3)

1. **Risk Management Service Updates:**
   - Implement minimum bet size enforcement
   - Update position sizing algorithms
   - Implement scaling based on signal confidence

2. **Take-Profit Strategy Implementation:**
   - Implement tiered take-profit for 0DTE
   - Implement partial profit taking for 7DTE
   - Add time-based adjustments

3. **UI Enhancements:**
   - Update position sizing controls
   - Add visualization for take-profit tiers
   - Enhance risk monitoring dashboards

### Phase 3: Testing and Validation (Week 4)

1. **Unit Testing:**
   - Test minimum bet size enforcement
   - Test position scaling algorithms
   - Test take-profit strategies

2. **Integration Testing:**
   - Test end-to-end trade lifecycle
   - Test interaction between components
   - Validate database updates

3. **Paper Trading Validation:**
   - Run paper trading with new parameters
   - Validate performance against benchmarks
   - Identify and fix any issues

### Phase 4: Production Deployment (Week 5)

1. **Staged Rollout:**
   - Deploy to staging environment
   - Validate in production-like conditions
   - Perform final adjustments

2. **Production Deployment:**
   - Deploy to production environment
   - Monitor initial trades closely
   - Be prepared for rollback if needed

3. **Post-Deployment Monitoring:**
   - Monitor position sizes and scaling
   - Track take-profit effectiveness
   - Measure performance against projections

## Monitoring and Optimization

After deployment, the following monitoring and optimization activities should be performed:

1. **Performance Monitoring:**
   - Track win rate with larger positions
   - Monitor drawdown and volatility
   - Compare actual vs. projected returns

2. **Risk Metrics Tracking:**
   - Monitor portfolio concentration
   - Track correlation between positions
   - Measure impact of larger positions on overall risk

3. **Take-Profit Effectiveness:**
   - Analyze partial profit taking results
   - Measure effectiveness of tiered approach
   - Optimize thresholds based on results

4. **Continuous Improvement:**
   - Refine position sizing algorithms
   - Adjust take-profit strategies
   - Optimize risk parameters

5. **Regular Reviews:**
   - Weekly performance reviews
   - Monthly strategy adjustments
   - Quarterly comprehensive evaluation

By following this implementation strategy, the Smart-0DTE-System and Mag7-7DTE-System can be successfully configured to operate with the specified account sizes and minimum bet sizes, while maintaining robust risk management and optimizing profit potential.

