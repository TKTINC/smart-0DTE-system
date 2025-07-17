# End-of-Day Trading Report Implementation

## Overview

This document outlines the implementation of comprehensive end-of-day reporting for both the Smart-0DTE and Mag7-7DTE systems. These reports will provide clear insights into the system's decision-making process, trade execution, and performance metrics.

## Report Components

### 1. Daily Summary Section

```python
def generate_daily_summary(date, portfolio_id):
    """Generate daily summary section of the report."""
    # Get portfolio data
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    
    # Get daily performance
    start_value = portfolio.previous_day_value
    end_value = portfolio.total_value
    daily_pnl = end_value - start_value
    daily_pnl_pct = (daily_pnl / start_value) * 100 if start_value > 0 else 0
    
    # Get trade counts
    trades = db.query(Trade).filter(
        Trade.portfolio_id == portfolio_id,
        Trade.execution_time >= date,
        Trade.execution_time < date + timedelta(days=1)
    ).all()
    
    entry_trades = [t for t in trades if t.trade_type == "entry"]
    exit_trades = [t for t in trades if t.trade_type == "exit"]
    
    # Get signal counts
    signals = db.query(Signal).filter(
        Signal.generation_time >= date,
        Signal.generation_time < date + timedelta(days=1)
    ).all()
    
    # Market context
    market_data = db.query(MarketData).filter(
        MarketData.symbol == "SPY",
        MarketData.date == date
    ).first()
    
    vix_data = db.query(MarketData).filter(
        MarketData.symbol == "VIX",
        MarketData.date == date
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
            "market_condition": _determine_market_condition(market_data, vix_data)
        }
    }
```

### 2. Signal Analysis Section

```python
def generate_signal_analysis(date, portfolio_id):
    """Generate signal analysis section of the report."""
    # Get signals for the day
    signals = db.query(Signal).filter(
        Signal.generation_time >= date,
        Signal.generation_time < date + timedelta(days=1)
    ).all()
    
    signal_details = []
    for signal in signals:
        # Get instrument
        instrument = db.query(Instrument).filter(Instrument.id == signal.instrument_id).first()
        
        # Get signal factors
        factors = db.query(SignalFactor).filter(SignalFactor.signal_id == signal.id).all()
        
        # Get trades for this signal
        trades = db.query(Trade).filter(Trade.signal_id == signal.id).all()
        
        # Calculate performance if signal was executed
        performance = None
        if signal.status == SignalStatus.EXECUTED and trades:
            entry_trades = [t for t in trades if t.trade_type == "entry"]
            exit_trades = [t for t in trades if t.trade_type == "exit"]
            
            if entry_trades and exit_trades:
                entry_value = sum(t.price * t.quantity for t in entry_trades)
                exit_value = sum(t.price * t.quantity for t in exit_trades)
                pnl = exit_value - entry_value
                pnl_pct = (pnl / entry_value) * 100 if entry_value > 0 else 0
                
                performance = {
                    "pnl": pnl,
                    "pnl_pct": pnl_pct,
                    "entry_time": min(t.execution_time for t in entry_trades),
                    "exit_time": max(t.execution_time for t in exit_trades),
                    "hold_time_minutes": (max(t.execution_time for t in exit_trades) - 
                                         min(t.execution_time for t in entry_trades)).total_seconds() / 60
                }
        
        # Decision factors analysis
        decision_factors = []
        for factor in factors:
            decision_factors.append({
                "name": factor.factor_name,
                "value": factor.factor_value,
                "weight": factor.factor_weight,
                "category": factor.factor_category,
                "description": factor.factor_description
            })
        
        # Sort factors by weight (descending)
        decision_factors.sort(key=lambda x: x["weight"], reverse=True)
        
        signal_details.append({
            "id": signal.id,
            "symbol": instrument.symbol if instrument else "Unknown",
            "signal_type": signal.signal_type.value,
            "signal_source": signal.signal_source.value,
            "confidence_score": signal.confidence_score,
            "status": signal.status.value,
            "generation_time": signal.generation_time.strftime("%H:%M:%S"),
            "decision_factors": decision_factors,
            "performance": performance,
            "notes": signal.notes
        })
    
    # Group signals by source
    signals_by_source = {}
    for signal in signals:
        source = signal.signal_source.value
        if source not in signals_by_source:
            signals_by_source[source] = []
        signals_by_source[source].append(signal)
    
    # Calculate source performance
    source_performance = {}
    for source, source_signals in signals_by_source.items():
        executed_signals = [s for s in source_signals if s.status == SignalStatus.EXECUTED]
        profitable_signals = [s for s in executed_signals if s.profit_loss and s.profit_loss > 0]
        
        source_performance[source] = {
            "total_signals": len(source_signals),
            "executed_signals": len(executed_signals),
            "profitable_signals": len(profitable_signals),
            "win_rate": len(profitable_signals) / len(executed_signals) if executed_signals else 0,
            "avg_confidence": sum(s.confidence_score for s in source_signals) / len(source_signals) if source_signals else 0
        }
    
    return {
        "signal_count": len(signals),
        "signal_details": signal_details,
        "source_performance": source_performance
    }
```

