"""
Lean Database Service for Smart-0DTE-System
Optimized database operations for cost-effective deployment.
"""

import asyncio
import logging
import json
import gzip
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
from contextlib import asynccontextmanager
import asyncpg
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import text
import msgpack

from app.core.lean_config import lean_config, data_optimization, get_optimal_batch_size
from app.models.market_data_models import MarketDataSnapshot, OptionsChain, VIXData

logger = logging.getLogger(__name__)

Base = declarative_base()


class LeanMarketData(Base):
    """Optimized market data model for lean deployment."""
    __tablename__ = "lean_market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    compressed_data = Column(Text)  # Compressed additional data
    
    # Composite index for efficient queries
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_timestamp_symbol', 'timestamp', 'symbol'),
    )


class LeanOptionsData(Base):
    """Optimized options data model for lean deployment."""
    __tablename__ = "lean_options_data"
    
    id = Column(Integer, primary_key=True, index=True)
    underlying_symbol = Column(String(10), nullable=False, index=True)
    option_symbol = Column(String(50), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    strike = Column(Float, nullable=False)
    expiry = Column(DateTime, nullable=False)
    option_type = Column(String(4), nullable=False)  # CALL or PUT
    bid = Column(Float, nullable=False)
    ask = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    open_interest = Column(Integer, nullable=False)
    implied_volatility = Column(Float)
    delta = Column(Float)
    gamma = Column(Float)
    theta = Column(Float)
    vega = Column(Float)
    
    # Composite indexes for efficient queries
    __table_args__ = (
        Index('idx_underlying_timestamp', 'underlying_symbol', 'timestamp'),
        Index('idx_option_symbol_timestamp', 'option_symbol', 'timestamp'),
        Index('idx_strike_expiry', 'strike', 'expiry'),
    )


class LeanSignalData(Base):
    """Optimized signal data model for lean deployment."""
    __tablename__ = "lean_signal_data"
    
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(String(50), nullable=False, unique=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    signal_type = Column(String(20), nullable=False)
    confidence = Column(Float, nullable=False)
    strategy = Column(String(30), nullable=False)
    compressed_metadata = Column(Text)  # Compressed signal metadata
    executed = Column(Boolean, default=False, index=True)
    result = Column(Float)  # P&L result if executed
    
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_executed_timestamp', 'executed', 'timestamp'),
    )


class LeanDatabaseManager:
    """Optimized database manager for lean deployment."""
    
    def __init__(self):
        self.engine = None
        self.async_session_maker = None
        self.connection_pool = None
        self.compression_enabled = data_optimization.COMPRESSION_ALGORITHM
        self.batch_size = get_optimal_batch_size("market_data")
        
    async def initialize(self) -> None:
        """Initialize database connection with optimized settings."""
        try:
            # Create async engine with lean configuration
            self.engine = create_async_engine(
                lean_config.DATABASE_URL,
                pool_size=lean_config.DATABASE_POOL_SIZE,
                max_overflow=lean_config.DATABASE_MAX_OVERFLOW,
                pool_timeout=lean_config.DATABASE_POOL_TIMEOUT,
                pool_recycle=lean_config.DATABASE_POOL_RECYCLE,
                echo=lean_config.DATABASE_ECHO,
                # Optimization settings
                pool_pre_ping=True,
                pool_reset_on_return='commit',
                connect_args={
                    "server_settings": {
                        "application_name": "smart-0dte-lean",
                        "jit": "off",  # Disable JIT for small queries
                    }
                }
            )
            
            # Create session maker
            self.async_session_maker = async_sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables if they don't exist
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            # Optimize database settings
            await self._optimize_database_settings()
            
            logger.info("Lean database manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize lean database manager: {e}")
            raise
    
    async def _optimize_database_settings(self) -> None:
        """Optimize PostgreSQL settings for lean deployment."""
        try:
            async with self.async_session_maker() as session:
                # Optimize for small instance (db.t3.small)
                optimizations = [
                    "SET shared_buffers = '256MB'",
                    "SET effective_cache_size = '1GB'",
                    "SET maintenance_work_mem = '64MB'",
                    "SET checkpoint_completion_target = 0.9",
                    "SET wal_buffers = '16MB'",
                    "SET default_statistics_target = 100",
                    "SET random_page_cost = 1.1",
                    "SET effective_io_concurrency = 200"
                ]
                
                for optimization in optimizations:
                    try:
                        await session.execute(text(optimization))
                    except Exception as e:
                        logger.warning(f"Could not apply optimization '{optimization}': {e}")
                
                await session.commit()
                
        except Exception as e:
            logger.warning(f"Could not optimize database settings: {e}")
    
    @asynccontextmanager
    async def get_session(self):
        """Get database session with proper cleanup."""
        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def _compress_data(self, data: Dict[str, Any]) -> str:
        """Compress data using configured algorithm."""
        if not data:
            return ""
        
        try:
            # Use msgpack for efficient serialization
            packed_data = msgpack.packb(data)
            
            # Compress with gzip
            if self.compression_enabled:
                compressed_data = gzip.compress(packed_data)
                return compressed_data.hex()
            else:
                return packed_data.hex()
                
        except Exception as e:
            logger.error(f"Failed to compress data: {e}")
            return json.dumps(data)  # Fallback to JSON
    
    def _decompress_data(self, compressed_data: str) -> Dict[str, Any]:
        """Decompress data using configured algorithm."""
        if not compressed_data:
            return {}
        
        try:
            # Convert from hex
            data_bytes = bytes.fromhex(compressed_data)
            
            # Decompress if needed
            if self.compression_enabled:
                decompressed_data = gzip.decompress(data_bytes)
            else:
                decompressed_data = data_bytes
            
            # Unpack with msgpack
            return msgpack.unpackb(decompressed_data, raw=False)
            
        except Exception as e:
            logger.error(f"Failed to decompress data: {e}")
            try:
                # Fallback to JSON
                return json.loads(compressed_data)
            except:
                return {}
    
    async def store_market_data_batch(self, market_data_list: List[MarketDataSnapshot]) -> None:
        """Store market data in optimized batches."""
        if not market_data_list:
            return
        
        try:
            async with self.get_session() as session:
                batch_data = []
                
                for data in market_data_list:
                    # Filter out low-volume or insignificant data
                    if (data.volume < data_optimization.MIN_VOLUME_THRESHOLD or
                        abs(data.change_percent) < data_optimization.MIN_PRICE_CHANGE_THRESHOLD):
                        continue
                    
                    # Compress additional data
                    additional_data = {
                        "change": round(data.change, data_optimization.PRICE_PRECISION),
                        "change_percent": round(data.change_percent, data_optimization.PERCENTAGE_PRECISION),
                        "high": round(data.high, data_optimization.PRICE_PRECISION),
                        "low": round(data.low, data_optimization.PRICE_PRECISION),
                        "open": round(data.open, data_optimization.PRICE_PRECISION),
                        "vwap": round(data.vwap, data_optimization.PRICE_PRECISION) if data.vwap else None
                    }
                    
                    lean_data = LeanMarketData(
                        symbol=data.symbol,
                        timestamp=data.timestamp,
                        price=round(data.price, data_optimization.PRICE_PRECISION),
                        volume=int(data.volume),
                        compressed_data=self._compress_data(additional_data)
                    )
                    batch_data.append(lean_data)
                
                # Batch insert for efficiency
                if batch_data:
                    session.add_all(batch_data)
                    await session.commit()
                    
                    logger.debug(f"Stored {len(batch_data)} market data records")
                
        except Exception as e:
            logger.error(f"Failed to store market data batch: {e}")
            raise
    
    async def store_options_data_batch(self, options_data_list: List[OptionsChain]) -> None:
        """Store options data in optimized batches."""
        if not options_data_list:
            return
        
        try:
            async with self.get_session() as session:
                batch_data = []
                
                for options_chain in options_data_list:
                    for option in options_chain.options:
                        # Filter out low-volume options
                        if option.volume < data_optimization.MIN_VOLUME_THRESHOLD:
                            continue
                        
                        lean_option = LeanOptionsData(
                            underlying_symbol=options_chain.symbol,
                            option_symbol=option.symbol,
                            timestamp=options_chain.timestamp,
                            strike=round(option.strike, data_optimization.PRICE_PRECISION),
                            expiry=option.expiry,
                            option_type=option.option_type,
                            bid=round(option.bid, data_optimization.PRICE_PRECISION),
                            ask=round(option.ask, data_optimization.PRICE_PRECISION),
                            volume=int(option.volume),
                            open_interest=int(option.open_interest),
                            implied_volatility=round(option.implied_volatility, 4) if option.implied_volatility else None,
                            delta=round(option.delta, 4) if option.delta else None,
                            gamma=round(option.gamma, 6) if option.gamma else None,
                            theta=round(option.theta, 4) if option.theta else None,
                            vega=round(option.vega, 4) if option.vega else None
                        )
                        batch_data.append(lean_option)
                
                # Batch insert for efficiency
                if batch_data:
                    session.add_all(batch_data)
                    await session.commit()
                    
                    logger.debug(f"Stored {len(batch_data)} options data records")
                
        except Exception as e:
            logger.error(f"Failed to store options data batch: {e}")
            raise
    
    async def get_recent_market_data(self, symbol: str, minutes: int = 60) -> List[Dict[str, Any]]:
        """Get recent market data with decompression."""
        try:
            async with self.get_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(minutes=minutes)
                
                result = await session.execute(
                    text("""
                        SELECT symbol, timestamp, price, volume, compressed_data
                        FROM lean_market_data
                        WHERE symbol = :symbol AND timestamp >= :cutoff_time
                        ORDER BY timestamp DESC
                        LIMIT 100
                    """),
                    {"symbol": symbol, "cutoff_time": cutoff_time}
                )
                
                market_data = []
                for row in result:
                    additional_data = self._decompress_data(row.compressed_data)
                    
                    data_point = {
                        "symbol": row.symbol,
                        "timestamp": row.timestamp,
                        "price": row.price,
                        "volume": row.volume,
                        **additional_data
                    }
                    market_data.append(data_point)
                
                return market_data
                
        except Exception as e:
            logger.error(f"Failed to get recent market data: {e}")
            return []
    
    async def get_options_chain(self, symbol: str, expiry_date: datetime) -> List[Dict[str, Any]]:
        """Get options chain data for specific expiry."""
        try:
            async with self.get_session() as session:
                result = await session.execute(
                    text("""
                        SELECT *
                        FROM lean_options_data
                        WHERE underlying_symbol = :symbol 
                        AND expiry = :expiry_date
                        AND timestamp >= :cutoff_time
                        ORDER BY strike, option_type
                    """),
                    {
                        "symbol": symbol,
                        "expiry_date": expiry_date,
                        "cutoff_time": datetime.utcnow() - timedelta(minutes=30)
                    }
                )
                
                options_data = []
                for row in result:
                    option_data = {
                        "underlying_symbol": row.underlying_symbol,
                        "option_symbol": row.option_symbol,
                        "timestamp": row.timestamp,
                        "strike": row.strike,
                        "expiry": row.expiry,
                        "option_type": row.option_type,
                        "bid": row.bid,
                        "ask": row.ask,
                        "volume": row.volume,
                        "open_interest": row.open_interest,
                        "implied_volatility": row.implied_volatility,
                        "delta": row.delta,
                        "gamma": row.gamma,
                        "theta": row.theta,
                        "vega": row.vega
                    }
                    options_data.append(option_data)
                
                return options_data
                
        except Exception as e:
            logger.error(f"Failed to get options chain: {e}")
            return []
    
    async def cleanup_old_data(self) -> None:
        """Clean up old data to manage storage costs."""
        try:
            async with self.get_session() as session:
                cutoff_time = datetime.utcnow() - timedelta(days=lean_config.DATA_RETENTION_DAYS)
                
                # Clean up old market data
                await session.execute(
                    text("DELETE FROM lean_market_data WHERE timestamp < :cutoff_time"),
                    {"cutoff_time": cutoff_time}
                )
                
                # Clean up old options data
                await session.execute(
                    text("DELETE FROM lean_options_data WHERE timestamp < :cutoff_time"),
                    {"cutoff_time": cutoff_time}
                )
                
                # Clean up old signal data (keep longer for learning)
                signal_cutoff = datetime.utcnow() - timedelta(days=lean_config.DATA_RETENTION_DAYS * 2)
                await session.execute(
                    text("DELETE FROM lean_signal_data WHERE timestamp < :cutoff_time"),
                    {"cutoff_time": signal_cutoff}
                )
                
                await session.commit()
                
                # Vacuum tables to reclaim space
                await session.execute(text("VACUUM ANALYZE lean_market_data"))
                await session.execute(text("VACUUM ANALYZE lean_options_data"))
                await session.execute(text("VACUUM ANALYZE lean_signal_data"))
                
                logger.info("Completed data cleanup and vacuum")
                
        except Exception as e:
            logger.error(f"Failed to cleanup old data: {e}")
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics for monitoring."""
        try:
            async with self.get_session() as session:
                # Get table sizes
                result = await session.execute(
                    text("""
                        SELECT 
                            schemaname,
                            tablename,
                            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size,
                            pg_total_relation_size(schemaname||'.'||tablename) as size_bytes
                        FROM pg_tables 
                        WHERE schemaname = 'public'
                        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
                    """)
                )
                
                table_stats = []
                total_size = 0
                for row in result:
                    table_stats.append({
                        "table": row.tablename,
                        "size": row.size,
                        "size_bytes": row.size_bytes
                    })
                    total_size += row.size_bytes
                
                # Get connection stats
                conn_result = await session.execute(
                    text("SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active'")
                )
                active_connections = conn_result.scalar()
                
                return {
                    "table_stats": table_stats,
                    "total_size_bytes": total_size,
                    "total_size_pretty": f"{total_size / (1024**3):.2f} GB",
                    "active_connections": active_connections,
                    "pool_size": lean_config.DATABASE_POOL_SIZE,
                    "max_overflow": lean_config.DATABASE_MAX_OVERFLOW
                }
                
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
            return {}
    
    async def close(self) -> None:
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("Database connections closed")


# Global lean database manager instance
lean_db_manager = LeanDatabaseManager()

