"""
Lean Configuration for Smart-0DTE-System
Optimized settings for cost-effective deployment while maintaining feature richness.
"""

import os
from typing import Dict, Any, List
from pydantic import BaseSettings, validator
from datetime import timedelta


class LeanConfig(BaseSettings):
    """Optimized configuration for lean deployment with 89-90% cost reduction."""
    
    # Application Settings
    APP_NAME: str = "Smart-0DTE-System-Lean"
    VERSION: str = "2.0.0-lean"
    DEBUG: bool = False
    ENVIRONMENT: str = "lean-production"
    
    # Database Settings - Optimized for db.t3.small
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://smart0dte:password@localhost:5432/smart0dte_lean")
    DATABASE_POOL_SIZE: int = 5  # Reduced from 20
    DATABASE_MAX_OVERFLOW: int = 10  # Reduced from 50
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600  # 1 hour
    DATABASE_ECHO: bool = False
    
    # Redis Settings - Optimized for cache.t3.micro
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    REDIS_MAX_CONNECTIONS: int = 10  # Reduced from 50
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_SOCKET_CONNECT_TIMEOUT: int = 5
    REDIS_RETRY_ON_TIMEOUT: bool = True
    
    # Cache Settings - Intelligent caching for efficiency
    CACHE_DEFAULT_TTL: int = 300  # 5 minutes
    CACHE_COMPRESSION: bool = True
    CACHE_SERIALIZATION: str = "msgpack"  # More efficient than JSON
    
    # Cache TTL by data type (seconds)
    CACHE_TTL_CONFIG: Dict[str, int] = {
        "real_time_prices": 30,      # 30 seconds
        "options_chains": 300,       # 5 minutes
        "correlations": 600,         # 10 minutes
        "historical_data": 3600,     # 1 hour
        "ai_predictions": 1800,      # 30 minutes
        "vix_data": 120,            # 2 minutes
        "market_status": 60,         # 1 minute
        "user_sessions": 1800        # 30 minutes
    }
    
    # Data Settings - Optimized for cost efficiency
    DATA_SAMPLING_RATE: int = 60  # 1 minute (vs real-time)
    DATA_RETENTION_DAYS: int = 30  # Reduced from 365
    HISTORICAL_DATA_LIMIT: int = 1000  # Reduced from 10000
    DATA_COMPRESSION: bool = True
    DATA_BATCH_SIZE: int = 100  # Reduced from 1000
    
    # Market Data Settings
    SUPPORTED_TICKERS: List[str] = ["SPY", "QQQ", "IWM"]
    VIX_SYMBOL: str = "VIX"
    OPTIONS_STRIKES_RANGE: int = 10  # ATM ±10 strikes only
    DATA_UPDATE_INTERVAL: int = 60  # 1 minute updates
    
    # Databento Settings - Optimized for cost
    DATABENTO_API_KEY: str = os.getenv("DATABENTO_API_KEY", "")
    DATABENTO_DATASET: str = "OPRA.PILLAR"
    DATABENTO_RATE_LIMIT: int = 100  # Requests per minute
    DATABENTO_TIMEOUT: int = 30
    DATABENTO_RETRY_ATTEMPTS: int = 3
    
    # AI Settings - Optimized for efficiency
    AI_MODEL_CACHE_SIZE: int = 100  # Reduced from 1000
    AI_PREDICTION_CACHE_TTL: int = 1800  # 30 minutes
    AI_BATCH_SIZE: int = 10  # Reduced from 100
    AI_MODEL_UPDATE_INTERVAL: int = 86400  # Daily instead of hourly
    AI_FEATURE_CACHE_SIZE: int = 500  # Reduced from 5000
    
    # Signal Generation Settings
    SIGNAL_GENERATION_INTERVAL: int = 60  # 1 minute
    SIGNAL_CONFIDENCE_THRESHOLD: float = 0.65  # 65% minimum
    SIGNAL_MAX_AGE: int = 300  # 5 minutes
    SIGNAL_CACHE_SIZE: int = 50  # Reduced from 500
    
    # Trading Settings
    MAX_CONCURRENT_POSITIONS: int = 5  # Reduced from 20
    MAX_DAILY_TRADES: int = 20  # Reduced from 100
    POSITION_SIZE_DEFAULT: float = 24000.0  # $24K per trade
    PROFIT_TARGET: float = 0.10  # 10%
    STOP_LOSS: float = 0.10  # 10%
    
    # Risk Management Settings
    RISK_CHECK_INTERVAL: int = 300  # 5 minutes
    MAX_DAILY_LOSS: float = 2000.0  # $2K daily loss limit
    VIX_EXTREME_THRESHOLD: float = 30.0
    CORRELATION_RISK_THRESHOLD: float = 0.8
    
    # IBKR Settings
    IBKR_HOST: str = os.getenv("IBKR_HOST", "localhost")
    IBKR_PORT: int = int(os.getenv("IBKR_PORT", "7497"))
    IBKR_CLIENT_ID: int = int(os.getenv("IBKR_CLIENT_ID", "1"))
    IBKR_ACCOUNT: str = os.getenv("IBKR_ACCOUNT", "")
    IBKR_PAPER_TRADING: bool = True
    IBKR_TIMEOUT: int = 30
    IBKR_RETRY_ATTEMPTS: int = 3
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    API_RATE_LIMIT: str = "1000/minute"  # Reduced from 10000/minute
    API_TIMEOUT: int = 30
    
    # Security Settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "lean-smart-0dte-secret-key-change-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    ALGORITHM: str = "HS256"
    
    # Monitoring Settings - Essential only
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    METRICS_ENABLED: bool = True
    HEALTH_CHECK_INTERVAL: int = 300  # 5 minutes
    
    # Performance Settings
    ASYNC_POOL_SIZE: int = 10  # Reduced from 100
    MAX_WORKERS: int = 2  # Reduced from 10
    REQUEST_TIMEOUT: int = 30
    RESPONSE_TIMEOUT: int = 30
    
    # Data Lifecycle Settings
    DATA_CLEANUP_INTERVAL: int = 86400  # Daily cleanup
    OLD_DATA_RETENTION_DAYS: int = 7  # Keep only 7 days of detailed data
    ARCHIVE_DATA_RETENTION_DAYS: int = 30  # Keep 30 days of archived data
    
    # Intelligent Sampling Settings
    SAMPLING_RATES: Dict[str, int] = {
        "market_hours": 1,      # Full sampling during market hours
        "pre_market": 5,        # 5-minute sampling pre-market
        "after_hours": 10,      # 10-minute sampling after hours
        "weekends": 60          # Hourly sampling on weekends
    }
    
    # Memory Management Settings
    MAX_MEMORY_USAGE_PERCENT: int = 80
    MEMORY_CHECK_INTERVAL: int = 300  # 5 minutes
    GARBAGE_COLLECTION_INTERVAL: int = 600  # 10 minutes
    
    # Feature Flags for Lean Mode
    ENABLE_ADVANCED_ANALYTICS: bool = True
    ENABLE_REAL_TIME_CHARTS: bool = True
    ENABLE_HISTORICAL_BACKTESTING: bool = True
    ENABLE_MULTI_TIMEFRAME_ANALYSIS: bool = False  # Disabled for cost savings
    ENABLE_EXTENDED_HOURS_TRADING: bool = False  # Disabled for cost savings
    ENABLE_DETAILED_LOGGING: bool = False  # Disabled for cost savings
    
    class Config:
        env_file = ".env"
        case_sensitive = True