### 3. Trade Execution Section

```python
def generate_trade_execution(date, portfolio_id):
    """Generate trade execution section of the report."""
    # Get trades for the day
    trades = db.query(Trade).filter(
        Trade.portfolio_id == portfolio_id,
        Trade.execution_time >= date,
        Trade.execution_time < date + timedelta(days=1)
    ).all()
    
    trade_details = []
    for trade in trades:
        # Get instrument
        instrument = db.query(Instrument).filter(Instrument.id == trade.instrument_id).first()
        
        # Get signal
        signal = db.query(Signal).filter(Signal.id == trade.signal_id).first() if trade.signal_id else None
        
        # Get option details if applicable
        option = db.query(Option).filter(Option.id == trade.option_id).first() if trade.option_id else None
        
        trade_details.append({
            "id": trade.id,
            "symbol": instrument.symbol if instrument else "Unknown",
            "trade_type": trade.trade_type,
            "direction": trade.direction,
            "quantity": trade.quantity,
            "price": trade.price,
            "execution_time": trade.execution_time.strftime("%H:%M:%S"),
            "option_details": {
                "strike": option.strike if option else None,
                "expiration": option.expiration.strftime("%Y-%m-%d") if option and option.expiration else None,
                "option_type": option.option_type if option else None
            } if trade.option_id else None,
            "signal_id": trade.signal_id,
            "signal_confidence": signal.confidence_score if signal else None,
            "commission": trade.commission,
            "execution_quality": _calculate_execution_quality(trade, signal)
        })
    
    # Group trades by symbol
    trades_by_symbol = {}
    for trade in trades:
        instrument = db.query(Instrument).filter(Instrument.id == trade.instrument_id).first()
        symbol = instrument.symbol if instrument else "Unknown"
        
        if symbol not in trades_by_symbol:
            trades_by_symbol[symbol] = []
        trades_by_symbol[symbol].append(trade)
    
    # Calculate execution metrics
    execution_metrics = {
        "avg_execution_time_ms": _calculate_avg_execution_time(trades),
        "slippage_bps": _calculate_avg_slippage(trades),
        "commission_total": sum(t.commission for t in trades if t.commission),
        "market_impact_bps": _calculate_market_impact(trades)
    }
    
    return {
        "trade_count": len(trades),
        "trade_details": trade_details,
        "trades_by_symbol": {
            symbol: len(symbol_trades) for symbol, symbol_trades in trades_by_symbol.items()
        },
        "execution_metrics": execution_metrics
    }
```

### 4. Position Management Section

