# End-of-Day Reporting System Implementation Plan

## Overview

This document outlines the detailed implementation plan for adding comprehensive end-of-day reporting to both the Smart-0DTE and Mag7-7DTE systems. The reporting system will provide users with transparent insights into the autonomous trading systems' decision-making processes, trade execution, and performance metrics without requiring constant monitoring.

## Implementation Phases

### Phase 1: Database Schema Updates

#### Common Models (Shared Between Both Systems)

```python
# models/reporting.py

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, JSON, Text, Enum, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum
from datetime import datetime

from app.models.market_data import Base

class ReportType(enum.Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"

class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    report_type = Column(Enum(ReportType), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    generation_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Report data
    report_data = Column(JSON, nullable=False)
    
    # Report metadata
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    pdf_path = Column(String(500), nullable=True)
    
    # Relationships
    portfolio = relationship("Portfolio", back_populates="reports")
    
# Add relationship to Portfolio model
from app.models.portfolio import Portfolio
Portfolio.reports = relationship("Report", back_populates="portfolio")

class ReportSchedule(Base):
    __tablename__ = "report_schedules"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    report_type = Column(Enum(ReportType), nullable=False)
    
    # Schedule settings
    is_active = Column(Boolean, nullable=False, default=True)
    time_of_day = Column(String(5), nullable=False, default="17:00")  # HH:MM format
    days_of_week = Column(JSON, nullable=True)  # Array of days (0-6, 0=Sunday)
    
    # Delivery settings
    email_delivery = Column(Boolean, nullable=False, default=True)
    notification_delivery = Column(Boolean, nullable=False, default=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="report_schedules")

# Add relationship to User model
from app.models.user import User
User.report_schedules = relationship("ReportSchedule", back_populates="user")

class SignalFactor(Base):
    __tablename__ = "signal_factors"

    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("signals.id"), nullable=False)
    factor_name = Column(String(100), nullable=False)
    factor_value = Column(Float, nullable=False)
    factor_weight = Column(Float, nullable=False)
    factor_category = Column(String(50), nullable=False)  # e.g., "technical", "fundamental", etc.
    factor_description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    signal = relationship("Signal", back_populates="signal_factors")

# Add relationship to Signal model
from app.models.signal import Signal
Signal.signal_factors = relationship("SignalFactor", back_populates="signal")
```

#### System-Specific Schema Updates

##### 0DTE System

```python
# Add to models/market_data.py

class MarketCondition(Base):
    __tablename__ = "market_conditions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    
    # Market metrics
    vix_open = Column(Float, nullable=True)
    vix_high = Column(Float, nullable=True)
    vix_low = Column(Float, nullable=True)
    vix_close = Column(Float, nullable=True)
    
    spy_open = Column(Float, nullable=True)
    spy_high = Column(Float, nullable=True)
    spy_low = Column(Float, nullable=True)
    spy_close = Column(Float, nullable=True)
    spy_volume = Column(Integer, nullable=True)
    
    # Market condition classification
    condition_type = Column(String(50), nullable=True)  # e.g., "normal", "high_volatility", "trending", etc.
    is_unusual = Column(Boolean, nullable=False, default=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
```

##### 7DTE System

```python
# Add to models/market_data.py

class FundamentalData(Base):
    __tablename__ = "fundamental_data"

    id = Column(Integer, primary_key=True, index=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    date = Column(DateTime, nullable=False)
    
    # Earnings data
    next_earnings_date = Column(DateTime, nullable=True)
    earnings_time = Column(String(10), nullable=True)  # "BMO" (Before Market Open) or "AMC" (After Market Close)
    estimated_eps = Column(Float, nullable=True)
    previous_eps = Column(Float, nullable=True)
    
    # Valuation metrics
    pe_ratio = Column(Float, nullable=True)
    forward_pe = Column(Float, nullable=True)
    peg_ratio = Column(Float, nullable=True)
    price_to_sales = Column(Float, nullable=True)
    price_to_book = Column(Float, nullable=True)
    
    # Growth metrics
    revenue_growth_yoy = Column(Float, nullable=True)
    eps_growth_yoy = Column(Float, nullable=True)
    
    # Analyst ratings
    analyst_rating = Column(String(20), nullable=True)  # e.g., "Buy", "Hold", "Sell"
    price_target = Column(Float, nullable=True)
    price_target_high = Column(Float, nullable=True)
    price_target_low = Column(Float, nullable=True)
    
    # Metadata
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    instrument = relationship("Instrument", back_populates="fundamental_data")

# Add relationship to Instrument model
from app.models.market_data import Instrument
Instrument.fundamental_data = relationship("FundamentalData", back_populates="instrument")
```

