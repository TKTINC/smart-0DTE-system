"""
Advanced Reporting Service for Smart-0DTE-System

This service provides comprehensive reporting capabilities including:
- Performance analytics and metrics
- Risk analysis and drawdown calculations
- Strategy performance comparisons
- Time-based performance aggregations
- Export capabilities for various formats
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
import json

from app.services.tax_service import TaxService, TaxSummary

logger = logging.getLogger(__name__)


class ReportPeriod(Enum):
    """Report period types."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"
    CUSTOM = "custom"


class PerformanceMetric(Enum):
    """Performance metric types."""
    TOTAL_RETURN = "total_return"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    WIN_RATE = "win_rate"
    PROFIT_FACTOR = "profit_factor"
    AVERAGE_WIN = "average_win"
    AVERAGE_LOSS = "average_loss"
    VOLATILITY = "volatility"


@dataclass
class TradeRecord:
    """Individual trade record for analysis."""
    trade_id: str
    symbol: str
    strategy: str
    entry_time: datetime
    exit_time: Optional[datetime]
    entry_price: float
    exit_price: Optional[float]
    quantity: int
    trade_type: str  # 'long', 'short', 'call', 'put'
    pnl: float
    commission: float
    is_winner: bool
    holding_period: Optional[timedelta]
    market_conditions: Dict[str, Any]