class DataOptimizationConfig:
    """Configuration for data optimization strategies."""
    
    # Compression settings
    COMPRESSION_ALGORITHM: str = "lz4"  # Fast compression
    COMPRESSION_LEVEL: int = 1  # Low compression for speed
    
    # Data aggregation settings
    PRICE_PRECISION: int = 4  # 4 decimal places
    VOLUME_PRECISION: int = 0  # Whole numbers
    PERCENTAGE_PRECISION: int = 4  # 4 decimal places
    
    # Data filtering settings
    MIN_VOLUME_THRESHOLD: int = 100  # Minimum volume to process
    MIN_PRICE_CHANGE_THRESHOLD: float = 0.01  # Minimum price change to store
    
    # Batch processing settings
    BATCH_PROCESSING_SIZE: int = 100
    BATCH_PROCESSING_INTERVAL: int = 60  # 1 minute
    
    # Data quality settings
    MAX_DATA_AGE_SECONDS: int = 300  # 5 minutes
    DATA_VALIDATION_ENABLED: bool = True
    OUTLIER_DETECTION_ENABLED: bool = True


class CacheOptimizationConfig:
    """Configuration for cache optimization strategies."""
    
    # Cache hierarchy
    L1_CACHE_SIZE: int = 100  # In-memory cache
    L2_CACHE_SIZE: int = 1000  # Redis cache
    
    # Cache warming settings
    CACHE_WARMING_ENABLED: bool = True
    CACHE_WARMING_INTERVAL: int = 300  # 5 minutes
    
    # Cache eviction settings
    CACHE_EVICTION_POLICY: str = "lru"  # Least Recently Used
    CACHE_MAX_MEMORY_POLICY: str = "allkeys-lru"
    
    # Cache monitoring
    CACHE_HIT_RATE_THRESHOLD: float = 0.8  # 80% hit rate target
    CACHE_MONITORING_INTERVAL: int = 300  # 5 minutes