### Phase 2: Report Generation Services

#### Common Service (Base Implementation)

```python
# services/reporting_service.py

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from sqlalchemy.orm import Session
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.models.reporting import Report, ReportType
from app.models.portfolio import Portfolio
from app.models.signal import Signal, SignalStatus
from app.models.trade import Trade
from app.models.position import Position, ClosedPosition
from app.models.market_data import MarketData, Instrument
from app.models.user import User, UserPreference

logger = logging.getLogger(__name__)

class ReportingService:
    """Base reporting service with common functionality."""
    
    def __init__(self, db: Session):
        self.db = db
        self.report_dir = os.environ.get("REPORT_DIR", "/app/reports")
        
        # Create report directory if it doesn't exist
        os.makedirs(self.report_dir, exist_ok=True)
    
    async def generate_daily_report(self, date: datetime.date = None, portfolio_id: int = 1) -> Dict[str, Any]:
        """Generate daily report for a specific date."""
        if date is None:
            date = datetime.utcnow().date()
        
        # Check if report already exists
        existing_report = self.db.query(Report).filter(
            Report.portfolio_id == portfolio_id,
            Report.report_type == ReportType.DAILY,
            Report.start_date == date,
            Report.end_date == date
        ).first()
        
        if existing_report:
            logger.info(f"Daily report for {date} already exists, returning existing report")
            return existing_report.report_data
        
        # Generate report data
        report_data = await self._generate_report_data(date, portfolio_id)
        
        # Create report record
        report = Report(
            portfolio_id=portfolio_id,
            report_type=ReportType.DAILY,
            start_date=date,
            end_date=date,
            title=f"Daily Trading Report - {date.strftime('%Y-%m-%d')}",
            description=f"Comprehensive trading report for {date.strftime('%Y-%m-%d')}",
            report_data=report_data
        )
        
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        
        # Generate PDF
        pdf_path = await self._generate_pdf_report(report_data, report.id)
        
        # Update report with PDF path
        report.pdf_path = pdf_path
        self.db.commit()
        
        return report_data
    
    async def _generate_report_data(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate report data for a specific date."""
        # This method should be overridden by system-specific implementations
        raise NotImplementedError("This method must be implemented by subclasses")
    
    async def _generate_pdf_report(self, report_data: Dict[str, Any], report_id: int) -> str:
        """Generate PDF report from report data."""
        # Create PDF file path
        date_str = report_data["report_date"]
        pdf_path = os.path.join(self.report_dir, f"daily_report_{date_str}_{report_id}.pdf")
        
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
        
        # Continue with other sections...
        # (Trade Execution, Position Management, Risk Analysis, System Performance, Next Day Outlook)
        
        # Build PDF
        doc.build(story)
        
        return pdf_path
    
    async def get_report_by_date(self, date: datetime.date, portfolio_id: int = 1) -> Optional[Dict[str, Any]]:
        """Get report for a specific date."""
        report = self.db.query(Report).filter(
            Report.portfolio_id == portfolio_id,
            Report.report_type == ReportType.DAILY,
            Report.start_date == date,
            Report.end_date == date
        ).first()
        
        if not report:
            return None
        
        return report.report_data
    
    async def get_report_pdf_path(self, date: datetime.date, portfolio_id: int = 1) -> Optional[str]:
        """Get PDF path for a report on a specific date."""
        report = self.db.query(Report).filter(
            Report.portfolio_id == portfolio_id,
            Report.report_type == ReportType.DAILY,
            Report.start_date == date,
            Report.end_date == date
        ).first()
        
        if not report or not report.pdf_path:
            return None
        
        return report.pdf_path
```