@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics."""
    period_start: datetime
    period_end: datetime
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    gross_profit: float
    gross_loss: float
    profit_factor: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    max_drawdown: float
    max_drawdown_duration: timedelta
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    volatility: float
    total_return: float
    annualized_return: float
    risk_adjusted_return: float


@dataclass
class StrategyPerformance:
    """Strategy-specific performance analysis."""
    strategy_name: str
    total_trades: int
    win_rate: float
    total_pnl: float
    average_pnl_per_trade: float
    best_trade: float
    worst_trade: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    sharpe_ratio: float
    symbols_traded: List[str]
    market_conditions_performance: Dict[str, float]


@dataclass
class RiskMetrics:
    """Risk analysis metrics."""
    var_95: float  # Value at Risk (95% confidence)
    var_99: float  # Value at Risk (99% confidence)
    expected_shortfall: float
    maximum_drawdown: float
    drawdown_duration: timedelta
    beta_spy: float
    correlation_spy: float
    correlation_vix: float
    position_concentration: Dict[str, float]
    leverage_ratio: float
    risk_adjusted_return: float


@dataclass
class MarketRegimeAnalysis:
    """Market regime performance analysis."""
    low_volatility_performance: float
    high_volatility_performance: float
    trending_market_performance: float
    sideways_market_performance: float
    correlation_breakdown_performance: float
    vix_regime_performance: Dict[str, float]


@dataclass
class ComprehensiveReport:
    """Complete performance report."""
    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    performance_metrics: PerformanceMetrics
    strategy_performance: List[StrategyPerformance]
    risk_metrics: RiskMetrics
    market_regime_analysis: MarketRegimeAnalysis
    tax_summary: TaxSummary
    recommendations: List[str]
    charts_data: Dict[str, Any]


class ReportingService:
    """Advanced reporting service for trading performance analysis."""
    
    def __init__(self):
        self.tax_service = TaxService()
        self.trade_records: List[TradeRecord] = []
        self.portfolio_values: List[Dict] = []  # Time series of portfolio values
        
    async def add_trade_record(self, trade: TradeRecord) -> None:
        """Add a trade record for analysis."""
        self.trade_records.append(trade)
        
        # Process tax implications
        if trade.exit_time:  # Only for closed trades
            await self.tax_service.process_trade(
                symbol=trade.symbol,
                trade_date=trade.exit_time,
                quantity=trade.quantity,
                price=trade.exit_price,
                trade_type='sell'
            )
        
        logger.info(f"Added trade record: {trade.trade_id}")
    
    async def generate_performance_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> PerformanceMetrics:
        """Generate comprehensive performance metrics for the period."""
        period_trades = [
            trade for trade in self.trade_records
            if trade.exit_time and start_date <= trade.exit_time <= end_date
        ]
        
        if not period_trades:
            return self._empty_performance_metrics(start_date, end_date)
        
        # Basic trade statistics
        total_trades = len(period_trades)
        winning_trades = sum(1 for trade in period_trades if trade.is_winner)
        losing_trades = total_trades - winning_trades
        win_rate = winning_trades / total_trades if total_trades > 0 else 0
        
        # P&L calculations
        total_pnl = sum(trade.pnl for trade in period_trades)
        gross_profit = sum(trade.pnl for trade in period_trades if trade.pnl > 0)
        gross_loss = sum(trade.pnl for trade in period_trades if trade.pnl < 0)
        
        # Profit factor
        profit_factor = abs(gross_profit / gross_loss) if gross_loss != 0 else float('inf')
        
        # Average win/loss
        winning_pnls = [trade.pnl for trade in period_trades if trade.is_winner]
        losing_pnls = [trade.pnl for trade in period_trades if not trade.is_winner]
        
        average_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
        average_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0
        
        # Largest win/loss
        largest_win = max(winning_pnls) if winning_pnls else 0
        largest_loss = min(losing_pnls) if losing_pnls else 0
        
        # Risk metrics
        max_drawdown, max_dd_duration = await self._calculate_max_drawdown(start_date, end_date)
        sharpe_ratio = await self._calculate_sharpe_ratio(period_trades)
        sortino_ratio = await self._calculate_sortino_ratio(period_trades)
        volatility = await self._calculate_volatility(period_trades)
        
        # Return calculations
        total_return = await self._calculate_total_return(start_date, end_date)
        annualized_return = await self._calculate_annualized_return(total_return, start_date, end_date)
        
        # Calmar ratio
        calmar_ratio = annualized_return / abs(max_drawdown) if max_drawdown != 0 else 0
        
        # Risk-adjusted return
        risk_adjusted_return = total_return / volatility if volatility != 0 else 0
        
        return PerformanceMetrics(
            period_start=start_date,
            period_end=end_date,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            profit_factor=profit_factor,
            average_win=average_win,
            average_loss=average_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_dd_duration,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            calmar_ratio=calmar_ratio,
            volatility=volatility,
            total_return=total_return,
            annualized_return=annualized_return,
            risk_adjusted_return=risk_adjusted_return
        )
    
    async def analyze_strategy_performance(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[StrategyPerformance]:
        """Analyze performance by trading strategy."""
        period_trades = [
            trade for trade in self.trade_records
            if trade.exit_time and start_date <= trade.exit_time <= end_date
        ]
        
        # Group trades by strategy
        strategy_trades = {}
        for trade in period_trades:
            if trade.strategy not in strategy_trades:
                strategy_trades[trade.strategy] = []
            strategy_trades[trade.strategy].append(trade)
        
        strategy_performances = []
        
        for strategy_name, trades in strategy_trades.items():
            total_trades = len(trades)
            winning_trades = sum(1 for trade in trades if trade.is_winner)
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            
            total_pnl = sum(trade.pnl for trade in trades)
            average_pnl = total_pnl / total_trades if total_trades > 0 else 0
            
            best_trade = max(trade.pnl for trade in trades) if trades else 0
            worst_trade = min(trade.pnl for trade in trades) if trades else 0
            
            # Consecutive wins/losses
            max_consecutive_wins = await self._calculate_max_consecutive(trades, True)
            max_consecutive_losses = await self._calculate_max_consecutive(trades, False)
            
            # Sharpe ratio for strategy
            strategy_sharpe = await self._calculate_sharpe_ratio(trades)
            
            # Symbols traded
            symbols_traded = list(set(trade.symbol for trade in trades))
            
            # Market conditions performance
            market_conditions_performance = await self._analyze_market_conditions_performance(trades)
            
            strategy_performances.append(StrategyPerformance(
                strategy_name=strategy_name,
                total_trades=total_trades,
                win_rate=win_rate,
                total_pnl=total_pnl,
                average_pnl_per_trade=average_pnl,
                best_trade=best_trade,
                worst_trade=worst_trade,
                max_consecutive_wins=max_consecutive_wins,
                max_consecutive_losses=max_consecutive_losses,
                sharpe_ratio=strategy_sharpe,
                symbols_traded=symbols_traded,
                market_conditions_performance=market_conditions_performance
            ))
        
        return strategy_performances
    
    async def calculate_risk_metrics(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> RiskMetrics:
        """Calculate comprehensive risk metrics."""
        period_trades = [
            trade for trade in self.trade_records
            if trade.exit_time and start_date <= trade.exit_time <= end_date
        ]
        
        if not period_trades:
            return self._empty_risk_metrics()
        
        # Calculate daily returns
        daily_returns = await self._calculate_daily_returns(start_date, end_date)
        
        # Value at Risk calculations
        var_95 = await self._calculate_var(daily_returns, 0.95)
        var_99 = await self._calculate_var(daily_returns, 0.99)
        expected_shortfall = await self._calculate_expected_shortfall(daily_returns, 0.95)
        
        # Drawdown metrics
        max_drawdown, drawdown_duration = await self._calculate_max_drawdown(start_date, end_date)
        
        # Market correlations
        beta_spy = await self._calculate_beta_spy(daily_returns)
        correlation_spy = await self._calculate_correlation_spy(daily_returns)
        correlation_vix = await self._calculate_correlation_vix(daily_returns)
        
        # Position concentration
        position_concentration = await self._calculate_position_concentration(period_trades)
        
        # Leverage ratio
        leverage_ratio = await self._calculate_leverage_ratio(start_date, end_date)
        
        # Risk-adjusted return
        total_return = await self._calculate_total_return(start_date, end_date)
        volatility = await self._calculate_volatility(period_trades)
        risk_adjusted_return = total_return / volatility if volatility != 0 else 0
        
        return RiskMetrics(
            var_95=var_95,
            var_99=var_99,
            expected_shortfall=expected_shortfall,
            maximum_drawdown=max_drawdown,
            drawdown_duration=drawdown_duration,
            beta_spy=beta_spy,
            correlation_spy=correlation_spy,
            correlation_vix=correlation_vix,
            position_concentration=position_concentration,
            leverage_ratio=leverage_ratio,
            risk_adjusted_return=risk_adjusted_return
        )
    
    async def analyze_market_regimes(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> MarketRegimeAnalysis:
        """Analyze performance across different market regimes."""
        period_trades = [
            trade for trade in self.trade_records
            if trade.exit_time and start_date <= trade.exit_time <= end_date
        ]
        
        # Categorize trades by market conditions
        low_vol_trades = [t for t in period_trades if t.market_conditions.get('vix_level', 20) < 20]
        high_vol_trades = [t for t in period_trades if t.market_conditions.get('vix_level', 20) >= 20]
        
        trending_trades = [t for t in period_trades if t.market_conditions.get('market_trend') == 'trending']
        sideways_trades = [t for t in period_trades if t.market_conditions.get('market_trend') == 'sideways']
        
        correlation_breakdown_trades = [
            t for t in period_trades 
            if t.market_conditions.get('correlation_breakdown', False)
        ]
        
        # Calculate performance for each regime
        low_vol_performance = sum(t.pnl for t in low_vol_trades) if low_vol_trades else 0
        high_vol_performance = sum(t.pnl for t in high_vol_trades) if high_vol_trades else 0
        trending_performance = sum(t.pnl for t in trending_trades) if trending_trades else 0
        sideways_performance = sum(t.pnl for t in sideways_trades) if sideways_trades else 0
        correlation_breakdown_performance = sum(t.pnl for t in correlation_breakdown_trades) if correlation_breakdown_trades else 0
        
        # VIX regime performance
        vix_regime_performance = {
            "low_vix": sum(t.pnl for t in period_trades if t.market_conditions.get('vix_level', 20) < 15),
            "medium_vix": sum(t.pnl for t in period_trades if 15 <= t.market_conditions.get('vix_level', 20) < 25),
            "high_vix": sum(t.pnl for t in period_trades if t.market_conditions.get('vix_level', 20) >= 25)
        }
        
        return MarketRegimeAnalysis(
            low_volatility_performance=low_vol_performance,
            high_volatility_performance=high_vol_performance,
            trending_market_performance=trending_performance,
            sideways_market_performance=sideways_performance,
            correlation_breakdown_performance=correlation_breakdown_performance,
            vix_regime_performance=vix_regime_performance
        )
    
    async def generate_comprehensive_report(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> ComprehensiveReport:
        """Generate a complete performance report."""
        report_id = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Generate all components
        performance_metrics = await self.generate_performance_metrics(start_date, end_date)
        strategy_performance = await self.analyze_strategy_performance(start_date, end_date)
        risk_metrics = await self.calculate_risk_metrics(start_date, end_date)
        market_regime_analysis = await self.analyze_market_regimes(start_date, end_date)
        tax_summary = await self.tax_service.generate_tax_summary(start_date, end_date)
        
        # Generate recommendations
        recommendations = await self._generate_recommendations(
            performance_metrics, risk_metrics, market_regime_analysis, tax_summary
        )
        
        # Generate charts data
        charts_data = await self._generate_charts_data(start_date, end_date)
        
        return ComprehensiveReport(
            report_id=report_id,
            generated_at=datetime.now(),
            period_start=start_date,
            period_end=end_date,
            performance_metrics=performance_metrics,
            strategy_performance=strategy_performance,
            risk_metrics=risk_metrics,
            market_regime_analysis=market_regime_analysis,
            tax_summary=tax_summary,
            recommendations=recommendations,
            charts_data=charts_data
        )
    
    # Helper methods (simplified implementations)
    
    def _empty_performance_metrics(self, start_date: datetime, end_date: datetime) -> PerformanceMetrics:
        """Return empty performance metrics."""
        return PerformanceMetrics(
            period_start=start_date,
            period_end=end_date,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            total_pnl=0.0,
            gross_profit=0.0,
            gross_loss=0.0,
            profit_factor=0.0,
            average_win=0.0,
            average_loss=0.0,
            largest_win=0.0,
            largest_loss=0.0,
            max_drawdown=0.0,
            max_drawdown_duration=timedelta(),
            sharpe_ratio=0.0,
            sortino_ratio=0.0,
            calmar_ratio=0.0,
            volatility=0.0,
            total_return=0.0,
            annualized_return=0.0,
            risk_adjusted_return=0.0
        )
    
    def _empty_risk_metrics(self) -> RiskMetrics:
        """Return empty risk metrics."""
        return RiskMetrics(
            var_95=0.0,
            var_99=0.0,
            expected_shortfall=0.0,
            maximum_drawdown=0.0,
            drawdown_duration=timedelta(),
            beta_spy=0.0,
            correlation_spy=0.0,
            correlation_vix=0.0,
            position_concentration={},
            leverage_ratio=0.0,
            risk_adjusted_return=0.0
        )
    
    async def _calculate_max_drawdown(self, start_date: datetime, end_date: datetime) -> tuple:
        """Calculate maximum drawdown and duration."""
        # Simplified implementation
        return -0.05, timedelta(days=3)  # -5% max drawdown, 3 days duration
    
    async def _calculate_sharpe_ratio(self, trades: List[TradeRecord]) -> float:
        """Calculate Sharpe ratio."""
        if not trades:
            return 0.0
        
        returns = [trade.pnl for trade in trades]
        avg_return = sum(returns) / len(returns)
        
        if len(returns) < 2:
            return 0.0
        
        variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = variance ** 0.5
        
        return (avg_return / std_dev) if std_dev != 0 else 0.0
    
    async def _calculate_sortino_ratio(self, trades: List[TradeRecord]) -> float:
        """Calculate Sortino ratio."""
        # Simplified implementation
        return await self._calculate_sharpe_ratio(trades) * 1.2
    
    async def _calculate_volatility(self, trades: List[TradeRecord]) -> float:
        """Calculate volatility."""
        if not trades:
            return 0.0
        
        returns = [trade.pnl for trade in trades]
        avg_return = sum(returns) / len(returns)
        
        if len(returns) < 2:
            return 0.0
        
        variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
        return variance ** 0.5
    
    async def _calculate_total_return(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate total return for the period."""
        # Simplified implementation
        period_trades = [
            trade for trade in self.trade_records
            if trade.exit_time and start_date <= trade.exit_time <= end_date
        ]
        return sum(trade.pnl for trade in period_trades)
    
    async def _calculate_annualized_return(self, total_return: float, start_date: datetime, end_date: datetime) -> float:
        """Calculate annualized return."""
        days = (end_date - start_date).days
        if days == 0:
            return 0.0
        
        years = days / 365.25
        return total_return / years if years > 0 else 0.0
    
    async def _calculate_max_consecutive(self, trades: List[TradeRecord], winners: bool) -> int:
        """Calculate maximum consecutive wins or losses."""
        if not trades:
            return 0
        
        max_consecutive = 0
        current_consecutive = 0
        
        for trade in sorted(trades, key=lambda x: x.exit_time):
            if trade.is_winner == winners:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0
        
        return max_consecutive
    
    async def _analyze_market_conditions_performance(self, trades: List[TradeRecord]) -> Dict[str, float]:
        """Analyze performance under different market conditions."""
        conditions_performance = {}
        
        # Group by market conditions
        for trade in trades:
            for condition, value in trade.market_conditions.items():
                if condition not in conditions_performance:
                    conditions_performance[condition] = []
                conditions_performance[condition].append(trade.pnl)
        
        # Calculate average performance for each condition
        return {
            condition: sum(pnls) / len(pnls) if pnls else 0
            for condition, pnls in conditions_performance.items()
        }
    
    async def _calculate_daily_returns(self, start_date: datetime, end_date: datetime) -> List[float]:
        """Calculate daily returns."""
        # Simplified implementation
        return [0.01, -0.005, 0.02, -0.01, 0.015]  # Mock daily returns
    
    async def _calculate_var(self, returns: List[float], confidence: float) -> float:
        """Calculate Value at Risk."""
        if not returns:
            return 0.0
        
        sorted_returns = sorted(returns)
        index = int((1 - confidence) * len(sorted_returns))
        return sorted_returns[index] if index < len(sorted_returns) else 0.0
    
    async def _calculate_expected_shortfall(self, returns: List[float], confidence: float) -> float:
        """Calculate Expected Shortfall (Conditional VaR)."""
        var = await self._calculate_var(returns, confidence)
        tail_returns = [r for r in returns if r <= var]
        return sum(tail_returns) / len(tail_returns) if tail_returns else 0.0
    
    async def _calculate_beta_spy(self, returns: List[float]) -> float:
        """Calculate beta relative to SPY."""
        # Simplified implementation
        return 0.85  # Mock beta
    
    async def _calculate_correlation_spy(self, returns: List[float]) -> float:
        """Calculate correlation with SPY."""
        # Simplified implementation
        return 0.72  # Mock correlation
    
    async def _calculate_correlation_vix(self, returns: List[float]) -> float:
        """Calculate correlation with VIX."""
        # Simplified implementation
        return -0.45  # Mock negative correlation with VIX
    
    async def _calculate_position_concentration(self, trades: List[TradeRecord]) -> Dict[str, float]:
        """Calculate position concentration by symbol."""
        symbol_exposure = {}
        total_exposure = 0
        
        for trade in trades:
            exposure = abs(trade.quantity * trade.entry_price)
            symbol_exposure[trade.symbol] = symbol_exposure.get(trade.symbol, 0) + exposure
            total_exposure += exposure
        
        return {
            symbol: exposure / total_exposure if total_exposure > 0 else 0
            for symbol, exposure in symbol_exposure.items()
        }
    
    async def _calculate_leverage_ratio(self, start_date: datetime, end_date: datetime) -> float:
        """Calculate average leverage ratio."""
        # Simplified implementation
        return 1.5  # Mock leverage ratio
    
    async def _generate_recommendations(
        self,
        performance: PerformanceMetrics,
        risk: RiskMetrics,
        market_regime: MarketRegimeAnalysis,
        tax_summary: TaxSummary
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        if performance.win_rate < 0.6:
            recommendations.append("Consider tightening entry criteria to improve win rate")
        
        if risk.maximum_drawdown > 0.1:
            recommendations.append("Implement stricter position sizing to reduce maximum drawdown")
        
        if market_regime.high_volatility_performance < market_regime.low_volatility_performance:
            recommendations.append("Adjust strategy allocation during high volatility periods")
        
        if tax_summary.short_term_gains > tax_summary.long_term_gains * 2:
            recommendations.append("Consider holding positions longer for better tax efficiency")
        
        recommendations.extend(tax_summary.recommendations)
        
        return recommendations
    
    async def _generate_charts_data(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate data for charts and visualizations."""
        return {
            "equity_curve": await self._generate_equity_curve_data(start_date, end_date),
            "drawdown_chart": await self._generate_drawdown_data(start_date, end_date),
            "monthly_returns": await self._generate_monthly_returns_data(start_date, end_date),
            "strategy_allocation": await self._generate_strategy_allocation_data(start_date, end_date),
            "symbol_performance": await self._generate_symbol_performance_data(start_date, end_date)
        }
    
    async def _generate_equity_curve_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Generate equity curve data."""
        # Simplified implementation
        return [
            {"date": "2024-01-01", "value": 10000},
            {"date": "2024-01-02", "value": 10150},
            {"date": "2024-01-03", "value": 10080},
            {"date": "2024-01-04", "value": 10250}
        ]
    
    async def _generate_drawdown_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Generate drawdown data."""
        return [
            {"date": "2024-01-01", "drawdown": 0.0},
            {"date": "2024-01-02", "drawdown": -0.02},
            {"date": "2024-01-03", "drawdown": -0.05},
            {"date": "2024-01-04", "drawdown": -0.01}
        ]
    
    async def _generate_monthly_returns_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Generate monthly returns data."""
        return [
            {"month": "2024-01", "return": 0.05},
            {"month": "2024-02", "return": -0.02},
            {"month": "2024-03", "return": 0.08}
        ]
    
    async def _generate_strategy_allocation_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Generate strategy allocation data."""
        return [
            {"strategy": "Mean Reversion", "allocation": 0.4},
            {"strategy": "Momentum", "allocation": 0.3},
            {"strategy": "Correlation Breakdown", "allocation": 0.3}
        ]
    
    async def _generate_symbol_performance_data(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Generate symbol performance data."""
        return [
            {"symbol": "SPY", "return": 0.06, "trades": 45},
            {"symbol": "QQQ", "return": 0.04, "trades": 32},
            {"symbol": "IWM", "return": 0.02, "trades": 28},
            {"symbol": "VIX", "return": 0.08, "trades": 15}
        ]

