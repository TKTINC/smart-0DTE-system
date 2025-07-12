"""
Smart-0DTE-System Configuration

This module handles all configuration settings for the application,
including database connections, API keys, and runtime parameters.
"""

import os
from typing import List, Optional
from pydantic import BaseSettings, validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Application Configuration
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    API_VERSION: str = "v1"
    
    # Database Configuration
    DATABASE_URL: str = "postgresql://smart0dte_user:smart0dte_password@localhost:5432/smart0dte"
    REDIS_URL: str = "redis://localhost:6379/0"
    INFLUXDB_URL: str = "http://localhost:8086"
    INFLUXDB_TOKEN: str = "smart0dte_influx_token_12345"
    INFLUXDB_ORG: str = "smart0dte"
    INFLUXDB_BUCKET: str = "market_data"
    
    # External API Configuration
    DATABENTO_API_KEY: str = ""
    
    # Interactive Brokers Configuration
    IBKR_HOST: str = "127.0.0.1"
    IBKR_PORT: int = 7497
    IBKR_CLIENT_ID: int = 1
    IBKR_PAPER_TRADING: bool = True
    
    # Security Configuration
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    # CORS Configuration
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    CORS_CREDENTIALS: bool = True
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 1000
    RATE_LIMIT_BURST: int = 100
    
    # Trading Configuration
    DEFAULT_POSITION_SIZE: float = 24000.0
    DEFAULT_PROFIT_TARGET: float = 0.10
    DEFAULT_STOP_LOSS: float = 0.10
    DEFAULT_CONFIDENCE_THRESHOLD: float = 0.65
    MAX_POSITIONS_PER_USER: int = 10
    DAILY_LOSS_LIMIT: float = 2400.0
    
    # Risk Management Configuration
    VIX_EMERGENCY_THRESHOLD: float = 35.0
    CORRELATION_BREAKDOWN_THRESHOLD: float = 0.3
    VOLUME_SPIKE_THRESHOLD: float = 3.0
    EMERGENCY_HALT_ENABLED: bool = True
    
    # Market Data Configuration
    MARKET_DATA_REFRESH_INTERVAL: int = 2  # seconds
    OPTIONS_CHAIN_REFRESH_INTERVAL: int = 30  # seconds
    CORRELATION_REFRESH_INTERVAL: int = 5  # seconds
    VIX_REFRESH_INTERVAL: int = 1  # seconds
    
    # Supported Tickers
    SUPPORTED_TICKERS: List[str] = ["SPY", "QQQ", "IWM"]
    
    # AWS Configuration
    AWS_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    S3_BUCKET_NAME: Optional[str] = None
    CLOUDWATCH_LOG_GROUP: str = "/aws/smart0dte/application"
    
    # Monitoring Configuration
    SENTRY_DSN: Optional[str] = None
    DATADOG_API_KEY: Optional[str] = None
    
    # Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAIL_FROM: str = "noreply@smart0dte.com"
    
    # Webhook Configuration
    SLACK_WEBHOOK_URL: Optional[str] = None
    DISCORD_WEBHOOK_URL: Optional[str] = None
    
    # Feature Flags
    ENABLE_PAPER_TRADING: bool = True
    ENABLE_LIVE_TRADING: bool = False
    ENABLE_SIGNAL_AUTOMATION: bool = True
    ENABLE_RISK_MANAGEMENT: bool = True
    ENABLE_EMERGENCY_HALT: bool = True
    ENABLE_CORRELATION_ANALYSIS: bool = True
    ENABLE_VIX_ADAPTATION: bool = True
    
    # Performance Configuration
    MAX_CONCURRENT_REQUESTS: int = 100
    DATABASE_POOL_SIZE: int = 20
    REDIS_POOL_SIZE: int = 10
    CACHE_TTL_SECONDS: int = 300
    
    # Backup Configuration
    BACKUP_ENABLED: bool = True
    BACKUP_INTERVAL_HOURS: int = 6
    BACKUP_RETENTION_DAYS: int = 30
    
    @validator("CORS_ORIGINS", pre=True)
    def assemble_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @validator("ALLOWED_HOSTS", pre=True)
    def assemble_allowed_hosts(cls, v):
        """Parse allowed hosts from string or list."""
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        return v
    
    @validator("SUPPORTED_TICKERS", pre=True)
    def assemble_supported_tickers(cls, v):
        """Parse supported tickers from string or list."""
        if isinstance(v, str):
            return [i.strip().upper() for i in v.split(",")]
        return [ticker.upper() for ticker in v]
    
    @property
    def database_url_async(self) -> str:
        """Get async database URL for SQLAlchemy."""
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT.lower() == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT.lower() == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode."""
        return self.ENVIRONMENT.lower() == "testing"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()