```python
def generate_position_management(date, portfolio_id):
    """Generate position management section of the report."""
    # Get positions at end of day
    positions = db.query(Position).filter(
        Position.portfolio_id == portfolio_id,
        Position.as_of_date == date
    ).all()
    
    # Get closed positions during the day
    closed_positions = db.query(ClosedPosition).filter(
        ClosedPosition.portfolio_id == portfolio_id,
        ClosedPosition.close_date == date
    ).all()
    
    position_details = []
    for position in positions:
        # Get instrument
        instrument = db.query(Instrument).filter(Instrument.id == position.instrument_id).first()
        
        # Get option details if applicable
        option = db.query(Option).filter(Option.id == position.option_id).first() if position.option_id else None
        
        # Calculate days held
        days_held = (date - position.open_date).days
        
        position_details.append({
            "id": position.id,
            "symbol": instrument.symbol if instrument else "Unknown",
            "position_type": "option" if position.option_id else "stock",
            "quantity": position.quantity,
            "entry_price": position.entry_price,
            "current_price": position.current_price,
            "current_value": position.current_value,
            "unrealized_pnl": position.unrealized_pnl,
            "unrealized_pnl_pct": position.unrealized_pnl_pct,
            "days_held": days_held,
            "option_details": {
                "strike": option.strike if option else None,
                "expiration": option.expiration.strftime("%Y-%m-%d") if option and option.expiration else None,
                "option_type": option.option_type if option else None,
                "days_to_expiration": (option.expiration - date).days if option and option.expiration else None
            } if position.option_id else None
        })
    
    closed_position_details = []
    for position in closed_positions:
        # Get instrument
        instrument = db.query(Instrument).filter(Instrument.id == position.instrument_id).first()
        
        # Get option details if applicable
        option = db.query(Option).filter(Option.id == position.option_id).first() if position.option_id else None
        
        # Calculate hold time
        hold_time_days = (position.close_date - position.open_date).days
        
        closed_position_details.append({
            "id": position.id,
            "symbol": instrument.symbol if instrument else "Unknown",
            "position_type": "option" if position.option_id else "stock",
            "quantity": position.quantity,
            "entry_price": position.entry_price,
            "exit_price": position.exit_price,
            "realized_pnl": position.realized_pnl,
            "realized_pnl_pct": position.realized_pnl_pct,
            "hold_time_days": hold_time_days,
            "option_details": {
                "strike": option.strike if option else None,
                "expiration": option.expiration.strftime("%Y-%m-%d") if option and option.expiration else None,
                "option_type": option.option_type if option else None
            } if position.option_id else None,
            "exit_reason": position.exit_reason
        })
    
    # Calculate position management metrics
    management_metrics = {
        "avg_hold_time_closed": sum(p["hold_time_days"] for p in closed_position_details) / len(closed_position_details) if closed_position_details else 0,
        "avg_profit_pct_closed": sum(p["realized_pnl_pct"] for p in closed_position_details) / len(closed_position_details) if closed_position_details else 0,
        "win_rate_closed": len([p for p in closed_position_details if p["realized_pnl"] > 0]) / len(closed_position_details) if closed_position_details else 0,
        "avg_unrealized_pnl_pct": sum(p["unrealized_pnl_pct"] for p in position_details) / len(position_details) if position_details else 0
    }
    
    return {
        "open_positions_count": len(positions),
        "closed_positions_count": len(closed_positions),
        "open_position_details": position_details,
        "closed_position_details": closed_position_details,
        "management_metrics": management_metrics
    }
```

### 5. Risk Analysis Section