#### System-Specific Implementations

##### 0DTE System

```python
# services/odte_reporting_service.py

from app.services.reporting_service import ReportingService

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
    
    # Implement other report section generators...
```

##### 7DTE System

```python
# services/sevendte_reporting_service.py

from app.services.reporting_service import ReportingService

class SevenDTEReportingService(ReportingService):
    """Reporting service for 7DTE system."""
    
    async def _generate_report_data(self, date: datetime.date, portfolio_id: int) -> Dict[str, Any]:
        """Generate report data for 7DTE system."""
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
        """Generate daily summary section for 7DTE system."""
        # Similar to 0DTE implementation, but with 7DTE-specific data
        # ...
        
        # Additional 7DTE-specific data
        # Get fundamental data for Mag7 stocks
        mag7_symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META"]
        
        fundamental_data = {}
        for symbol in mag7_symbols:
            instrument = self.db.query(Instrument).filter(Instrument.symbol == symbol).first()
            if instrument:
                fund_data = self.db.query(FundamentalData).filter(
                    FundamentalData.instrument_id == instrument.id,
                    FundamentalData.date <= date
                ).order_by(FundamentalData.date.desc()).first()
                
                if fund_data:
                    fundamental_data[symbol] = {
                        "pe_ratio": fund_data.pe_ratio,
                        "price_target": fund_data.price_target,
                        "analyst_rating": fund_data.analyst_rating,
                        "next_earnings_date": fund_data.next_earnings_date.strftime("%Y-%m-%d") if fund_data.next_earnings_date else None
                    }
        
        # Rest of implementation similar to 0DTE
        # ...
        
        result = {
            # Basic data similar to 0DTE
            # ...
            
            # 7DTE-specific data
            "fundamental_context": {
                "mag7_data": fundamental_data,
                "earnings_this_week": self._get_earnings_this_week(date)
            }
        }
        
        return result
    
    def _get_earnings_this_week(self, date: datetime.date) -> List[Dict[str, Any]]:
        """Get earnings announcements for the current week."""
        # Calculate start and end of week
        start_of_week = date - timedelta(days=date.weekday())
        end_of_week = start_of_week + timedelta(days=6)
        
        # Get all instruments with earnings this week
        earnings_this_week = []
        
        instruments = self.db.query(Instrument).all()
        for instrument in instruments:
            fund_data = self.db.query(FundamentalData).filter(
                FundamentalData.instrument_id == instrument.id,
                FundamentalData.date <= date
            ).order_by(FundamentalData.date.desc()).first()
            
            if fund_data and fund_data.next_earnings_date:
                if start_of_week <= fund_data.next_earnings_date <= end_of_week:
                    earnings_this_week.append({
                        "symbol": instrument.symbol,
                        "date": fund_data.next_earnings_date.strftime("%Y-%m-%d"),
                        "time": fund_data.earnings_time,
                        "estimated_eps": fund_data.estimated_eps,
                        "previous_eps": fund_data.previous_eps
                    })
        
        return earnings_this_week
    
    # Implement other report section generators...
```

### Phase 3: API Endpoints

#### Common API Endpoints

