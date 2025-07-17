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