```python
def generate_risk_analysis(date, portfolio_id):
    """Generate risk analysis section of the report."""
    # Get portfolio data
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    
    # Get positions at end of day
    positions = db.query(Position).filter(
        Position.portfolio_id == portfolio_id,
        Position.as_of_date == date
    ).all()
    
    # Get risk metrics
    risk_service = RiskManagementService(db)
    risk_metrics = risk_service.calculate_portfolio_risk_metrics(portfolio_id)
    
    # Calculate exposure by symbol
    exposure_by_symbol = {}
    for position in positions:
        instrument = db.query(Instrument).filter(Instrument.id == position.instrument_id).first()
        symbol = instrument.symbol if instrument else "Unknown"
        
        if symbol not in exposure_by_symbol:
            exposure_by_symbol[symbol] = 0
        
        exposure_by_symbol[symbol] += position.current_value
    
    # Calculate exposure percentages
    total_exposure = sum(exposure_by_symbol.values())
    exposure_pct_by_symbol = {
        symbol: (value / portfolio.total_value) * 100
        for symbol, value in exposure_by_symbol.items()
    }
    
    # Calculate Greeks (for options)
    total_delta = sum(p.delta * p.quantity for p in positions if p.delta is not None)
    total_gamma = sum(p.gamma * p.quantity for p in positions if p.gamma is not None)
    total_theta = sum(p.theta * p.quantity for p in positions if p.theta is not None)
    total_vega = sum(p.vega * p.quantity for p in positions if p.vega is not None)
    
    # Calculate correlation risk
    correlation_risk = risk_metrics.get("correlation_risk", 0)
    
    # Calculate VaR (Value at Risk)
    var_95 = _calculate_var(positions, portfolio.total_value, confidence=0.95)
    var_99 = _calculate_var(positions, portfolio.total_value, confidence=0.99)
    
    return {
        "total_exposure": total_exposure,
        "exposure_pct": (total_exposure / portfolio.total_value) * 100 if portfolio.total_value > 0 else 0,
        "exposure_by_symbol": exposure_by_symbol,
        "exposure_pct_by_symbol": exposure_pct_by_symbol,
        "greeks": {
            "total_delta": total_delta,
            "total_gamma": total_gamma,
            "total_theta": total_theta,
            "total_vega": total_vega,
            "delta_dollars": total_delta * 100,  # Dollar value of 1-point move
            "theta_dollars": total_theta * 100   # Dollar value of 1-day time decay
        },
        "risk_metrics": {
            "correlation_risk": correlation_risk,
            "var_95_pct": var_95,
            "var_99_pct": var_99,
            "var_95_dollars": (var_95 / 100) * portfolio.total_value,
            "var_99_dollars": (var_99 / 100) * portfolio.total_value,
            "max_drawdown_today_pct": _calculate_max_drawdown(portfolio_id, date)
        }
    }
```

### 6. System Performance Section

```python
def generate_system_performance(date, portfolio_id):
    """Generate system performance section of the report."""
    # Get signals for the day
    signals = db.query(Signal).filter(
        Signal.generation_time >= date,
        Signal.generation_time < date + timedelta(days=1)
    ).all()
    
    # Get trades for the day
    trades = db.query(Trade).filter(
        Trade.portfolio_id == portfolio_id,
        Trade.execution_time >= date,
        Trade.execution_time < date + timedelta(days=1)
    ).all()
    
    # Calculate signal accuracy
    executed_signals = [s for s in signals if s.status == SignalStatus.EXECUTED]
    profitable_signals = [s for s in executed_signals if s.profit_loss and s.profit_loss > 0]
    
    signal_accuracy = len(profitable_signals) / len(executed_signals) if executed_signals else 0
    
    # Calculate average confidence score
    avg_confidence = sum(s.confidence_score for s in signals) / len(signals) if signals else 0
    
    # Calculate execution efficiency
    avg_execution_time_ms = _calculate_avg_execution_time(trades)
    
    # Calculate decision time
    avg_decision_time_ms = _calculate_avg_decision_time(signals)
    
    # Calculate system uptime
    system_logs = db.query(SystemLog).filter(
        SystemLog.date == date
    ).all()
    
    downtime_seconds = sum(log.downtime_seconds for log in system_logs if log.downtime_seconds)
    uptime_pct = ((24 * 60 * 60) - downtime_seconds) / (24 * 60 * 60) * 100
    
    # Calculate error rate
    error_logs = db.query(ErrorLog).filter(
        ErrorLog.timestamp >= date,
        ErrorLog.timestamp < date + timedelta(days=1)
    ).all()
    
    error_rate = len(error_logs) / (len(signals) + len(trades)) if (len(signals) + len(trades)) > 0 else 0
    
    return {
        "signal_metrics": {
            "total_signals": len(signals),
            "executed_signals": len(executed_signals),
            "profitable_signals": len(profitable_signals),
            "signal_accuracy": signal_accuracy,
            "avg_confidence": avg_confidence
        },
        "execution_metrics": {
            "avg_execution_time_ms": avg_execution_time_ms,
            "avg_decision_time_ms": avg_decision_time_ms,
            "slippage_bps": _calculate_avg_slippage(trades)
        },
        "system_metrics": {
            "uptime_pct": uptime_pct,
            "error_rate": error_rate,
            "error_count": len(error_logs),
            "critical_errors": len([e for e in error_logs if e.severity == "CRITICAL"])
        }
    }
```

