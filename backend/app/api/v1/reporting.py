"""
Reporting API Endpoints for Smart-0DTE-System

This module provides REST API endpoints for:
- Performance analytics and metrics
- Tax calculations and reporting
- Risk analysis and reporting
- Strategy performance analysis
- Export capabilities
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import io
import csv
import json

from app.services.reporting_service import ReportingService, ReportPeriod
from app.services.tax_service import TaxService

logger = logging.getLogger(__name__)

router = APIRouter()

# Global service instances
reporting_service = ReportingService()
tax_service = TaxService()


class PerformanceRequest(BaseModel):
    """Request model for performance analytics."""
    start_date: datetime
    end_date: datetime
    period: Optional[ReportPeriod] = ReportPeriod.DAILY
    symbols: Optional[List[str]] = ["SPY", "QQQ", "IWM", "VIX"]
    strategies: Optional[List[str]] = None


class TaxReportRequest(BaseModel):
    """Request model for tax reporting."""
    start_date: datetime
    end_date: datetime
    tax_year: Optional[int] = None
    export_format: Optional[str] = "json"


class TradeRecordRequest(BaseModel):
    """Request model for adding trade records."""
    trade_id: str
    symbol: str
    strategy: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price: float
    exit_price: Optional[float] = None
    quantity: int
    trade_type: str
    pnl: float
    commission: float = 0.0
    market_conditions: Optional[Dict] = {}


@router.get("/performance/metrics")
async def get_performance_metrics(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis")
):
    """Get comprehensive performance metrics for the specified period."""
    try:
        metrics = await reporting_service.generate_performance_metrics(start_date, end_date)
        
        return {
            "status": "success",
            "data": {
                "period_start": metrics.period_start.isoformat(),
                "period_end": metrics.period_end.isoformat(),
                "total_trades": metrics.total_trades,
                "win_rate": round(metrics.win_rate * 100, 2),
                "total_pnl": round(metrics.total_pnl, 2),
                "profit_factor": round(metrics.profit_factor, 2),
                "sharpe_ratio": round(metrics.sharpe_ratio, 2),
                "max_drawdown": round(metrics.max_drawdown * 100, 2),
                "total_return": round(metrics.total_return * 100, 2),
                "annualized_return": round(metrics.annualized_return * 100, 2),
                "volatility": round(metrics.volatility * 100, 2),
                "average_win": round(metrics.average_win, 2),
                "average_loss": round(metrics.average_loss, 2),
                "largest_win": round(metrics.largest_win, 2),
                "largest_loss": round(metrics.largest_loss, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating performance metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance/strategies")
async def get_strategy_performance(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis")
):
    """Get performance analysis by trading strategy."""
    try:
        strategies = await reporting_service.analyze_strategy_performance(start_date, end_date)
        
        return {
            "status": "success",
            "data": [
                {
                    "strategy_name": strategy.strategy_name,
                    "total_trades": strategy.total_trades,
                    "win_rate": round(strategy.win_rate * 100, 2),
                    "total_pnl": round(strategy.total_pnl, 2),
                    "average_pnl_per_trade": round(strategy.average_pnl_per_trade, 2),
                    "best_trade": round(strategy.best_trade, 2),
                    "worst_trade": round(strategy.worst_trade, 2),
                    "sharpe_ratio": round(strategy.sharpe_ratio, 2),
                    "symbols_traded": strategy.symbols_traded,
                    "max_consecutive_wins": strategy.max_consecutive_wins,
                    "max_consecutive_losses": strategy.max_consecutive_losses
                }
                for strategy in strategies
            ]
        }
        
    except Exception as e:
        logger.error(f"Error analyzing strategy performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk/metrics")
async def get_risk_metrics(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis")
):
    """Get comprehensive risk analysis metrics."""
    try:
        risk_metrics = await reporting_service.calculate_risk_metrics(start_date, end_date)
        
        return {
            "status": "success",
            "data": {
                "var_95": round(risk_metrics.var_95 * 100, 2),
                "var_99": round(risk_metrics.var_99 * 100, 2),
                "expected_shortfall": round(risk_metrics.expected_shortfall * 100, 2),
                "maximum_drawdown": round(risk_metrics.maximum_drawdown * 100, 2),
                "beta_spy": round(risk_metrics.beta_spy, 2),
                "correlation_spy": round(risk_metrics.correlation_spy, 2),
                "correlation_vix": round(risk_metrics.correlation_vix, 2),
                "position_concentration": {
                    symbol: round(concentration * 100, 2)
                    for symbol, concentration in risk_metrics.position_concentration.items()
                },
                "leverage_ratio": round(risk_metrics.leverage_ratio, 2),
                "risk_adjusted_return": round(risk_metrics.risk_adjusted_return * 100, 2)
            }
        }
        
    except Exception as e:
        logger.error(f"Error calculating risk metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/market-regimes/analysis")
async def get_market_regime_analysis(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis")
):
    """Get performance analysis across different market regimes."""
    try:
        analysis = await reporting_service.analyze_market_regimes(start_date, end_date)
        
        return {
            "status": "success",
            "data": {
                "low_volatility_performance": round(analysis.low_volatility_performance, 2),
                "high_volatility_performance": round(analysis.high_volatility_performance, 2),
                "trending_market_performance": round(analysis.trending_market_performance, 2),
                "sideways_market_performance": round(analysis.sideways_market_performance, 2),
                "correlation_breakdown_performance": round(analysis.correlation_breakdown_performance, 2),
                "vix_regime_performance": {
                    regime: round(performance, 2)
                    for regime, performance in analysis.vix_regime_performance.items()
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error analyzing market regimes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tax/summary")
async def get_tax_summary(
    start_date: datetime = Query(..., description="Start date for tax analysis"),
    end_date: datetime = Query(..., description="End date for tax analysis")
):
    """Get comprehensive tax summary for the specified period."""
    try:
        tax_summary = await tax_service.generate_tax_summary(start_date, end_date)
        
        return {
            "status": "success",
            "data": {
                "period_start": tax_summary.period_start.isoformat(),
                "period_end": tax_summary.period_end.isoformat(),
                "short_term_gains": round(tax_summary.short_term_gains, 2),
                "long_term_gains": round(tax_summary.long_term_gains, 2),
                "total_gains": round(tax_summary.total_gains, 2),
                "wash_sale_adjustments": round(tax_summary.wash_sale_adjustments, 2),
                "realized_gains": round(tax_summary.realized_gains, 2),
                "unrealized_gains": round(tax_summary.unrealized_gains, 2),
                "tax_efficiency_score": round(tax_summary.tax_efficiency_score, 1),
                "recommendations": tax_summary.recommendations
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating tax summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/reports/comprehensive")
async def get_comprehensive_report(
    start_date: datetime = Query(..., description="Start date for report"),
    end_date: datetime = Query(..., description="End date for report")
):
    """Generate a comprehensive performance report with all analytics."""
    try:
        report = await reporting_service.generate_comprehensive_report(start_date, end_date)
        
        return {
            "status": "success",
            "data": {
                "report_id": report.report_id,
                "generated_at": report.generated_at.isoformat(),
                "period_start": report.period_start.isoformat(),
                "period_end": report.period_end.isoformat(),
                "performance_summary": {
                    "total_trades": report.performance_metrics.total_trades,
                    "win_rate": round(report.performance_metrics.win_rate * 100, 2),
                    "total_pnl": round(report.performance_metrics.total_pnl, 2),
                    "sharpe_ratio": round(report.performance_metrics.sharpe_ratio, 2),
                    "max_drawdown": round(report.performance_metrics.max_drawdown * 100, 2)
                },
                "tax_summary": {
                    "short_term_gains": round(report.tax_summary.short_term_gains, 2),
                    "long_term_gains": round(report.tax_summary.long_term_gains, 2),
                    "tax_efficiency_score": round(report.tax_summary.tax_efficiency_score, 1)
                },
                "risk_summary": {
                    "var_95": round(report.risk_metrics.var_95 * 100, 2),
                    "maximum_drawdown": round(report.risk_metrics.maximum_drawdown * 100, 2),
                    "correlation_spy": round(report.risk_metrics.correlation_spy, 2)
                },
                "strategy_performance": [
                    {
                        "strategy": strategy.strategy_name,
                        "total_pnl": round(strategy.total_pnl, 2),
                        "win_rate": round(strategy.win_rate * 100, 2),
                        "trades": strategy.total_trades
                    }
                    for strategy in report.strategy_performance
                ],
                "recommendations": report.recommendations,
                "charts_data": report.charts_data
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating comprehensive report: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trades/record")
async def add_trade_record(trade: TradeRecordRequest):
    """Add a trade record for analysis."""
    try:
        from app.services.reporting_service import TradeRecord
        
        trade_record = TradeRecord(
            trade_id=trade.trade_id,
            symbol=trade.symbol,
            strategy=trade.strategy,
            entry_time=trade.entry_time,
            exit_time=trade.exit_time,
            entry_price=trade.entry_price,
            exit_price=trade.exit_price,
            quantity=trade.quantity,
            trade_type=trade.trade_type,
            pnl=trade.pnl,
            commission=trade.commission,
            is_winner=trade.pnl > 0,
            holding_period=trade.exit_time - trade.entry_time if trade.exit_time else None,
            market_conditions=trade.market_conditions or {}
        )
        
        await reporting_service.add_trade_record(trade_record)
        
        return {
            "status": "success",
            "message": f"Trade record {trade.trade_id} added successfully"
        }
        
    except Exception as e:
        logger.error(f"Error adding trade record: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export/tax-data")
async def export_tax_data(
    start_date: datetime = Query(..., description="Start date for export"),
    end_date: datetime = Query(..., description="End date for export"),
    format_type: str = Query("csv", description="Export format (csv, pdf)")
):
    """Export tax data for external tax software."""
    try:
        export_data = await tax_service.export_tax_data(start_date, end_date, format_type)
        
        if format_type.lower() == "csv":
            # Create CSV response
            output = io.StringIO()
            if export_data.get("data"):
                fieldnames = export_data["data"][0].keys()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(export_data["data"])
            
            response = StreamingResponse(
                io.BytesIO(output.getvalue().encode()),
                media_type="text/csv",
                headers={"Content-Disposition": f"attachment; filename={export_data['filename']}"}
            )
            return response
        
        else:
            return {
                "status": "success",
                "data": export_data
            }
        
    except Exception as e:
        logger.error(f"Error exporting tax data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/equity-curve")
async def get_equity_curve_data(
    start_date: datetime = Query(..., description="Start date for chart"),
    end_date: datetime = Query(..., description="End date for chart")
):
    """Get equity curve data for charting."""
    try:
        charts_data = await reporting_service._generate_charts_data(start_date, end_date)
        
        return {
            "status": "success",
            "data": charts_data["equity_curve"]
        }
        
    except Exception as e:
        logger.error(f"Error generating equity curve data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/drawdown")
async def get_drawdown_data(
    start_date: datetime = Query(..., description="Start date for chart"),
    end_date: datetime = Query(..., description="End date for chart")
):
    """Get drawdown data for charting."""
    try:
        charts_data = await reporting_service._generate_charts_data(start_date, end_date)
        
        return {
            "status": "success",
            "data": charts_data["drawdown_chart"]
        }
        
    except Exception as e:
        logger.error(f"Error generating drawdown data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/charts/monthly-returns")
async def get_monthly_returns_data(
    start_date: datetime = Query(..., description="Start date for chart"),
    end_date: datetime = Query(..., description="End date for chart")
):
    """Get monthly returns data for charting."""
    try:
        charts_data = await reporting_service._generate_charts_data(start_date, end_date)
        
        return {
            "status": "success",
            "data": charts_data["monthly_returns"]
        }
        
    except Exception as e:
        logger.error(f"Error generating monthly returns data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/optimization/recommendations")
async def get_optimization_recommendations(
    start_date: datetime = Query(..., description="Start date for analysis"),
    end_date: datetime = Query(..., description="End date for analysis")
):
    """Get trading and tax optimization recommendations."""
    try:
        report = await reporting_service.generate_comprehensive_report(start_date, end_date)
        
        return {
            "status": "success",
            "data": {
                "performance_recommendations": [
                    rec for rec in report.recommendations 
                    if "performance" in rec.lower() or "strategy" in rec.lower()
                ],
                "tax_recommendations": report.tax_summary.recommendations,
                "risk_recommendations": [
                    rec for rec in report.recommendations 
                    if "risk" in rec.lower() or "drawdown" in rec.lower()
                ],
                "general_recommendations": [
                    rec for rec in report.recommendations 
                    if rec not in report.tax_summary.recommendations
                ]
            }
        }
        
    except Exception as e:
        logger.error(f"Error generating optimization recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def reporting_health_check():
    """Health check for reporting service."""
    return {
        "status": "healthy",
        "service": "reporting",
        "version": "1.0.0",
        "features": [
            "performance_analytics",
            "tax_calculations",
            "risk_analysis",
            "strategy_performance",
            "market_regime_analysis",
            "export_capabilities"
        ]
    }

