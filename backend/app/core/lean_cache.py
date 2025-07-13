"""
Lean Cache Service for Smart-0DTE-System
Optimized Redis caching for cost-effective deployment.
"""

import asyncio
import logging
import json
import gzip
import pickle
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
import redis.asyncio as redis
import msgpack
from functools import wraps
import hashlib

from app.core.lean_config import lean_config, cache_optimization, get_cache_ttl

logger = logging.getLogger(__name__)


class LeanCacheManager:
    """Optimized cache manager for lean deployment with intelligent strategies."""
    
    def __init__(self):
        self.redis_client = None
        self.l1_cache = {}  # In-memory L1 cache
        self.l1_cache_timestamps = {}
        self.l1_cache_max_size = cache_optimization.L1_CACHE_SIZE
        self.compression_enabled = True
        self.serialization_method = lean_config.CACHE_SERIALIZATION
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "l1_hits": 0,
            "l2_hits": 0,
            "sets": 0,
            "deletes": 0,
            "compressions": 0,
            "decompressions": 0
        }
    
    async def initialize(self) -> None:
        """Initialize Redis connection with optimized settings."""
        try:
            # Parse Redis URL
            redis_url = lean_config.REDIS_URL
            
            # Create Redis connection with lean configuration
            self.redis_client = redis.from_url(
                redis_url,
                max_connections=lean_config.REDIS_MAX_CONNECTIONS,
                socket_timeout=lean_config.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=lean_config.REDIS_SOCKET_CONNECT_TIMEOUT,
                retry_on_timeout=lean_config.REDIS_RETRY_ON_TIMEOUT,
                decode_responses=False,  # We handle encoding ourselves
                health_check_interval=30
            )
            
            # Test connection
            await self.redis_client.ping()
            
            # Configure Redis for optimal memory usage
            await self._configure_redis_optimization()
            
            # Start cache warming if enabled
            if cache_optimization.CACHE_WARMING_ENABLED:
                asyncio.create_task(self._cache_warming_loop())
            
            # Start cache monitoring
            asyncio.create_task(self._cache_monitoring_loop())
            
            logger.info("Lean cache manager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize lean cache manager: {e}")
            raise
    
    async def _configure_redis_optimization(self) -> None:
        """Configure Redis for optimal memory usage on small instances."""
        try:
            # Set memory policy for cache.t3.micro (1GB RAM)
            await self.redis_client.config_set("maxmemory", "800mb")  # Leave 200MB for OS
            await self.redis_client.config_set("maxmemory-policy", cache_optimization.CACHE_MAX_MEMORY_POLICY)
            
            # Optimize for memory efficiency
            await self.redis_client.config_set("save", "900 1 300 10 60 10000")  # Optimized save intervals
            await self.redis_client.config_set("rdbcompression", "yes")
            await self.redis_client.config_set("rdbchecksum", "yes")
            
            # Optimize for network efficiency
            await self.redis_client.config_set("tcp-keepalive", "60")
            await self.redis_client.config_set("timeout", "300")
            
            logger.info("Redis optimization configuration applied")
            
        except Exception as e:
            logger.warning(f"Could not apply Redis optimization: {e}")
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serialize data using configured method with compression."""
        try:
            # Choose serialization method
            if self.serialization_method == "msgpack":
                serialized = msgpack.packb(data)
            elif self.serialization_method == "pickle":
                serialized = pickle.dumps(data)
            else:
                serialized = json.dumps(data).encode('utf-8')
            
            # Compress if enabled and data is large enough
            if self.compression_enabled and len(serialized) > 1024:  # Compress if > 1KB
                compressed = gzip.compress(serialized)
                self.stats["compressions"] += 1
                return b"GZIP:" + compressed
            
            return serialized
            
        except Exception as e:
            logger.error(f"Failed to serialize data: {e}")
            return json.dumps(str(data)).encode('utf-8')
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserialize data with decompression support."""
        try:
            # Check if data is compressed
            if data.startswith(b"GZIP:"):
                data = gzip.decompress(data[5:])
                self.stats["decompressions"] += 1
            
            # Choose deserialization method
            if self.serialization_method == "msgpack":
                return msgpack.unpackb(data, raw=False)
            elif self.serialization_method == "pickle":
                return pickle.loads(data)
            else:
                return json.loads(data.decode('utf-8'))
                
        except Exception as e:
            logger.error(f"Failed to deserialize data: {e}")
            return None
    
    def _generate_cache_key(self, key: str, namespace: str = "smart0dte") -> str:
        """Generate standardized cache key with namespace."""
        return f"{namespace}:{key}"
    
    def _evict_l1_cache(self) -> None:
        """Evict oldest entries from L1 cache when it's full."""
        if len(self.l1_cache) >= self.l1_cache_max_size:
            # Remove oldest 20% of entries
            sorted_keys = sorted(
                self.l1_cache_timestamps.keys(),
                key=lambda k: self.l1_cache_timestamps[k]
            )
            
            keys_to_remove = sorted_keys[:int(self.l1_cache_max_size * 0.2)]
            for key in keys_to_remove:
                self.l1_cache.pop(key, None)
                self.l1_cache_timestamps.pop(key, None)
    
    async def get(self, key: str, default: Any = None) -> Any:
        """Get value from cache with L1/L2 hierarchy."""
        cache_key = self._generate_cache_key(key)
        
        try:
            # Check L1 cache first (in-memory)
            if cache_key in self.l1_cache:
                self.stats["hits"] += 1
                self.stats["l1_hits"] += 1
                self.l1_cache_timestamps[cache_key] = datetime.utcnow()
                return self.l1_cache[cache_key]
            
            # Check L2 cache (Redis)
            if self.redis_client:
                data = await self.redis_client.get(cache_key)
                if data is not None:
                    value = self._deserialize_data(data)
                    
                    # Store in L1 cache for faster access
                    self._evict_l1_cache()
                    self.l1_cache[cache_key] = value
                    self.l1_cache_timestamps[cache_key] = datetime.utcnow()
                    
                    self.stats["hits"] += 1
                    self.stats["l2_hits"] += 1
                    return value
            
            # Cache miss
            self.stats["misses"] += 1
            return default
            
        except Exception as e:
            logger.error(f"Failed to get cache value for key {key}: {e}")
            self.stats["misses"] += 1
            return default
    
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache with intelligent TTL."""
        cache_key = self._generate_cache_key(key)
        
        try:
            # Determine TTL
            if ttl is None:
                data_type = key.split(':')[0] if ':' in key else 'default'
                ttl = get_cache_ttl(data_type)
            
            # Store in L1 cache
            self._evict_l1_cache()
            self.l1_cache[cache_key] = value
            self.l1_cache_timestamps[cache_key] = datetime.utcnow()
            
            # Store in L2 cache (Redis)
            if self.redis_client:
                serialized_data = self._serialize_data(value)
                await self.redis_client.setex(cache_key, ttl, serialized_data)
            
            self.stats["sets"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to set cache value for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        cache_key = self._generate_cache_key(key)
        
        try:
            # Remove from L1 cache
            self.l1_cache.pop(cache_key, None)
            self.l1_cache_timestamps.pop(cache_key, None)
            
            # Remove from L2 cache
            if self.redis_client:
                await self.redis_client.delete(cache_key)
            
            self.stats["deletes"] += 1
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete cache value for key {key}: {e}")
            return False
    
    async def get_many(self, keys: List[str]) -> Dict[str, Any]:
        """Get multiple values from cache efficiently."""
        results = {}
        redis_keys = []
        redis_key_mapping = {}
        
        # Check L1 cache first
        for key in keys:
            cache_key = self._generate_cache_key(key)
            if cache_key in self.l1_cache:
                results[key] = self.l1_cache[cache_key]
                self.l1_cache_timestamps[cache_key] = datetime.utcnow()
                self.stats["l1_hits"] += 1
            else:
                redis_keys.append(cache_key)
                redis_key_mapping[cache_key] = key
        
        # Get remaining keys from Redis
        if redis_keys and self.redis_client:
            try:
                redis_values = await self.redis_client.mget(redis_keys)
                for cache_key, data in zip(redis_keys, redis_values):
                    original_key = redis_key_mapping[cache_key]
                    if data is not None:
                        value = self._deserialize_data(data)
                        results[original_key] = value
                        
                        # Store in L1 cache
                        self._evict_l1_cache()
                        self.l1_cache[cache_key] = value
                        self.l1_cache_timestamps[cache_key] = datetime.utcnow()
                        
                        self.stats["l2_hits"] += 1
                    else:
                        self.stats["misses"] += 1
                        
            except Exception as e:
                logger.error(f"Failed to get multiple cache values: {e}")
        
        self.stats["hits"] += len(results)
        return results
    
    async def set_many(self, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """Set multiple values in cache efficiently."""
        try:
            # Prepare data for Redis
            redis_data = {}
            for key, value in data.items():
                cache_key = self._generate_cache_key(key)
                
                # Store in L1 cache
                self._evict_l1_cache()
                self.l1_cache[cache_key] = value
                self.l1_cache_timestamps[cache_key] = datetime.utcnow()
                
                # Prepare for Redis
                redis_data[cache_key] = self._serialize_data(value)
            
            # Store in Redis with pipeline for efficiency
            if redis_data and self.redis_client:
                pipe = self.redis_client.pipeline()
                
                for cache_key, serialized_value in redis_data.items():
                    data_type = cache_key.split(':')[1] if ':' in cache_key else 'default'
                    key_ttl = ttl or get_cache_ttl(data_type)
                    pipe.setex(cache_key, key_ttl, serialized_value)
                
                await pipe.execute()
            
            self.stats["sets"] += len(data)
            return True
            
        except Exception as e:
            logger.error(f"Failed to set multiple cache values: {e}")
            return False
    
    async def clear_namespace(self, namespace: str = "smart0dte") -> bool:
        """Clear all keys in a namespace."""
        try:
            # Clear L1 cache
            keys_to_remove = [k for k in self.l1_cache.keys() if k.startswith(f"{namespace}:")]
            for key in keys_to_remove:
                self.l1_cache.pop(key, None)
                self.l1_cache_timestamps.pop(key, None)
            
            # Clear Redis keys
            if self.redis_client:
                pattern = f"{namespace}:*"
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear namespace {namespace}: {e}")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics and health metrics."""
        try:
            # Calculate hit rate
            total_requests = self.stats["hits"] + self.stats["misses"]
            hit_rate = (self.stats["hits"] / total_requests) if total_requests > 0 else 0
            
            # Get Redis info
            redis_info = {}
            if self.redis_client:
                info = await self.redis_client.info()
                redis_info = {
                    "used_memory": info.get("used_memory_human", "N/A"),
                    "used_memory_peak": info.get("used_memory_peak_human", "N/A"),
                    "connected_clients": info.get("connected_clients", 0),
                    "total_commands_processed": info.get("total_commands_processed", 0),
                    "keyspace_hits": info.get("keyspace_hits", 0),
                    "keyspace_misses": info.get("keyspace_misses", 0)
                }
            
            return {
                "l1_cache_size": len(self.l1_cache),
                "l1_cache_max_size": self.l1_cache_max_size,
                "hit_rate": round(hit_rate, 4),
                "stats": self.stats.copy(),
                "redis_info": redis_info,
                "compression_enabled": self.compression_enabled,
                "serialization_method": self.serialization_method
            }
            
        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {"error": str(e)}
    
    async def _cache_warming_loop(self) -> None:
        """Warm cache with frequently accessed data."""
        while True:
            try:
                await asyncio.sleep(cache_optimization.CACHE_WARMING_INTERVAL)
                
                # Warm cache with current market data
                current_time = datetime.utcnow()
                for symbol in lean_config.SUPPORTED_TICKERS:
                    # Pre-cache market status
                    await self.set(f"market_status:{symbol}", {
                        "symbol": symbol,
                        "timestamp": current_time,
                        "is_market_hours": self._is_market_hours(current_time)
                    }, ttl=60)
                
                logger.debug("Cache warming completed")
                
            except Exception as e:
                logger.error(f"Cache warming error: {e}")
                await asyncio.sleep(60)  # Wait before retrying
    
    async def _cache_monitoring_loop(self) -> None:
        """Monitor cache performance and adjust settings."""
        while True:
            try:
                await asyncio.sleep(cache_optimization.CACHE_MONITORING_INTERVAL)
                
                # Check hit rate
                total_requests = self.stats["hits"] + self.stats["misses"]
                if total_requests > 100:  # Only check after sufficient requests
                    hit_rate = self.stats["hits"] / total_requests
                    
                    if hit_rate < cache_optimization.CACHE_HIT_RATE_THRESHOLD:
                        logger.warning(f"Cache hit rate ({hit_rate:.2%}) below threshold ({cache_optimization.CACHE_HIT_RATE_THRESHOLD:.2%})")
                        
                        # Adjust L1 cache size if hit rate is low
                        if self.l1_cache_max_size < 200:
                            self.l1_cache_max_size = min(200, self.l1_cache_max_size + 20)
                            logger.info(f"Increased L1 cache size to {self.l1_cache_max_size}")
                
                # Reset stats periodically
                if total_requests > 10000:
                    self.stats = {key: 0 for key in self.stats.keys()}
                
            except Exception as e:
                logger.error(f"Cache monitoring error: {e}")
                await asyncio.sleep(60)
    
    def _is_market_hours(self, timestamp: datetime) -> bool:
        """Check if timestamp is during market hours."""
        # Simple market hours check (9:30 AM - 4:00 PM ET)
        hour = timestamp.hour
        minute = timestamp.minute
        
        # Convert to market time (assuming UTC input)
        market_hour = (hour - 4) % 24  # Rough EST conversion
        
        if market_hour == 9 and minute >= 30:
            return True
        elif 10 <= market_hour <= 15:
            return True
        elif market_hour == 16 and minute == 0:
            return True
        
        return False
    
    async def close(self) -> None:
        """Close cache connections."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Cache connections closed")


def cache_result(ttl: Optional[int] = None, key_prefix: str = ""):
    """Decorator for caching function results."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix or func.__name__]
            
            # Add args to key
            for arg in args:
                if isinstance(arg, (str, int, float)):
                    key_parts.append(str(arg))
                else:
                    key_parts.append(hashlib.md5(str(arg).encode()).hexdigest()[:8])
            
            # Add kwargs to key
            for k, v in sorted(kwargs.items()):
                if isinstance(v, (str, int, float)):
                    key_parts.append(f"{k}:{v}")
                else:
                    key_parts.append(f"{k}:{hashlib.md5(str(v).encode()).hexdigest()[:8]}")
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            cached_result = await lean_cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            await lean_cache_manager.set(cache_key, result, ttl)
            
            return result
        
        return wrapper
    return decorator


# Global lean cache manager instance
lean_cache_manager = LeanCacheManager()