### 7. Next Day Outlook Section

```python
def generate_next_day_outlook(date, portfolio_id):
    """Generate next day outlook section of the report."""
    next_date = date + timedelta(days=1)
    
    # Check if next day is a trading day
    is_trading_day = _is_trading_day(next_date)
    
    if not is_trading_day:
        return {
            "is_trading_day": False,
            "next_trading_day": _get_next_trading_day(next_date)
        }
    
    # Get portfolio data
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    
    # Get positions
    positions = db.query(Position).filter(
        Position.portfolio_id == portfolio_id,
        Position.as_of_date == date
    ).all()
    
    # Check for expiring options
    expiring_options = []
    for position in positions:
        if position.option_id:
            option = db.query(Option).filter(Option.id == position.option_id).first()
            if option and option.expiration == next_date:
                instrument = db.query(Instrument).filter(Instrument.id == position.instrument_id).first()
                expiring_options.append({
                    "symbol": instrument.symbol if instrument else "Unknown",
                    "option_type": option.option_type,
                    "strike": option.strike,
                    "quantity": position.quantity,
                    "current_value": position.current_value
                })
    
    # Check for upcoming earnings
    upcoming_earnings = []
    instruments = db.query(Instrument).all()
    for instrument in instruments:
        fundamental_data = db.query(FundamentalData).filter(
            FundamentalData.instrument_id == instrument.id
        ).order_by(FundamentalData.date.desc()).first()
        
        if fundamental_data and fundamental_data.next_earnings_date == next_date:
            upcoming_earnings.append({
                "symbol": instrument.symbol,
                "earnings_time": fundamental_data.earnings_time,
                "estimated_eps": fundamental_data.estimated_eps,
                "previous_eps": fundamental_data.previous_eps
            })
    
    # Check for economic events
    economic_events = db.query(EconomicEvent).filter(
        EconomicEvent.date == next_date
    ).all()
    
    economic_event_details = []
    for event in economic_events:
        economic_event_details.append({
            "name": event.name,
            "time": event.time.strftime("%H:%M") if event.time else "Unknown",
            "importance": event.importance,
            "previous": event.previous,
            "forecast": event.forecast
        })
    
    # Calculate available capital
    available_capital = portfolio.cash_balance
    
    # Estimate potential signals
    potential_signals_count = _estimate_potential_signals(next_date)
    
    return {
        "is_trading_day": True,
        "date": next_date.strftime("%Y-%m-%d"),
        "expiring_options": expiring_options,
        "upcoming_earnings": upcoming_earnings,
        "economic_events": economic_event_details,
        "available_capital": available_capital,
        "estimated_potential_signals": potential_signals_count,
        "market_outlook": _generate_market_outlook(next_date)
    }
```

## Report Generation and Delivery

```python
def generate_end_of_day_report(date=None, portfolio_id=1):
    """Generate comprehensive end-of-day report."""
    if date is None:
        date = datetime.utcnow().date()
    
    report = {
        "report_date": date.strftime("%Y-%m-%d"),
        "generation_time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "daily_summary": generate_daily_summary(date, portfolio_id),
        "signal_analysis": generate_signal_analysis(date, portfolio_id),
        "trade_execution": generate_trade_execution(date, portfolio_id),
        "position_management": generate_position_management(date, portfolio_id),
        "risk_analysis": generate_risk_analysis(date, portfolio_id),
        "system_performance": generate_system_performance(date, portfolio_id),
        "next_day_outlook": generate_next_day_outlook(date, portfolio_id)
    }
    
    # Save report to database
    report_record = DailyReport(
        date=date,
        portfolio_id=portfolio_id,
        report_data=report
    )
    db.add(report_record)
    db.commit()
    
    # Generate PDF report
    pdf_path = _generate_pdf_report(report)
    
    # Send email notification
    _send_report_notification(pdf_path, date)
    
    return {
        "report": report,
        "pdf_path": pdf_path
    }
```

## PDF Report Generation