```python
# api/v1/reporting.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.user import User
from app.models.reporting import Report, ReportType
from app.schemas.reporting import ReportResponse, ReportScheduleCreate, ReportScheduleResponse
from app.services.reporting_service import ReportingService
from app.api.deps import get_current_user

router = APIRouter()

@router.get("/reports/daily/{date}", response_model=ReportResponse)
async def get_daily_report(
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
    
    # Get appropriate reporting service based on system
    reporting_service = get_reporting_service(db)
    
    # Check if report exists
    report_data = await reporting_service.get_report_by_date(report_date, portfolio_id)
    
    if not report_data:
        # Generate report if it doesn't exist
        report_data = await reporting_service.generate_daily_report(report_date, portfolio_id)
    
    return {
        "date": date,
        "portfolio_id": portfolio_id,
        "report_data": report_data
    }

@router.get("/reports/daily/{date}/pdf")
async def get_daily_report_pdf(
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
    
    # Get appropriate reporting service based on system
    reporting_service = get_reporting_service(db)
    
    # Check if report exists
    pdf_path = await reporting_service.get_report_pdf_path(report_date, portfolio_id)
    
    if not pdf_path:
        # Generate report if it doesn't exist
        report_data = await reporting_service.generate_daily_report(report_date, portfolio_id)
        pdf_path = await reporting_service.get_report_pdf_path(report_date, portfolio_id)
    
    if not pdf_path or not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Report PDF not found")
    
    return FileResponse(
        path=pdf_path,
        filename=f"trading_report_{date}.pdf",
        media_type="application/pdf"
    )

@router.post("/reports/generate/daily", response_model=ReportResponse)
async def generate_daily_report(
    date: Optional[str] = None,
    portfolio_id: int = 1,
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate daily report for a specific date."""
    if date:
        try:
            report_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    else:
        report_date = datetime.utcnow().date()
    
    # Get appropriate reporting service based on system
    reporting_service = get_reporting_service(db)
    
    # Generate report
    if background_tasks:
        # Generate report in background
        background_tasks.add_task(reporting_service.generate_daily_report, report_date, portfolio_id)
        
        return {
            "date": report_date.strftime("%Y-%m-%d"),
            "portfolio_id": portfolio_id,
            "report_data": {"status": "generating"}
        }
    else:
        # Generate report synchronously
        report_data = await reporting_service.generate_daily_report(report_date, portfolio_id)
        
        return {
            "date": report_date.strftime("%Y-%m-%d"),
            "portfolio_id": portfolio_id,
            "report_data": report_data
        }

# Helper function to get appropriate reporting service
def get_reporting_service(db: Session) -> ReportingService:
    """Get appropriate reporting service based on system."""
    # Determine which system we're running in
    if os.environ.get("SYSTEM_TYPE") == "7DTE":
        from app.services.sevendte_reporting_service import SevenDTEReportingService
        return SevenDTEReportingService(db)
    else:
        from app.services.odte_reporting_service import ODTEReportingService
        return ODTEReportingService(db)
```

### Phase 4: Email Notification Service

```python
# services/email_service.py

import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import List, Optional

logger = logging.getLogger(__name__)

class EmailService:
    """Email service for sending notifications."""
    
    def __init__(self):
        self.smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.environ.get("SMTP_PORT", 587))
        self.smtp_username = os.environ.get("SMTP_USERNAME", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.from_email = os.environ.get("FROM_EMAIL", "noreply@smart-trading-system.com")
        self.from_name = os.environ.get("FROM_NAME", "Smart Trading System")
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        is_html: bool = False,
        attachments: Optional[List[str]] = None
    ) -> bool:
        """Send email with optional attachments."""
        try:
            # Create message
            msg = MIMEMultipart()
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            
            # Add body
            if is_html:
                msg.attach(MIMEText(body, "html"))
            else:
                msg.attach(MIMEText(body, "plain"))
            
            # Add attachments
            if attachments:
                for attachment_path in attachments:
                    if os.path.exists(attachment_path):
                        with open(attachment_path, "rb") as f:
                            attachment = MIMEApplication(f.read(), _subtype="pdf")
                            attachment.add_header(
                                "Content-Disposition",
                                f"attachment; filename={os.path.basename(attachment_path)}"
                            )
                            msg.attach(attachment)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email sent to {to_email}: {subject}")
            return True
        
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
```

