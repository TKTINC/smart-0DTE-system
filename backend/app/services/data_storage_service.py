"""
Data Storage Service for Smart-0DTE-System
Optimized time-series storage for SPY, QQQ, IWM, and VIX data

Efficient database operations with minimal storage footprint
and maximum query performance for 0DTE options trading.
"""

import asyncio
import asyncpg
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Union
import json
from contextlib import asynccontextmanager

from ..models.market_data import (
    Symbol, MarketDataPoint, OHLCData, OptionsData, VIXData,
    CorrelationData, MARKET_DATA_SCHEMA, DATABASE_INDEXES
)

logger = logging.getLogger(__name__)

class DataStorageService:
    """
    Optimized data storage service for ETF/VIX trading data
    Uses PostgreSQL with time-series optimizations
    """
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.connection_pool = None
        self.is_initialized = False
        
    async def initialize(self):
        """Initialize database connection pool and create tables"""
        try:
            # Create connection pool
            self.connection_pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                command_timeout=30
            )
            
            # Create tables and indexes
            await self._create_tables()
            await self._create_indexes()
            
            self.is_initialized = True
            logger.info("Data storage service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize data storage service: {e}")
            raise
    
    async def close(self):
        """Close database connections"""
        if self.connection_pool:
            await self.connection_pool.close()
            logger.info("Data storage service closed")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get database connection from pool"""
        if not self.connection_pool:
            raise RuntimeError("Database not initialized")
        
        async with self.connection_pool.acquire() as connection:
            yield connection
    
    async def _create_tables(self):
        """Create optimized database tables"""
        async with self.get_connection() as conn:
            # Market data real-time table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS market_data_realtime (
                    symbol VARCHAR(10) NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    price DECIMAL(10,4) NOT NULL,
                    volume BIGINT NOT NULL,
                    bid DECIMAL(10,4),
                    ask DECIMAL(10,4),
                    PRIMARY KEY (symbol, timestamp)
                )
            """)
            
            # OHLC data table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS ohlc_data (
                    symbol VARCHAR(10) NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    interval VARCHAR(5) NOT NULL,
                    open DECIMAL(10,4) NOT NULL,
                    high DECIMAL(10,4) NOT NULL,
                    low DECIMAL(10,4) NOT NULL,
                    close DECIMAL(10,4) NOT NULL,
                    volume BIGINT NOT NULL,
                    PRIMARY KEY (symbol, timestamp, interval)
                )
            """)
            
            # Options data table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS options_data (
                    underlying_symbol VARCHAR(10) NOT NULL,
                    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
                    expiration DATE NOT NULL,
                    strike DECIMAL(10,2) NOT NULL,
                    option_type VARCHAR(4) NOT NULL,
                    bid DECIMAL(8,4) NOT NULL,
                    ask DECIMAL(8,4) NOT NULL,
                    last DECIMAL(8,4) NOT NULL,
                    volume INTEGER NOT NULL,
                    open_interest INTEGER NOT NULL,
                    implied_volatility DECIMAL(6,4) NOT NULL,
                    delta DECIMAL(6,4),
                    gamma DECIMAL(8,6),
                    theta DECIMAL(8,6),
                    vega DECIMAL(8,6),
                    PRIMARY KEY (underlying_symbol, timestamp, expiration, strike, option_type)
                )
            """)
            
            # VIX data table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS vix_data (
                    timestamp TIMESTAMP WITH TIME ZONE PRIMARY KEY,
                    vix_level DECIMAL(6,2) NOT NULL,
                    vix_change DECIMAL(6,2) NOT NULL,
                    vix_change_percent DECIMAL(6,2) NOT NULL,
                    term_structure JSONB NOT NULL,
                    regime VARCHAR(20) NOT NULL
                )
            """)
            
            # Correlation data table
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS correlation_data (
                    timestamp TIMESTAMP WITH TIME ZONE PRIMARY KEY,
                    spy_qqq_correlation DECIMAL(6,4) NOT NULL,
                    spy_iwm_correlation DECIMAL(6,4) NOT NULL,
                    qqq_iwm_correlation DECIMAL(6,4) NOT NULL,
                    spy_vix_correlation DECIMAL(6,4) NOT NULL,
                    qqq_vix_correlation DECIMAL(6,4) NOT NULL,
                    iwm_vix_correlation DECIMAL(6,4) NOT NULL,
                    regime_change_probability DECIMAL(6,4) NOT NULL
                )
            """)
            
            logger.info("Database tables created successfully")
    
    async def _create_indexes(self):
        """Create optimized indexes for fast queries"""
        async with self.get_connection() as conn:
            indexes = [
                "CREATE INDEX IF NOT EXISTS idx_market_data_symbol_time ON market_data_realtime(symbol, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_ohlc_symbol_interval_time ON ohlc_data(symbol, interval, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_options_underlying_exp ON options_data(underlying_symbol, expiration, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_options_strike_type ON options_data(underlying_symbol, strike, option_type, timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_vix_timestamp ON vix_data(timestamp DESC)",
                "CREATE INDEX IF NOT EXISTS idx_correlation_timestamp ON correlation_data(timestamp DESC)"
            ]
            
            for index_sql in indexes:
                await conn.execute(index_sql)
            
            logger.info("Database indexes created successfully")
    
    # Market Data Operations
    async def store_market_data(self, data: MarketDataPoint):
        """Store real-time market data"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO market_data_realtime 
                (symbol, timestamp, price, volume, bid, ask)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (symbol, timestamp) DO UPDATE SET
                price = EXCLUDED.price,
                volume = EXCLUDED.volume,
                bid = EXCLUDED.bid,
                ask = EXCLUDED.ask
            """, data.symbol.value, data.timestamp, data.price, 
                data.volume, data.bid, data.ask)
    
    async def store_market_data_batch(self, data_points: List[MarketDataPoint]):
        """Store multiple market data points efficiently"""
        if not data_points:
            return
        
        async with self.get_connection() as conn:
            values = [
                (d.symbol.value, d.timestamp, d.price, d.volume, d.bid, d.ask)
                for d in data_points
            ]
            
            await conn.executemany("""
                INSERT INTO market_data_realtime 
                (symbol, timestamp, price, volume, bid, ask)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (symbol, timestamp) DO UPDATE SET
                price = EXCLUDED.price,
                volume = EXCLUDED.volume,
                bid = EXCLUDED.bid,
                ask = EXCLUDED.ask
            """, values)
    
    async def get_latest_market_data(self, symbol: Symbol) -> Optional[MarketDataPoint]:
        """Get latest market data for a symbol"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM market_data_realtime 
                WHERE symbol = $1 
                ORDER BY timestamp DESC 
                LIMIT 1
            """, symbol.value)
            
            if row:
                return MarketDataPoint(
                    symbol=Symbol(row['symbol']),
                    timestamp=row['timestamp'],
                    price=float(row['price']),
                    volume=row['volume'],
                    bid=float(row['bid']) if row['bid'] else None,
                    ask=float(row['ask']) if row['ask'] else None
                )
            return None
    
    async def get_market_data_range(self, symbol: Symbol, start_time: datetime, 
                                  end_time: datetime) -> List[MarketDataPoint]:
        """Get market data for a time range"""
        async with self.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT * FROM market_data_realtime 
                WHERE symbol = $1 AND timestamp BETWEEN $2 AND $3
                ORDER BY timestamp ASC
            """, symbol.value, start_time, end_time)
            
            return [
                MarketDataPoint(
                    symbol=Symbol(row['symbol']),
                    timestamp=row['timestamp'],
                    price=float(row['price']),
                    volume=row['volume'],
                    bid=float(row['bid']) if row['bid'] else None,
                    ask=float(row['ask']) if row['ask'] else None
                )
                for row in rows
            ]
    
    # OHLC Data Operations
    async def store_ohlc_data(self, data: OHLCData):
        """Store OHLC data"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO ohlc_data 
                (symbol, timestamp, interval, open, high, low, close, volume)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (symbol, timestamp, interval) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
            """, data.symbol.value, data.timestamp, data.interval,
                data.open, data.high, data.low, data.close, data.volume)
    
    async def get_ohlc_data(self, symbol: Symbol, interval: str, 
                           start_time: datetime, end_time: datetime) -> List[OHLCData]:
        """Get OHLC data for charting"""
        async with self.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT * FROM ohlc_data 
                WHERE symbol = $1 AND interval = $2 
                AND timestamp BETWEEN $3 AND $4
                ORDER BY timestamp ASC
            """, symbol.value, interval, start_time, end_time)
            
            return [
                OHLCData(
                    symbol=Symbol(row['symbol']),
                    timestamp=row['timestamp'],
                    interval=row['interval'],
                    open=float(row['open']),
                    high=float(row['high']),
                    low=float(row['low']),
                    close=float(row['close']),
                    volume=row['volume']
                )
                for row in rows
            ]
    
    # Options Data Operations
    async def store_options_data(self, data: OptionsData):
        """Store options data"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO options_data 
                (underlying_symbol, timestamp, expiration, strike, option_type,
                 bid, ask, last, volume, open_interest, implied_volatility,
                 delta, gamma, theta, vega)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (underlying_symbol, timestamp, expiration, strike, option_type) 
                DO UPDATE SET
                bid = EXCLUDED.bid,
                ask = EXCLUDED.ask,
                last = EXCLUDED.last,
                volume = EXCLUDED.volume,
                open_interest = EXCLUDED.open_interest,
                implied_volatility = EXCLUDED.implied_volatility,
                delta = EXCLUDED.delta,
                gamma = EXCLUDED.gamma,
                theta = EXCLUDED.theta,
                vega = EXCLUDED.vega
            """, data.underlying_symbol.value, data.timestamp, data.expiration,
                data.strike, data.option_type, data.bid, data.ask, data.last,
                data.volume, data.open_interest, data.implied_volatility,
                data.delta, data.gamma, data.theta, data.vega)
    
    async def get_options_chain(self, symbol: Symbol, expiration: datetime) -> List[OptionsData]:
        """Get options chain for a specific expiration"""
        async with self.get_connection() as conn:
            rows = await conn.fetch("""
                SELECT * FROM options_data 
                WHERE underlying_symbol = $1 AND expiration = $2
                AND timestamp = (
                    SELECT MAX(timestamp) FROM options_data 
                    WHERE underlying_symbol = $1 AND expiration = $2
                )
                ORDER BY strike ASC, option_type ASC
            """, symbol.value, expiration.date())
            
            return [
                OptionsData(
                    underlying_symbol=Symbol(row['underlying_symbol']),
                    timestamp=row['timestamp'],
                    expiration=datetime.combine(row['expiration'], datetime.min.time()).replace(tzinfo=timezone.utc),
                    strike=float(row['strike']),
                    option_type=row['option_type'],
                    bid=float(row['bid']),
                    ask=float(row['ask']),
                    last=float(row['last']),
                    volume=row['volume'],
                    open_interest=row['open_interest'],
                    implied_volatility=float(row['implied_volatility']),
                    delta=float(row['delta']) if row['delta'] else None,
                    gamma=float(row['gamma']) if row['gamma'] else None,
                    theta=float(row['theta']) if row['theta'] else None,
                    vega=float(row['vega']) if row['vega'] else None
                )
                for row in rows
            ]
    
    # VIX Data Operations
    async def store_vix_data(self, data: VIXData):
        """Store VIX data"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO vix_data 
                (timestamp, vix_level, vix_change, vix_change_percent, term_structure, regime)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (timestamp) DO UPDATE SET
                vix_level = EXCLUDED.vix_level,
                vix_change = EXCLUDED.vix_change,
                vix_change_percent = EXCLUDED.vix_change_percent,
                term_structure = EXCLUDED.term_structure,
                regime = EXCLUDED.regime
            """, data.timestamp, data.vix_level, data.vix_change,
                data.vix_change_percent, json.dumps(data.term_structure), data.regime)
    
    async def get_latest_vix_data(self) -> Optional[VIXData]:
        """Get latest VIX data"""
        async with self.get_connection() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM vix_data 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            
            if row:
                return VIXData(
                    timestamp=row['timestamp'],
                    vix_level=float(row['vix_level']),
                    vix_change=float(row['vix_change']),
                    vix_change_percent=float(row['vix_change_percent']),
                    term_structure=json.loads(row['term_structure']),
                    regime=row['regime']
                )
            return None
    
    # Correlation Data Operations
    async def store_correlation_data(self, data: CorrelationData):
        """Store correlation data"""
        async with self.get_connection() as conn:
            await conn.execute("""
                INSERT INTO correlation_data 
                (timestamp, spy_qqq_correlation, spy_iwm_correlation, qqq_iwm_correlation,
                 spy_vix_correlation, qqq_vix_correlation, iwm_vix_correlation, 
                 regime_change_probability)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                ON CONFLICT (timestamp) DO UPDATE SET
                spy_qqq_correlation = EXCLUDED.spy_qqq_correlation,
                spy_iwm_correlation = EXCLUDED.spy_iwm_correlation,
                qqq_iwm_correlation = EXCLUDED.qqq_iwm_correlation,
                spy_vix_correlation = EXCLUDED.spy_vix_correlation,
                qqq_vix_correlation = EXCLUDED.qqq_vix_correlation,
                iwm_vix_correlation = EXCLUDED.iwm_vix_correlation,
                regime_change_probability = EXCLUDED.regime_change_probability
            """, data.timestamp, data.spy_qqq_correlation, data.spy_iwm_correlation,
                data.qqq_iwm_correlation, data.spy_vix_correlation, 
                data.qqq_vix_correlation, data.iwm_vix_correlation,
                data.regime_change_probability)
    
    # Data Cleanup Operations
    async def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data to maintain storage efficiency"""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        
        async with self.get_connection() as conn:
            # Clean up old market data (keep only recent for real-time)
            await conn.execute("""
                DELETE FROM market_data_realtime 
                WHERE timestamp < $1
            """, cutoff_date)
            
            # Clean up old options data (keep only recent expirations)
            await conn.execute("""
                DELETE FROM options_data 
                WHERE expiration < $1
            """, cutoff_date.date())
            
            logger.info(f"Cleaned up data older than {days_to_keep} days")
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        async with self.get_connection() as conn:
            stats = {}
            
            # Count records in each table
            tables = ['market_data_realtime', 'ohlc_data', 'options_data', 'vix_data', 'correlation_data']
            for table in tables:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                stats[f"{table}_count"] = count
            
            # Get latest timestamps
            for table in ['market_data_realtime', 'vix_data', 'correlation_data']:
                latest = await conn.fetchval(f"SELECT MAX(timestamp) FROM {table}")
                stats[f"{table}_latest"] = latest.isoformat() if latest else None
            
            return stats

# Global storage service instance
storage_service = None

async def get_storage_service() -> DataStorageService:
    """Get or create storage service instance"""
    global storage_service
    if storage_service is None:
        # Use environment variable or default for database URL
        import os
        database_url = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost/smart_0dte')
        storage_service = DataStorageService(database_url)
        await storage_service.initialize()
    return storage_service