```python
def _generate_pdf_report(report_data):
    """Generate PDF report from report data."""
    # Create PDF file path
    date_str = report_data["report_date"]
    pdf_path = f"/path/to/reports/{date_str}_trading_report.pdf"
    
    # Create PDF document
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Build PDF content
    story = []
    
    # Add title
    styles = getSampleStyleSheet()
    title = Paragraph(f"Trading Report - {date_str}", styles["Title"])
    story.append(title)
    story.append(Spacer(1, 12))
    
    # Add daily summary section
    story.append(Paragraph("Daily Summary", styles["Heading1"]))
    summary = report_data["daily_summary"]
    
    # Create summary table
    summary_data = [
        ["Portfolio Value", f"${summary['portfolio_value']:,.2f}"],
        ["Daily P&L", f"${summary['daily_pnl']:,.2f} ({summary['daily_pnl_pct']:.2f}%)"],
        ["Total Trades", str(summary['total_trades'])],
        ["Signals Generated", str(summary['signals_generated'])],
        ["Signals Executed", str(summary['signals_executed'])],
        ["Market Condition", summary['market_context']['market_condition']]
    ]
    
    summary_table = Table(summary_data)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 24))
    
    # Add signal analysis section
    story.append(Paragraph("Signal Analysis", styles["Heading1"]))
    signals = report_data["signal_analysis"]
    
    # Add signal summary
    story.append(Paragraph(f"Total Signals: {signals['signal_count']}", styles["Normal"]))
    story.append(Spacer(1, 12))
    
    # Add source performance table
    if signals['source_performance']:
        story.append(Paragraph("Signal Source Performance", styles["Heading2"]))
        source_data = [["Source", "Signals", "Executed", "Win Rate", "Avg Confidence"]]
        
        for source, perf in signals['source_performance'].items():
            source_data.append([
                source,
                str(perf['total_signals']),
                str(perf['executed_signals']),
                f"{perf['win_rate']:.2%}",
                f"{perf['avg_confidence']:.2f}"
            ])
        
        source_table = Table(source_data)
        source_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(source_table)
        story.append(Spacer(1, 12))
    
    # Add signal details
    if signals['signal_details']:
        story.append(Paragraph("Signal Details", styles["Heading2"]))
        
        for signal in signals['signal_details']:
            signal_paragraph = Paragraph(
                f"<b>{signal['symbol']} - {signal['signal_type']}</b> "
                f"(Confidence: {signal['confidence_score']:.2f}, Status: {signal['status']})",
                styles["Normal"]
            )
            story.append(signal_paragraph)
            
            # Add decision factors
            if signal['decision_factors']:
                factor_data = [["Factor", "Value", "Weight", "Category"]]
                
                for factor in signal['decision_factors'][:5]:  # Top 5 factors
                    factor_data.append([
                        factor['name'],
                        f"{factor['value']:.4f}",
                        f"{factor['weight']:.2f}",
                        factor['category']
                    ])
                
                factor_table = Table(factor_data, colWidths=[150, 80, 80, 100])
                factor_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(factor_table)
            
            # Add performance if available
            if signal['performance']:
                perf = signal['performance']
                perf_paragraph = Paragraph(
                    f"Performance: {perf['pnl_pct']:.2f}% (${perf['pnl']:.2f}), "
                    f"Hold Time: {perf['hold_time_minutes']:.1f} minutes",
                    styles["Normal"]
                )
                story.append(perf_paragraph)
            
            story.append(Spacer(1, 12))
    
    # Continue with other sections...
    # (Trade Execution, Position Management, Risk Analysis, System Performance, Next Day Outlook)
    
    # Build PDF
    doc.build(story)
    
    return pdf_path
```

## Email Notification