### Phase 5: Scheduled Tasks

```python
# tasks/scheduled_tasks.py

import os
import logging
import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.reporting import ReportSchedule, ReportType
from app.models.user import User
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

async def generate_end_of_day_reports():
    """Generate end-of-day reports for all users with active schedules."""
    try:
        db = SessionLocal()
        
        # Get current date
        current_date = datetime.utcnow().date()
        
        # Check if today is a trading day
        if not is_trading_day(current_date):
            logger.info(f"{current_date} is not a trading day, skipping report generation")
            return
        
        # Get all active daily report schedules
        schedules = db.query(ReportSchedule).filter(
            ReportSchedule.is_active == True,
            ReportSchedule.report_type == ReportType.DAILY
        ).all()
        
        # Get appropriate reporting service based on system
        if os.environ.get("SYSTEM_TYPE") == "7DTE":
            from app.services.sevendte_reporting_service import SevenDTEReportingService
            reporting_service = SevenDTEReportingService(db)
        else:
            from app.services.odte_reporting_service import ODTEReportingService
            reporting_service = ODTEReportingService(db)
        
        # Generate reports for each schedule
        for schedule in schedules:
            try:
                # Get user
                user = db.query(User).filter(User.id == schedule.user_id).first()
                if not user:
                    logger.warning(f"User not found for schedule {schedule.id}, skipping")
                    continue
                
                # Generate report
                logger.info(f"Generating daily report for user {user.id} ({user.email})")
                report_data = await reporting_service.generate_daily_report(current_date, user.default_portfolio_id)
                
                # Send email notification if enabled
                if schedule.email_delivery and user.email:
                    # Get report PDF path
                    pdf_path = await reporting_service.get_report_pdf_path(current_date, user.default_portfolio_id)
                    
                    if pdf_path:
                        # Send email
                        email_service = EmailService()
                        email_sent = await email_service.send_email(
                            to_email=user.email,
                            subject=f"Daily Trading Report - {current_date.strftime('%Y-%m-%d')}",
                            body=generate_email_body(report_data),
                            is_html=True,
                            attachments=[pdf_path]
                        )
                        
                        if email_sent:
                            logger.info(f"Daily report email sent to {user.email}")
                        else:
                            logger.error(f"Failed to send daily report email to {user.email}")
                
                logger.info(f"Daily report generated for user {user.id}")
            
            except Exception as e:
                logger.error(f"Error generating report for schedule {schedule.id}: {e}")
        
    except Exception as e:
        logger.error(f"Error in generate_end_of_day_reports: {e}")
    
    finally:
        db.close()

def generate_email_body(report_data):
    """Generate email body from report data."""
    summary = report_data.get("daily_summary", {})
    
    return f"""
    <html>
    <body>
        <h1>Trading Report - {report_data.get("report_date")}</h1>
        <p>Your end-of-day trading report is attached.</p>
        
        <h2>Daily Summary</h2>
        <table border="1" cellpadding="5" cellspacing="0">
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

def is_trading_day(date):
    """Check if a date is a trading day (not weekend or holiday)."""
    # Check if weekend
    if date.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
        return False
    
    # Check if holiday (simplified)
    holidays = [
        # 2023 holidays
        datetime(2023, 1, 2).date(),   # New Year's Day (observed)
        datetime(2023, 1, 16).date(),  # Martin Luther King Jr. Day
        datetime(2023, 2, 20).date(),  # Presidents' Day
        datetime(2023, 4, 7).date(),   # Good Friday
        datetime(2023, 5, 29).date(),  # Memorial Day
        datetime(2023, 6, 19).date(),  # Juneteenth
        datetime(2023, 7, 4).date(),   # Independence Day
        datetime(2023, 9, 4).date(),   # Labor Day
        datetime(2023, 11, 23).date(), # Thanksgiving Day
        datetime(2023, 12, 25).date(), # Christmas Day
        
        # 2024 holidays
        datetime(2024, 1, 1).date(),   # New Year's Day
        datetime(2024, 1, 15).date(),  # Martin Luther King Jr. Day
        datetime(2024, 2, 19).date(),  # Presidents' Day
        datetime(2024, 3, 29).date(),  # Good Friday
        datetime(2024, 5, 27).date(),  # Memorial Day
        datetime(2024, 6, 19).date(),  # Juneteenth
        datetime(2024, 7, 4).date(),   # Independence Day
        datetime(2024, 9, 2).date(),   # Labor Day
        datetime(2024, 11, 28).date(), # Thanksgiving Day
        datetime(2024, 12, 25).date(), # Christmas Day
        
        # 2025 holidays
        datetime(2025, 1, 1).date(),   # New Year's Day
        datetime(2025, 1, 20).date(),  # Martin Luther King Jr. Day
        datetime(2025, 2, 17).date(),  # Presidents' Day
        datetime(2025, 4, 18).date(),  # Good Friday
        datetime(2025, 5, 26).date(),  # Memorial Day
        datetime(2025, 6, 19).date(),  # Juneteenth
        datetime(2025, 7, 4).date(),   # Independence Day
        datetime(2025, 9, 1).date(),   # Labor Day
        datetime(2025, 11, 27).date(), # Thanksgiving Day
        datetime(2025, 12, 25).date(), # Christmas Day
    ]
    
    return date not in holidays
```