class AIOptimizationConfig:
    """Configuration for AI optimization strategies."""
    
    # Model settings
    MODEL_COMPLEXITY: str = "medium"  # Reduced from "high"
    FEATURE_SELECTION_ENABLED: bool = True
    FEATURE_COUNT_LIMIT: int = 50  # Reduced from 200
    
    # Training settings
    TRAINING_BATCH_SIZE: int = 32  # Reduced from 128
    TRAINING_EPOCHS: int = 10  # Reduced from 50
    EARLY_STOPPING_PATIENCE: int = 3
    
    # Inference settings
    INFERENCE_BATCH_SIZE: int = 10
    INFERENCE_TIMEOUT: int = 5  # 5 seconds
    MODEL_WARM_UP_ENABLED: bool = True
    
    # Model lifecycle
    MODEL_RETRAIN_INTERVAL: int = 86400  # Daily
    MODEL_VALIDATION_INTERVAL: int = 3600  # Hourly
    MODEL_BACKUP_ENABLED: bool = True


# Global lean configuration instance
lean_config = LeanConfig()
data_optimization = DataOptimizationConfig()
cache_optimization = CacheOptimizationConfig()
ai_optimization = AIOptimizationConfig()


def get_sampling_rate() -> int:
    """Get appropriate sampling rate based on current market conditions."""
    from datetime import datetime, time
    
    current_time = datetime.now().time()
    
    # Market hours: 9:30 AM - 4:00 PM ET
    market_open = time(9, 30)
    market_close = time(16, 0)
    
    # Pre-market: 4:00 AM - 9:30 AM ET
    pre_market_open = time(4, 0)
    
    # After-hours: 4:00 PM - 8:00 PM ET
    after_hours_close = time(20, 0)
    
    if market_open <= current_time <= market_close:
        return lean_config.SAMPLING_RATES["market_hours"]
    elif pre_market_open <= current_time < market_open:
        return lean_config.SAMPLING_RATES["pre_market"]
    elif market_close < current_time <= after_hours_close:
        return lean_config.SAMPLING_RATES["after_hours"]
    else:
        return lean_config.SAMPLING_RATES["weekends"]


def get_cache_ttl(data_type: str) -> int:
    """Get appropriate cache TTL for data type."""
    return lean_config.CACHE_TTL_CONFIG.get(data_type, lean_config.CACHE_DEFAULT_TTL)


def is_feature_enabled(feature: str) -> bool:
    """Check if a feature is enabled in lean mode."""
    feature_map = {
        "advanced_analytics": lean_config.ENABLE_ADVANCED_ANALYTICS,
        "real_time_charts": lean_config.ENABLE_REAL_TIME_CHARTS,
        "historical_backtesting": lean_config.ENABLE_HISTORICAL_BACKTESTING,
        "multi_timeframe_analysis": lean_config.ENABLE_MULTI_TIMEFRAME_ANALYSIS,
        "extended_hours_trading": lean_config.ENABLE_EXTENDED_HOURS_TRADING,
        "detailed_logging": lean_config.ENABLE_DETAILED_LOGGING
    }
    return feature_map.get(feature, True)


def get_memory_limit() -> int:
    """Get memory limit in MB based on lean configuration."""
    # Assume 1GB total memory for t3.micro/small instances
    total_memory_mb = 1024
    return int(total_memory_mb * (lean_config.MAX_MEMORY_USAGE_PERCENT / 100))


def get_optimal_batch_size(data_type: str) -> int:
    """Get optimal batch size for different data types."""
    batch_sizes = {
        "market_data": 50,
        "options_data": 25,
        "historical_data": 100,
        "ai_features": 20,
        "signals": 10
    }
    return batch_sizes.get(data_type, 50)