```python
def _send_report_notification(pdf_path, date):
    """Send email notification with attached report."""
    # Get user preferences
    user_prefs = db.query(UserPreference).first()
    if not user_prefs or not user_prefs.email_notifications:
        return
    
    # Get user
    user = db.query(User).filter(User.id == user_prefs.user_id).first()
    if not user:
        return
    
    # Create email
    date_str = date.strftime("%Y-%m-%d")
    subject = f"Trading Report - {date_str}"
    
    # Get daily summary
    report = db.query(DailyReport).filter(
        DailyReport.date == date
    ).first()
    
    if not report or not report.report_data:
        return
    
    summary = report.report_data.get("daily_summary", {})
    
    # Create email body
    body = f"""
    <html>
    <body>
        <h1>Trading Report - {date_str}</h1>
        <p>Your end-of-day trading report is attached.</p>
        
        <h2>Daily Summary</h2>
        <table>
            <tr>
                <td><b>Portfolio Value:</b></td>
                <td>${summary.get('portfolio_value', 0):,.2f}</td>
            </tr>
            <tr>
                <td><b>Daily P&L:</b></td>
                <td>${summary.get('daily_pnl', 0):,.2f} ({summary.get('daily_pnl_pct', 0):.2f}%)</td>
            </tr>
            <tr>
                <td><b>Total Trades:</b></td>
                <td>{summary.get('total_trades', 0)}</td>
            </tr>
            <tr>
                <td><b>Signals Generated:</b></td>
                <td>{summary.get('signals_generated', 0)}</td>
            </tr>
            <tr>
                <td><b>Signals Executed:</b></td>
                <td>{summary.get('signals_executed', 0)}</td>
            </tr>
        </table>
        
        <p>Please see the attached PDF for the complete report.</p>
    </body>
    </html>
    """
    
    # Send email
    email_service = EmailService()
    email_service.send_email(
        to_email=user.email,
        subject=subject,
        body=body,
        is_html=True,
        attachments=[pdf_path]
    )
```

## API Endpoints

```python
@router.get("/reports/daily/{date}")
def get_daily_report(
    date: str,
    portfolio_id: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get daily report for a specific date."""
    try:
        report_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Check if report exists
    report = db.query(DailyReport).filter(
        DailyReport.date == report_date,
        DailyReport.portfolio_id == portfolio_id
    ).first()
    
    if not report:
        # Generate report if it doesn't exist
        report_service = ReportService(db)
        report_result = report_service.generate_end_of_day_report(report_date, portfolio_id)
        
        return report_result["report"]
    
    return report.report_data

@router.get("/reports/daily/{date}/pdf")
def get_daily_report_pdf(
    date: str,
    portfolio_id: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get daily report PDF for a specific date."""
    try:
        report_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    # Check if report exists
    report = db.query(DailyReport).filter(
        DailyReport.date == report_date,
        DailyReport.portfolio_id == portfolio_id
    ).first()
    
    if not report:
        # Generate report if it doesn't exist
        report_service = ReportService(db)
        report_result = report_service.generate_end_of_day_report(report_date, portfolio_id)
        
        return FileResponse(
            path=report_result["pdf_path"],
            filename=f"trading_report_{date}.pdf",
            media_type="application/pdf"
        )
    
    # Generate PDF if it doesn't exist
    pdf_path = f"/path/to/reports/{date}_trading_report.pdf"
    if not os.path.exists(pdf_path):
        report_service = ReportService(db)
        pdf_path = report_service._generate_pdf_report(report.report_data)
    
    return FileResponse(
        path=pdf_path,
        filename=f"trading_report_{date}.pdf",
        media_type="application/pdf"
    )
```

## Implementation Plan

1. **Database Schema Updates**
   - Create `DailyReport` model to store report data
   - Add necessary fields to existing models for tracking decision factors

2. **Service Implementation**
   - Create `ReportService` class with all report generation methods
   - Implement helper functions for calculations and data processing

3. **API Endpoints**
   - Add endpoints for retrieving reports in JSON and PDF formats
   - Implement authentication and authorization

4. **PDF Generation**
   - Implement PDF report generation using ReportLab
   - Create templates for consistent report formatting

5. **Email Notification**
   - Implement email service for report delivery
   - Add user preferences for notification settings

6. **Scheduled Execution**
   - Set up scheduled task to generate reports at market close
   - Implement retry mechanism for failed report generation

7. **Frontend Integration**
   - Create report viewer component in frontend
   - Implement interactive charts for report visualization

## Conclusion

This end-of-day reporting system provides comprehensive insights into the autonomous trading system's decision-making process, trade execution, and performance metrics. By implementing this reporting framework, users will gain a clear understanding of how the system operates without needing to monitor it throughout the trading day.