### Phase 6: Integration with Main Application

#### Update Main Application

```python
# main.py

# Add reporting router to API
from app.api.v1 import reporting
app.include_router(reporting.router, prefix="/api/v1", tags=["reporting"])

# Add scheduled tasks
from app.tasks.scheduled_tasks import generate_end_of_day_reports
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Schedule end-of-day report generation (4:00 PM Eastern Time)
scheduler.add_job(
    generate_end_of_day_reports,
    CronTrigger(hour=16, minute=0, timezone="America/New_York"),
    id="generate_end_of_day_reports",
    replace_existing=True
)

# Start scheduler
scheduler.start()
```

## Implementation Timeline

1. **Week 1: Database Schema Updates**
   - Day 1-2: Implement common models
   - Day 3-4: Implement 0DTE-specific models
   - Day 5: Implement 7DTE-specific models

2. **Week 2: Report Generation Services**
   - Day 1-2: Implement base reporting service
   - Day 3-4: Implement 0DTE reporting service
   - Day 5: Implement 7DTE reporting service

3. **Week 3: API Endpoints and PDF Generation**
   - Day 1-2: Implement API endpoints
   - Day 3-5: Implement PDF generation

4. **Week 4: Email Notification and Scheduled Tasks**
   - Day 1-2: Implement email service
   - Day 3-4: Implement scheduled tasks
   - Day 5: Integration and testing

## Testing Plan

1. **Unit Tests**
   - Test each report section generator
   - Test PDF generation
   - Test email service

2. **Integration Tests**
   - Test end-to-end report generation
   - Test API endpoints
   - Test scheduled tasks

3. **Manual Testing**
   - Verify report content accuracy
   - Verify PDF formatting
   - Verify email delivery

## Deployment Plan

1. **Database Migrations**
   - Create migration scripts for new models
   - Apply migrations to both systems

2. **Code Deployment**
   - Deploy new services and API endpoints
   - Configure environment variables for email service

3. **Scheduler Configuration**
   - Configure scheduler for end-of-day report generation

## Conclusion

This implementation plan provides a comprehensive approach to adding end-of-day reporting to both the Smart-0DTE and Mag7-7DTE systems. The reporting system will provide users with transparent insights into the autonomous trading systems' decision-making processes, trade execution, and performance metrics without requiring constant monitoring.

The modular design allows for system-specific customizations while maintaining a consistent reporting framework across both systems. The scheduled report generation and email delivery ensure that users receive timely updates on their trading activities.

