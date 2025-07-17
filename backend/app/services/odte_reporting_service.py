import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.services.reporting_service import ReportingService
from app.models.reporting import Report, ReportType, MarketCondition, SignalFactor
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalStatus
from app.models.trade import Trade
from app.models.position import Position
from app.models.market_data import MarketData
from app.models.user import User

logger = logging.getLogger(__name__)

class ODTEReportingService(ReportingService):
    """Reporting service for 0DTE system."""
    
    async def _generate_report_data(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate report data for 0DTE system."""
        return {
            "report_date": date.strftime("%Y-%m-%d"),
            "generation_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            "daily_summary": await self._generate_daily_summary(date, portfolio_id),
            "signal_analysis": await self._generate_signal_analysis(date, portfolio_id),
            "trade_execution": await self._generate_trade_execution(date, portfolio_id),
            "position_management": await self._generate_position_management(date, portfolio_id),
            "risk_analysis": await self._generate_risk_analysis(date, portfolio_id),
            "system_performance": await self._generate_system_performance(date, portfolio_id),
            "next_day_outlook": await self._generate_next_day_outlook(date, portfolio_id)
        }
    
    async def _generate_daily_summary(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate daily summary section for 0DTE system."""
        # Get portfolio data
        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        
        # Get daily performance
        previous_day = date - timedelta(days=1)
        previous_portfolio = self.db.query(Portfolio).filter(
            Portfolio.id == portfolio_id,
            Portfolio.as_of_date == previous_day
        ).first()
        
        start_value = previous_portfolio.total_value if previous_portfolio else portfolio.initial_value
        end_value = portfolio.total_value
        daily_pnl = end_value - start_value
        daily_pnl_pct = (daily_pnl / start_value) * 100 if start_value > 0 else 0
        
        # Get trade counts
        trades = self.db.query(Trade).filter(
            Trade.portfolio_id == portfolio_id,
            Trade.execution_time >= datetime.combine(date, datetime.min.time()),
            Trade.execution_time < datetime.combine(date + timedelta(days=1), datetime.min.time())
        ).all()
        
        entry_trades = [t for t in trades if t.trade_type == "entry"]
        exit_trades = [t for t in trades if t.trade_type == "exit"]
        
        # Get signal counts
        signals = self.db.query(Signal).filter(
            Signal.generation_time >= datetime.combine(date, datetime.min.time()),
            Signal.generation_time < datetime.combine(date + timedelta(days=1), datetime.min.time())
        ).all()
        
        # Market context
        market_data = self.db.query(MarketData).filter(
            MarketData.symbol == "SPY",
            MarketData.date == date
        ).first()
        
        vix_data = self.db.query(MarketData).filter(
            MarketData.symbol == "VIX",
            MarketData.date == date
        ).first()
        
        # Get market condition
        market_condition = self.db.query(MarketCondition).filter(
            MarketCondition.date == date
        ).first()
        
        return {
            "date": date.strftime("%Y-%m-%d"),
            "portfolio_value": end_value,
            "daily_pnl": daily_pnl,
            "daily_pnl_pct": daily_pnl_pct,
            "total_trades": len(trades),
            "entry_trades": len(entry_trades),
            "exit_trades": len(exit_trades),
            "signals_generated": len(signals),
            "signals_executed": len([s for s in signals if s.status == SignalStatus.EXECUTED]),
            "market_context": {
                "spy_change_pct": market_data.change_percent if market_data else None,
                "vix_level": vix_data.close if vix_data else None,
                "vix_change_pct": vix_data.change_percent if vix_data else None,
                "market_condition": market_condition.condition_type if market_condition else "Unknown"
            }
        }
    
    async def _generate_signal_analysis(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate signal analysis section for 0DTE system."""
        # Get signals for the day
        signals = self.db.query(Signal).filter(
            Signal.generation_time >= datetime.combine(date, datetime.min.time()),
            Signal.generation_time < datetime.combine(date + timedelta(days=1), datetime.min.time())
        ).all()
        
        # Get signal factors
        signal_ids = [s.id for s in signals]
        signal_factors = []
        
        if signal_ids:
            signal_factors = self.db.query(SignalFactor).filter(
                SignalFactor.signal_id.in_(signal_ids)
            ).all()
        
        # Group signals by source
        signal_by_source = {}
        for signal in signals:
            if signal.source not in signal_by_source:
                signal_by_source[signal.source] = []
            signal_by_source[signal.source].append(signal)
        
        # Calculate source performance
        source_performance = {}
        for source, source_signals in signal_by_source.items():
            executed_signals = [s for s in source_signals if s.status == SignalStatus.EXECUTED]
            winning_signals = [s for s in executed_signals if s.result == "win"]
            
            source_performance[source] = {
                "total_signals": len(source_signals),
                "executed_signals": len(executed_signals),
                "win_rate": len(winning_signals) / len(executed_signals) if executed_signals else 0,
                "avg_confidence": sum(s.confidence for s in source_signals) / len(source_signals) if source_signals else 0
            }
        
        # Group factors by category
        factor_by_category = {}
        for factor in signal_factors:
            if factor.factor_category not in factor_by_category:
                factor_by_category[factor.factor_category] = []
            factor_by_category[factor.factor_category].append(factor)
        
        # Calculate category importance
        category_importance = {}
        for category, factors in factor_by_category.items():
            category_importance[category] = sum(f.factor_weight for f in factors) / len(factors) if factors else 0
        
        # Get detailed signal data
        signal_details = []
        for signal in signals:
            # Get factors for this signal
            factors = [f for f in signal_factors if f.signal_id == signal.id]
            
            signal_details.append({
                "id": signal.id,
                "symbol": signal.symbol,
                "direction": signal.direction,
                "confidence": signal.confidence,
                "status": signal.status,
                "result": signal.result,
                "generation_time": signal.generation_time.strftime("%Y-%m-%d %H:%M:%S"),
                "factors": [
                    {
                        "name": f.factor_name,
                        "value": f.factor_value,
                        "weight": f.factor_weight,
                        "category": f.factor_category,
                        "description": f.factor_description
                    }
                    for f in factors
                ]
            })
        
        return {
            "signal_count": len(signals),
            "executed_count": len([s for s in signals if s.status == SignalStatus.EXECUTED]),
            "win_rate": len([s for s in signals if s.result == "win"]) / len([s for s in signals if s.status == SignalStatus.EXECUTED]) if [s for s in signals if s.status == SignalStatus.EXECUTED] else 0,
            "source_performance": source_performance,
            "category_importance": category_importance,
            "signal_details": signal_details
        }
    
    async def _generate_trade_execution(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate trade execution section for 0DTE system."""
        # Get trades for the day
        trades = self.db.query(Trade).filter(
            Trade.portfolio_id == portfolio_id,
            Trade.execution_time >= datetime.combine(date, datetime.min.time()),
            Trade.execution_time < datetime.combine(date + timedelta(days=1), datetime.min.time())
        ).all()
        
        # Calculate execution metrics
        entry_trades = [t for t in trades if t.trade_type == "entry"]
        exit_trades = [t for t in trades if t.trade_type == "exit"]
        
        # Calculate slippage
        avg_slippage = sum(t.slippage for t in trades if t.slippage is not None) / len([t for t in trades if t.slippage is not None]) if [t for t in trades if t.slippage is not None] else 0
        
        # Calculate execution time
        avg_execution_time = sum((t.execution_time - t.signal_time).total_seconds() for t in trades if t.signal_time is not None) / len([t for t in trades if t.signal_time is not None]) if [t for t in trades if t.signal_time is not None] else 0
        
        # Get trade details
        trade_details = []
        for trade in trades:
            trade_details.append({
                "id": trade.id,
                "symbol": trade.symbol,
                "trade_type": trade.trade_type,
                "direction": trade.direction,
                "price": trade.price,
                "quantity": trade.quantity,
                "value": trade.price * trade.quantity,
                "execution_time": trade.execution_time.strftime("%Y-%m-%d %H:%M:%S"),
                "slippage": trade.slippage,
                "commission": trade.commission
            })
        
        return {
            "total_trades": len(trades),
            "entry_trades": len(entry_trades),
            "exit_trades": len(exit_trades),
            "avg_slippage": avg_slippage,
            "avg_execution_time": avg_execution_time,
            "total_commission": sum(t.commission for t in trades if t.commission is not None),
            "trades": trade_details
        }
    
    async def _generate_position_management(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate position management section for 0DTE system."""
        # Get open positions
        open_positions = self.db.query(Position).filter(
            Position.portfolio_id == portfolio_id,
            Position.is_open == True
        ).all()
        
        # Get positions closed today
        closed_positions = self.db.query(Position).filter(
            Position.portfolio_id == portfolio_id,
            Position.is_open == False,
            Position.exit_time >= datetime.combine(date, datetime.min.time()),
            Position.exit_time < datetime.combine(date + timedelta(days=1), datetime.min.time())
        ).all()
        
        # Calculate position metrics
        avg_holding_time = sum((p.exit_time - p.entry_time).total_seconds() / 3600 for p in closed_positions) / len(closed_positions) if closed_positions else 0
        
        # Get open position details
        open_position_details = []
        for position in open_positions:
            # Get current price
            market_data = self.db.query(MarketData).filter(
                MarketData.symbol == position.symbol,
                MarketData.date == date
            ).first()
            
            current_price = market_data.close if market_data else position.entry_price
            
            # Calculate unrealized P&L
            unrealized_pnl = (current_price - position.entry_price) * position.quantity * (1 if position.direction == "long" else -1)
            unrealized_pnl_pct = (unrealized_pnl / (position.entry_price * position.quantity)) * 100 if position.entry_price * position.quantity != 0 else 0
            
            open_position_details.append({
                "id": position.id,
                "symbol": position.symbol,
                "direction": position.direction,
                "entry_price": position.entry_price,
                "current_price": current_price,
                "quantity": position.quantity,
                "entry_date": position.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": unrealized_pnl_pct
            })
        
        # Get closed position details
        closed_position_details = []
        for position in closed_positions:
            # Calculate realized P&L
            realized_pnl = position.exit_price * position.quantity - position.entry_price * position.quantity
            if position.direction == "short":
                realized_pnl = -realized_pnl
            
            realized_pnl_pct = (realized_pnl / (position.entry_price * position.quantity)) * 100 if position.entry_price * position.quantity != 0 else 0
            
            closed_position_details.append({
                "id": position.id,
                "symbol": position.symbol,
                "direction": position.direction,
                "entry_price": position.entry_price,
                "exit_price": position.exit_price,
                "quantity": position.quantity,
                "entry_date": position.entry_time.strftime("%Y-%m-%d %H:%M:%S"),
                "exit_date": position.exit_time.strftime("%Y-%m-%d %H:%M:%S"),
                "holding_time_hours": (position.exit_time - position.entry_time).total_seconds() / 3600,
                "realized_pnl": realized_pnl,
                "realized_pnl_pct": realized_pnl_pct
            })
        
        return {
            "open_position_count": len(open_positions),
            "closed_position_count": len(closed_positions),
            "avg_holding_time_hours": avg_holding_time,
            "total_realized_pnl": sum(p.exit_price * p.quantity - p.entry_price * p.quantity for p in closed_positions),
            "open_positions": open_position_details,
            "closed_positions": closed_position_details
        }
    
    async def _generate_risk_analysis(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate risk analysis section for 0DTE system."""
        # Get portfolio
        portfolio = self.db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
        
        # Get open positions
        open_positions = self.db.query(Position).filter(
            Position.portfolio_id == portfolio_id,
            Position.is_open == True
        ).all()
        
        # Get market data
        market_data = self.db.query(MarketData).filter(
            MarketData.symbol == "SPY",
            MarketData.date == date
        ).first()
        
        vix_data = self.db.query(MarketData).filter(
            MarketData.symbol == "VIX",
            MarketData.date == date
        ).first()
        
        # Calculate portfolio beta
        portfolio_beta = 1.0  # Default to market beta
        
        # Calculate value at risk (VaR)
        # Simple VaR calculation: portfolio value * volatility * sqrt(time) * confidence factor
        portfolio_value = portfolio.total_value
        volatility = vix_data.close / 100 if vix_data else 0.2  # Convert VIX to decimal or use default
        confidence_factor = 1.65  # 95% confidence level
        value_at_risk = portfolio_value * volatility * confidence_factor
        
        # Calculate position concentration
        position_values = {}
        total_position_value = 0
        
        for position in open_positions:
            # Get current price
            position_market_data = self.db.query(MarketData).filter(
                MarketData.symbol == position.symbol,
                MarketData.date == date
            ).first()
            
            current_price = position_market_data.close if position_market_data else position.entry_price
            position_value = current_price * position.quantity
            
            if position.symbol not in position_values:
                position_values[position.symbol] = 0
            
            position_values[position.symbol] += position_value
            total_position_value += position_value
        
        # Calculate concentration percentages
        concentration = {}
        for symbol, value in position_values.items():
            concentration[symbol] = (value / total_position_value) * 100 if total_position_value > 0 else 0
        
        # Calculate Greeks (simplified)
        total_delta = sum(p.delta for p in open_positions if p.delta is not None)
        total_gamma = sum(p.gamma for p in open_positions if p.gamma is not None)
        total_theta = sum(p.theta for p in open_positions if p.theta is not None)
        total_vega = sum(p.vega for p in open_positions if p.vega is not None)
        
        return {
            "portfolio_beta": portfolio_beta,
            "value_at_risk": value_at_risk,
            "concentration": concentration,
            "greeks": {
                "delta": total_delta,
                "gamma": total_gamma,
                "theta": total_theta,
                "vega": total_vega
            },
            "vix_level": vix_data.close if vix_data else None
        }
    
    async def _generate_system_performance(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate system performance section for 0DTE system."""
        # Get signals for the last 30 days
        start_date = date - timedelta(days=30)
        signals = self.db.query(Signal).filter(
            Signal.generation_time >= datetime.combine(start_date, datetime.min.time()),
            Signal.generation_time < datetime.combine(date + timedelta(days=1), datetime.min.time())
        ).all()
        
        # Calculate signal accuracy
        executed_signals = [s for s in signals if s.status == SignalStatus.EXECUTED]
        winning_signals = [s for s in executed_signals if s.result == "win"]
        
        signal_accuracy = (len(winning_signals) / len(executed_signals)) * 100 if executed_signals else 0
        
        # Calculate execution efficiency
        execution_efficiency = (len(executed_signals) / len(signals)) * 100 if signals else 0
        
        # Calculate system uptime
        # This would typically come from a system monitoring service
        system_uptime = 99.9  # Placeholder
        
        # Calculate average response time
        # This would typically come from a system monitoring service
        avg_response_time = 0.5  # Placeholder in seconds
        
        return {
            "signal_accuracy": signal_accuracy,
            "execution_efficiency": execution_efficiency,
            "system_uptime": system_uptime,
            "avg_response_time": avg_response_time,
            "signal_count_30d": len(signals),
            "win_rate_30d": (len(winning_signals) / len(executed_signals)) * 100 if executed_signals else 0
        }
    
    async def _generate_next_day_outlook(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate next day outlook section for 0DTE system."""
        # Get market data
        market_data = self.db.query(MarketData).filter(
            MarketData.symbol == "SPY",
            MarketData.date == date
        ).first()
        
        vix_data = self.db.query(MarketData).filter(
            MarketData.symbol == "VIX",
            MarketData.date == date
        ).first()
        
        # Get market condition
        market_condition = self.db.query(MarketCondition).filter(
            MarketCondition.date == date
        ).first()
        
        # Determine next trading day
        next_day = date + timedelta(days=1)
        while next_day.weekday() >= 5:  # Skip weekends
            next_day += timedelta(days=1)
        
        # Check if next day is a 0DTE day (Monday, Wednesday, Friday)
        is_0dte_day = next_day.weekday() in [0, 2, 4]  # Monday, Wednesday, Friday
        
        # Determine market outlook
        market_outlook = "Neutral"
        if market_data and market_data.change_percent > 1.0:
            market_outlook = "Bullish"
        elif market_data and market_data.change_percent < -1.0:
            market_outlook = "Bearish"
        
        # Determine expected volatility
        expected_volatility = "Normal"
        if vix_data:
            if vix_data.close > 25:
                expected_volatility = "High"
            elif vix_data.close < 15:
                expected_volatility = "Low"
        
        # Get expiring options
        # This would typically come from a separate options data service
        expiring_options = []
        
        return {
            "next_trading_day": next_day.strftime("%Y-%m-%d"),
            "is_0dte_day": is_0dte_day,
            "market_outlook": market_outlook,
            "expected_volatility": expected_volatility,
            "expiring_options": expiring_options
        }

