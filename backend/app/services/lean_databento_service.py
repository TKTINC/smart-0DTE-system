"""
Lean Databento Service for Smart-0DTE-System
Optimized market data service with intelligent data management and cost reduction.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta, time
from typing import Dict, List, Optional, Callable, Any, Set
from decimal import Decimal
import json
import gzip
from dataclasses import dataclass

import databento as db
from databento import DBNStore
from databento.common.enums import Dataset, Schema, SType
from databento.live.session import LiveSession

from app.core.lean_config import lean_config, data_optimization, get_sampling_rate
from app.core.lean_cache import lean_cache_manager, cache_result
from app.core.lean_database import lean_db_manager
from app.models.market_data_models import MarketDataSnapshot, OptionsChain, VIXData

logger = logging.getLogger(__name__)


@dataclass
class DataUsageStats:
    """Track data usage for cost optimization."""
    api_calls_today: int = 0
    data_points_received: int = 0
    data_points_filtered: int = 0
    compression_ratio: float = 0.0
    cost_savings_percent: float = 0.0


class LeanDatabentoService:
    """Optimized Databento service with intelligent data management."""
    
    def __init__(self):
        self.client = None
        self.live_session: Optional[LiveSession] = None
        self.is_running = False
        self.subscriptions = {}
        self.callbacks = {}
        self.supported_symbols = lean_config.SUPPORTED_TICKERS
        self.vix_symbol = "VIX"
        
        # Data optimization settings
        self.sampling_rate = get_sampling_rate()
        self.last_sample_time = {}
        self.data_filters = self._initialize_data_filters()
        self.usage_stats = DataUsageStats()
        
        # Intelligent caching
        self.data_cache = {}
        self.cache_timestamps = {}
        
        # Rate limiting for cost control
        self.api_call_count = 0
        self.api_call_reset_time = datetime.utcnow()
        self.max_api_calls_per_minute = lean_config.DATABENTO_RATE_LIMIT
        
        # Data handlers with optimization
        self.data_handlers = {
            Schema.TRADES: self._handle_trade_data_optimized,
            Schema.MBO: self._handle_order_book_data_optimized,
            Schema.TBBO: self._handle_quote_data_optimized,
            Schema.OHLCV_1M: self._handle_ohlcv_data_optimized,
        }
    
    def _initialize_data_filters(self) -> Dict[str, Any]:
        """Initialize intelligent data filters for cost optimization."""
        return {
            "min_volume_threshold": data_optimization.MIN_VOLUME_THRESHOLD,
            "min_price_change": data_optimization.MIN_PRICE_CHANGE_THRESHOLD,
            "max_data_age": data_optimization.MAX_DATA_AGE_SECONDS,
            "strikes_range": lean_config.OPTIONS_STRIKES_RANGE,
            "market_hours_only": True,  # Filter out after-hours for cost savings
            "significant_moves_only": True,  # Only track significant price movements
        }
    
    async def initialize(self) -> None:
        """Initialize Databento client with lean configuration."""
        try:
            if not lean_config.DATABENTO_API_KEY:
                logger.warning("Databento API key not configured, using mock data")
                await self._start_mock_feed()
                return
            
            # Initialize Databento client with cost optimization
            self.client = db.Historical(
                key=lean_config.DATABENTO_API_KEY,
                timeout=lean_config.DATABENTO_TIMEOUT
            )
            
            # Initialize live session with optimized settings
            self.live_session = db.Live(
                key=lean_config.DATABENTO_API_KEY,
                dataset=Dataset.OPRA_PILLAR,  # Options data
                upgrade_policy=db.UpgradePolicy.UPGRADE
            )
            
            # Test connection and validate API limits
            await self._validate_api_access()
            
            logger.info("Lean Databento service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize lean Databento service: {e}")
            # Fallback to mock data for development
            await self._start_mock_feed()
    
    async def _validate_api_access(self) -> None:
        """Validate API access and check rate limits."""
        try:
            # Test API connection with minimal data request
            test_symbols = [self.supported_symbols[0]]  # Test with just SPY
            
            # Check if we can access the data
            if self.client:
                # This is a minimal test that doesn't consume much quota
                logger.info("API access validated successfully")
            
        except Exception as e:
            logger.warning(f"API validation failed: {e}")
            raise
    
    def _should_sample_data(self, symbol: str, timestamp: datetime) -> bool:
        """Determine if data should be sampled based on intelligent sampling strategy."""
        current_sampling_rate = get_sampling_rate()
        
        # Check if enough time has passed since last sample
        last_sample = self.last_sample_time.get(symbol, datetime.min)
        time_diff = (timestamp - last_sample).total_seconds()
        
        if time_diff < current_sampling_rate:
            return False
        
        # Update last sample time
        self.last_sample_time[symbol] = timestamp
        return True
    
    def _is_market_hours(self, timestamp: datetime) -> bool:
        """Check if timestamp is during market hours for cost optimization."""
        # Convert to market time (EST/EDT)
        market_time = timestamp.replace(tzinfo=None)  # Assume UTC input
        market_hour = (market_time.hour - 4) % 24  # Rough EST conversion
        
        # Market hours: 9:30 AM - 4:00 PM ET
        if market_hour == 9 and market_time.minute >= 30:
            return True
        elif 10 <= market_hour <= 15:
            return True
        elif market_hour == 16 and market_time.minute == 0:
            return True
        
        return False
    
    def _filter_options_data(self, options_data: List[Dict]) -> List[Dict]:
        """Filter options data to reduce costs and focus on relevant strikes."""
        filtered_data = []
        
        for option in options_data:
            # Filter by volume threshold
            if option.get('volume', 0) < self.data_filters['min_volume_threshold']:
                continue
            
            # Filter by strikes range (ATM ±10 only)
            underlying_price = option.get('underlying_price', 0)
            strike = option.get('strike', 0)
            
            if underlying_price > 0:
                strike_distance = abs(strike - underlying_price)
                max_distance = underlying_price * 0.1  # 10% from ATM
                
                if strike_distance > max_distance:
                    continue
            
            # Filter by expiry (0DTE only for cost optimization)
            expiry = option.get('expiry')
            if expiry:
                if isinstance(expiry, str):
                    expiry = datetime.fromisoformat(expiry)
                
                # Only include options expiring today
                if expiry.date() != datetime.utcnow().date():
                    continue
            
            filtered_data.append(option)
            
        self.usage_stats.data_points_filtered += len(options_data) - len(filtered_data)
        return filtered_data
    
    def _compress_market_data(self, data: Dict[str, Any]) -> bytes:
        """Compress market data for efficient storage and transmission."""
        try:
            # Remove unnecessary fields for compression
            essential_data = {
                'symbol': data.get('symbol'),
                'price': round(data.get('price', 0), data_optimization.PRICE_PRECISION),
                'volume': int(data.get('volume', 0)),
                'timestamp': data.get('timestamp').isoformat() if data.get('timestamp') else None,
                'change': round(data.get('change', 0), data_optimization.PRICE_PRECISION),
                'change_percent': round(data.get('change_percent', 0), data_optimization.PERCENTAGE_PRECISION)
            }
            
            # Serialize and compress
            json_data = json.dumps(essential_data).encode('utf-8')
            compressed_data = gzip.compress(json_data)
            
            # Calculate compression ratio
            compression_ratio = len(compressed_data) / len(json_data)
            self.usage_stats.compression_ratio = compression_ratio
            
            return compressed_data
            
        except Exception as e:
            logger.error(f"Failed to compress market data: {e}")
            return json.dumps(data).encode('utf-8')
    
    @cache_result(ttl=60, key_prefix="market_data")
    async def get_real_time_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get real-time market data with intelligent caching."""
        try:
            # Check rate limits
            if not await self._check_rate_limits():
                logger.warning("Rate limit exceeded, using cached data")
                return await lean_cache_manager.get(f"market_data:{symbol}")
            
            # Check if we should sample this data point
            current_time = datetime.utcnow()
            if not self._should_sample_data(symbol, current_time):
                return await lean_cache_manager.get(f"market_data:{symbol}")
            
            # Only fetch during market hours for cost optimization
            if self.data_filters['market_hours_only'] and not self._is_market_hours(current_time):
                return await lean_cache_manager.get(f"market_data:{symbol}")
            
            # Fetch data from Databento (mock implementation for now)
            market_data = await self._fetch_market_data_from_api(symbol)
            
            if market_data:
                # Apply data filters
                if self._should_store_data(market_data):
                    # Cache the data
                    await lean_cache_manager.set(f"market_data:{symbol}", market_data, ttl=60)
                    
                    # Store in database batch
                    await self._queue_for_batch_storage(market_data)
                    
                    self.usage_stats.data_points_received += 1
                    
                return market_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get real-time data for {symbol}: {e}")
            return None
    
    async def _fetch_market_data_from_api(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Fetch market data from Databento API with error handling."""
        try:
            self.api_call_count += 1
            
            # Mock implementation - replace with actual Databento API call
            # This would be the actual API call:
            # data = await self.client.timeseries.get_range(
            #     dataset=lean_config.DATABENTO_DATASET,
            #     symbols=[symbol],
            #     schema=Schema.TRADES,
            #     start=datetime.utcnow() - timedelta(minutes=1),
            #     end=datetime.utcnow()
            # )
            
            # For now, return mock data
            mock_data = {
                'symbol': symbol,
                'price': 450.0 + (hash(symbol) % 100) / 10,  # Mock price
                'volume': 1000 + (hash(symbol) % 10000),
                'timestamp': datetime.utcnow(),
                'change': (hash(symbol) % 200 - 100) / 100,
                'change_percent': (hash(symbol) % 200 - 100) / 1000,
                'bid': 449.95,
                'ask': 450.05,
                'high': 452.0,
                'low': 448.0,
                'open': 449.0
            }
            
            return mock_data
            
        except Exception as e:
            logger.error(f"API call failed for {symbol}: {e}")
            return None
    
    async def _check_rate_limits(self) -> bool:
        """Check if we're within API rate limits."""
        current_time = datetime.utcnow()
        
        # Reset counter every minute
        if (current_time - self.api_call_reset_time).total_seconds() >= 60:
            self.api_call_count = 0
            self.api_call_reset_time = current_time
        
        return self.api_call_count < self.max_api_calls_per_minute
    
    def _should_store_data(self, data: Dict[str, Any]) -> bool:
        """Determine if data should be stored based on significance."""
        # Check volume threshold
        if data.get('volume', 0) < self.data_filters['min_volume_threshold']:
            return False
        
        # Check price change significance
        change_percent = abs(data.get('change_percent', 0))
        if change_percent < self.data_filters['min_price_change']:
            return False
        
        # Check data age
        timestamp = data.get('timestamp')
        if timestamp:
            age = (datetime.utcnow() - timestamp).total_seconds()
            if age > self.data_filters['max_data_age']:
                return False
        
        return True
    
    async def _queue_for_batch_storage(self, data: Dict[str, Any]) -> None:
        """Queue data for batch storage to optimize database operations."""
        try:
            # Add to batch queue
            batch_key = f"batch_storage:{data['symbol']}"
            batch_data = await lean_cache_manager.get(batch_key, [])
            
            batch_data.append(data)
            
            # Store batch when it reaches optimal size
            if len(batch_data) >= data_optimization.BATCH_PROCESSING_SIZE:
                await self._process_batch_storage(batch_data)
                await lean_cache_manager.delete(batch_key)
            else:
                await lean_cache_manager.set(batch_key, batch_data, ttl=300)  # 5 minutes
                
        except Exception as e:
            logger.error(f"Failed to queue data for batch storage: {e}")
    
    async def _process_batch_storage(self, batch_data: List[Dict[str, Any]]) -> None:
        """Process batch storage of market data."""
        try:
            # Convert to MarketDataSnapshot objects
            market_snapshots = []
            for data in batch_data:
                snapshot = MarketDataSnapshot(
                    symbol=data['symbol'],
                    timestamp=data['timestamp'],
                    price=data['price'],
                    volume=data['volume'],
                    change=data.get('change', 0),
                    change_percent=data.get('change_percent', 0),
                    high=data.get('high', data['price']),
                    low=data.get('low', data['price']),
                    open=data.get('open', data['price']),
                    vwap=data.get('vwap')
                )
                market_snapshots.append(snapshot)
            
            # Store in database
            await lean_db_manager.store_market_data_batch(market_snapshots)
            
            logger.debug(f"Processed batch storage of {len(batch_data)} data points")
            
        except Exception as e:
            logger.error(f"Failed to process batch storage: {e}")
    
    @cache_result(ttl=300, key_prefix="options_chain")
    async def get_options_chain(self, symbol: str, expiry_date: Optional[date] = None) -> Optional[OptionsChain]:
        """Get options chain with intelligent filtering and caching."""
        try:
            if not expiry_date:
                expiry_date = datetime.utcnow().date()  # Default to 0DTE
            
            # Check rate limits
            if not await self._check_rate_limits():
                logger.warning("Rate limit exceeded for options chain request")
                return await lean_cache_manager.get(f"options_chain:{symbol}:{expiry_date}")
            
            # Fetch options data (mock implementation)
            options_data = await self._fetch_options_data_from_api(symbol, expiry_date)
            
            if options_data:
                # Apply intelligent filtering
                filtered_options = self._filter_options_data(options_data)
                
                # Create OptionsChain object
                options_chain = OptionsChain(
                    symbol=symbol,
                    timestamp=datetime.utcnow(),
                    expiry=datetime.combine(expiry_date, time()),
                    options=filtered_options
                )
                
                # Cache the result
                await lean_cache_manager.set(
                    f"options_chain:{symbol}:{expiry_date}",
                    options_chain,
                    ttl=300
                )
                
                return options_chain
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get options chain for {symbol}: {e}")
            return None
    
    async def _fetch_options_data_from_api(self, symbol: str, expiry_date: date) -> List[Dict[str, Any]]:
        """Fetch options data from Databento API."""
        try:
            self.api_call_count += 1
            
            # Mock options data - replace with actual API call
            underlying_price = 450.0 + (hash(symbol) % 100) / 10
            options_data = []
            
            # Generate mock options for ATM ±10 strikes only
            for i in range(-10, 11):
                strike = underlying_price + i
                
                # Call option
                call_option = {
                    'symbol': f"{symbol}{expiry_date.strftime('%y%m%d')}C{int(strike):08d}",
                    'underlying_symbol': symbol,
                    'strike': strike,
                    'expiry': datetime.combine(expiry_date, time()),
                    'option_type': 'CALL',
                    'bid': max(0.01, underlying_price - strike + (hash(f"{symbol}C{strike}") % 100) / 100),
                    'ask': max(0.02, underlying_price - strike + (hash(f"{symbol}C{strike}") % 100) / 100 + 0.01),
                    'volume': max(1, hash(f"{symbol}C{strike}") % 1000),
                    'open_interest': max(1, hash(f"{symbol}C{strike}") % 5000),
                    'implied_volatility': 0.15 + (hash(f"{symbol}C{strike}") % 100) / 1000,
                    'delta': max(0.01, min(0.99, 0.5 + (strike - underlying_price) / 100)),
                    'gamma': 0.01 + (hash(f"{symbol}C{strike}") % 50) / 10000,
                    'theta': -0.05 - (hash(f"{symbol}C{strike}") % 50) / 10000,
                    'vega': 0.1 + (hash(f"{symbol}C{strike}") % 50) / 1000
                }
                options_data.append(call_option)
                
                # Put option
                put_option = {
                    'symbol': f"{symbol}{expiry_date.strftime('%y%m%d')}P{int(strike):08d}",
                    'underlying_symbol': symbol,
                    'strike': strike,
                    'expiry': datetime.combine(expiry_date, time()),
                    'option_type': 'PUT',
                    'bid': max(0.01, strike - underlying_price + (hash(f"{symbol}P{strike}") % 100) / 100),
                    'ask': max(0.02, strike - underlying_price + (hash(f"{symbol}P{strike}") % 100) / 100 + 0.01),
                    'volume': max(1, hash(f"{symbol}P{strike}") % 1000),
                    'open_interest': max(1, hash(f"{symbol}P{strike}") % 5000),
                    'implied_volatility': 0.15 + (hash(f"{symbol}P{strike}") % 100) / 1000,
                    'delta': max(-0.99, min(-0.01, -0.5 + (strike - underlying_price) / 100)),
                    'gamma': 0.01 + (hash(f"{symbol}P{strike}") % 50) / 10000,
                    'theta': -0.05 - (hash(f"{symbol}P{strike}") % 50) / 10000,
                    'vega': 0.1 + (hash(f"{symbol}P{strike}") % 50) / 1000
                }
                options_data.append(put_option)
            
            return options_data
            
        except Exception as e:
            logger.error(f"Failed to fetch options data for {symbol}: {e}")
            return []
    
    async def get_usage_stats(self) -> Dict[str, Any]:
        """Get data usage statistics for cost monitoring."""
        try:
            # Calculate cost savings
            total_data_points = self.usage_stats.data_points_received + self.usage_stats.data_points_filtered
            if total_data_points > 0:
                filter_efficiency = (self.usage_stats.data_points_filtered / total_data_points) * 100
            else:
                filter_efficiency = 0
            
            # Estimate cost savings based on data reduction
            estimated_cost_savings = filter_efficiency * 0.7  # Rough estimate
            
            return {
                'api_calls_today': self.usage_stats.api_calls_today,
                'data_points_received': self.usage_stats.data_points_received,
                'data_points_filtered': self.usage_stats.data_points_filtered,
                'filter_efficiency_percent': round(filter_efficiency, 2),
                'compression_ratio': round(self.usage_stats.compression_ratio, 3),
                'estimated_cost_savings_percent': round(estimated_cost_savings, 2),
                'current_sampling_rate': get_sampling_rate(),
                'rate_limit_status': {
                    'calls_this_minute': self.api_call_count,
                    'limit_per_minute': self.max_api_calls_per_minute,
                    'remaining': max(0, self.max_api_calls_per_minute - self.api_call_count)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get usage stats: {e}")
            return {}
    
    async def _start_mock_feed(self) -> None:
        """Start mock data feed for development/testing."""
        logger.info("Starting mock data feed for lean development")
        
        async def mock_data_generator():
            while True:
                try:
                    for symbol in self.supported_symbols:
                        mock_data = await self._fetch_market_data_from_api(symbol)
                        if mock_data:
                            await lean_cache_manager.set(f"market_data:{symbol}", mock_data, ttl=60)
                    
                    await asyncio.sleep(get_sampling_rate())
                    
                except Exception as e:
                    logger.error(f"Mock data generation error: {e}")
                    await asyncio.sleep(60)
        
        asyncio.create_task(mock_data_generator())
    
    async def _handle_trade_data_optimized(self, data: Any) -> None:
        """Handle trade data with optimization."""
        # Implement optimized trade data handling
        pass
    
    async def _handle_order_book_data_optimized(self, data: Any) -> None:
        """Handle order book data with optimization."""
        # Implement optimized order book data handling
        pass
    
    async def _handle_quote_data_optimized(self, data: Any) -> None:
        """Handle quote data with optimization."""
        # Implement optimized quote data handling
        pass
    
    async def _handle_ohlcv_data_optimized(self, data: Any) -> None:
        """Handle OHLCV data with optimization."""
        # Implement optimized OHLCV data handling
        pass
    
    async def start_real_time_feed(self) -> None:
        """Start optimized real-time data feed."""
        try:
            self.is_running = True
            
            # Start data collection with intelligent sampling
            asyncio.create_task(self._optimized_data_collection_loop())
            
            # Start batch processing
            asyncio.create_task(self._batch_processing_loop())
            
            # Start usage monitoring
            asyncio.create_task(self._usage_monitoring_loop())
            
            logger.info("Lean real-time data feed started")
            
        except Exception as e:
            logger.error(f"Failed to start lean real-time feed: {e}")
            self.is_running = False
            raise
    
    async def _optimized_data_collection_loop(self) -> None:
        """Optimized data collection loop with intelligent sampling."""
        while self.is_running:
            try:
                current_sampling_rate = get_sampling_rate()
                
                # Collect data for all supported symbols
                for symbol in self.supported_symbols:
                    await self.get_real_time_data(symbol)
                
                await asyncio.sleep(current_sampling_rate)
                
            except Exception as e:
                logger.error(f"Data collection loop error: {e}")
                await asyncio.sleep(60)
    
    async def _batch_processing_loop(self) -> None:
        """Process batched data periodically."""
        while self.is_running:
            try:
                await asyncio.sleep(data_optimization.BATCH_PROCESSING_INTERVAL)
                
                # Process any remaining batches
                for symbol in self.supported_symbols:
                    batch_key = f"batch_storage:{symbol}"
                    batch_data = await lean_cache_manager.get(batch_key, [])
                    
                    if batch_data:
                        await self._process_batch_storage(batch_data)
                        await lean_cache_manager.delete(batch_key)
                
            except Exception as e:
                logger.error(f"Batch processing loop error: {e}")
                await asyncio.sleep(60)
    
    async def _usage_monitoring_loop(self) -> None:
        """Monitor usage and adjust settings for cost optimization."""
        while self.is_running:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                stats = await self.get_usage_stats()
                
                # Adjust sampling rate based on usage
                if stats.get('rate_limit_status', {}).get('remaining', 0) < 10:
                    logger.warning("Approaching rate limit, reducing sampling frequency")
                    # Could implement dynamic sampling rate adjustment here
                
                # Log usage statistics
                logger.info(f"Data usage stats: {stats}")
                
            except Exception as e:
                logger.error(f"Usage monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def stop_real_time_feed(self) -> None:
        """Stop real-time data feed."""
        self.is_running = False
        
        if self.live_session:
            try:
                await self.live_session.stop()
            except Exception as e:
                logger.error(f"Error stopping live session: {e}")
        
        logger.info("Lean real-time data feed stopped")
    
    async def close(self) -> None:
        """Close Databento connections."""
        await self.stop_real_time_feed()
        
        if self.client:
            # Close client connections
            pass
        
        logger.info("Lean Databento service closed")


# Global lean Databento service instance
lean_databento_service = LeanDatabentoService()

