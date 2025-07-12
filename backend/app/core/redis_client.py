"""
Smart-0DTE-System Redis Client

This module handles Redis connections for caching, real-time data storage,
and pub/sub messaging for the Smart-0DTE-System.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Union
import aioredis
from aioredis import Redis
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis client
redis_client: Optional[Redis] = None


async def init_redis() -> None:
    """Initialize Redis connection."""
    global redis_client
    
    try:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_POOL_SIZE,
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_keepalive_options={},
        )
        
        # Test connection
        await redis_client.ping()
        logger.info("Redis connection established successfully")
        
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        raise


async def close_redis() -> None:
    """Close Redis connection."""
    global redis_client
    
    if redis_client:
        try:
            await redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.error(f"Error closing Redis connection: {e}")


def get_redis() -> Redis:
    """Get Redis client instance."""
    if redis_client is None:
        raise RuntimeError("Redis client not initialized")
    return redis_client


class RedisManager:
    """Redis manager for handling caching and real-time data operations."""
    
    def __init__(self):
        self.client = None
    
    async def initialize(self):
        """Initialize Redis client."""
        self.client = get_redis()
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: bool = True
    ) -> bool:
        """
        Set a value in Redis.
        
        Args:
            key: Redis key
            value: Value to store
            ttl: Time to live in seconds
            serialize: Whether to JSON serialize the value
            
        Returns:
            bool: True if successful
        """
        try:
            if serialize and not isinstance(value, str):
                value = json.dumps(value, default=str)
            
            if ttl:
                return await self.client.setex(key, ttl, value)
            else:
                return await self.client.set(key, value)
                
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    async def get(
        self,
        key: str,
        deserialize: bool = True
    ) -> Optional[Any]:
        """
        Get a value from Redis.
        
        Args:
            key: Redis key
            deserialize: Whether to JSON deserialize the value
            
        Returns:
            Value or None if not found
        """
        try:
            value = await self.client.get(key)
            
            if value is None:
                return None
            
            if deserialize:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            
            return value
            
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def delete(self, *keys: str) -> int:
        """
        Delete keys from Redis.
        
        Args:
            *keys: Keys to delete
            
        Returns:
            int: Number of keys deleted
        """
        try:
            return await self.client.delete(*keys)
        except Exception as e:
            logger.error(f"Redis DELETE error for keys {keys}: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """
        Check if key exists in Redis.
        
        Args:
            key: Redis key
            
        Returns:
            bool: True if key exists
        """
        try:
            return bool(await self.client.exists(key))
        except Exception as e:
            logger.error(f"Redis EXISTS error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration for a key.
        
        Args:
            key: Redis key
            ttl: Time to live in seconds
            
        Returns:
            bool: True if successful
        """
        try:
            return await self.client.expire(key, ttl)
        except Exception as e:
            logger.error(f"Redis EXPIRE error for key {key}: {e}")
            return False
    
    async def hset(
        self,
        name: str,
        mapping: Dict[str, Any],
        serialize: bool = True
    ) -> int:
        """
        Set hash fields.
        
        Args:
            name: Hash name
            mapping: Field-value mapping
            serialize: Whether to serialize values
            
        Returns:
            int: Number of fields added
        """
        try:
            if serialize:
                mapping = {
                    k: json.dumps(v, default=str) if not isinstance(v, str) else v
                    for k, v in mapping.items()
                }
            
            return await self.client.hset(name, mapping=mapping)
            
        except Exception as e:
            logger.error(f"Redis HSET error for hash {name}: {e}")
            return 0
    
    async def hget(
        self,
        name: str,
        key: str,
        deserialize: bool = True
    ) -> Optional[Any]:
        """
        Get hash field value.
        
        Args:
            name: Hash name
            key: Field key
            deserialize: Whether to deserialize value
            
        Returns:
            Field value or None
        """
        try:
            value = await self.client.hget(name, key)
            
            if value is None:
                return None
            
            if deserialize:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            
            return value
            
        except Exception as e:
            logger.error(f"Redis HGET error for hash {name}, key {key}: {e}")
            return None
    
    async def hgetall(
        self,
        name: str,
        deserialize: bool = True
    ) -> Dict[str, Any]:
        """
        Get all hash fields.
        
        Args:
            name: Hash name
            deserialize: Whether to deserialize values
            
        Returns:
            Dict of field-value pairs
        """
        try:
            data = await self.client.hgetall(name)
            
            if not data:
                return {}
            
            if deserialize:
                result = {}
                for k, v in data.items():
                    try:
                        result[k] = json.loads(v)
                    except (json.JSONDecodeError, TypeError):
                        result[k] = v
                return result
            
            return data
            
        except Exception as e:
            logger.error(f"Redis HGETALL error for hash {name}: {e}")
            return {}
    
    async def lpush(self, key: str, *values: Any) -> int:
        """
        Push values to the left of a list.
        
        Args:
            key: List key
            *values: Values to push
            
        Returns:
            int: Length of list after push
        """
        try:
            serialized_values = [
                json.dumps(v, default=str) if not isinstance(v, str) else v
                for v in values
            ]
            return await self.client.lpush(key, *serialized_values)
        except Exception as e:
            logger.error(f"Redis LPUSH error for key {key}: {e}")
            return 0
    
    async def rpop(self, key: str, deserialize: bool = True) -> Optional[Any]:
        """
        Pop value from the right of a list.
        
        Args:
            key: List key
            deserialize: Whether to deserialize value
            
        Returns:
            Popped value or None
        """
        try:
            value = await self.client.rpop(key)
            
            if value is None:
                return None
            
            if deserialize:
                try:
                    return json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    return value
            
            return value
            
        except Exception as e:
            logger.error(f"Redis RPOP error for key {key}: {e}")
            return None
    
    async def lrange(
        self,
        key: str,
        start: int = 0,
        end: int = -1,
        deserialize: bool = True
    ) -> List[Any]:
        """
        Get range of list elements.
        
        Args:
            key: List key
            start: Start index
            end: End index
            deserialize: Whether to deserialize values
            
        Returns:
            List of values
        """
        try:
            values = await self.client.lrange(key, start, end)
            
            if not values:
                return []
            
            if deserialize:
                result = []
                for v in values:
                    try:
                        result.append(json.loads(v))
                    except (json.JSONDecodeError, TypeError):
                        result.append(v)
                return result
            
            return values
            
        except Exception as e:
            logger.error(f"Redis LRANGE error for key {key}: {e}")
            return []
    
    async def publish(self, channel: str, message: Any) -> int:
        """
        Publish message to a channel.
        
        Args:
            channel: Channel name
            message: Message to publish
            
        Returns:
            int: Number of subscribers that received the message
        """
        try:
            if not isinstance(message, str):
                message = json.dumps(message, default=str)
            
            return await self.client.publish(channel, message)
            
        except Exception as e:
            logger.error(f"Redis PUBLISH error for channel {channel}: {e}")
            return 0
    
    async def health_check(self) -> bool:
        """
        Check Redis health.
        
        Returns:
            bool: True if Redis is healthy
        """
        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Global Redis manager instance
redis_manager = RedisManager()


# Market data specific Redis operations
class MarketDataCache:
    """Specialized Redis operations for market data caching."""
    
    def __init__(self, redis_manager: RedisManager):
        self.redis = redis_manager
    
    async def set_market_data(
        self,
        symbol: str,
        data: Dict[str, Any],
        ttl: int = 3600
    ) -> bool:
        """Cache market data for a symbol."""
        key = f"market:{symbol}:current"
        data["timestamp"] = datetime.utcnow().isoformat()
        return await self.redis.set(key, data, ttl=ttl)
    
    async def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get cached market data for a symbol."""
        key = f"market:{symbol}:current"
        return await self.redis.get(key)
    
    async def set_options_chain(
        self,
        symbol: str,
        expiration: str,
        option_type: str,
        data: Dict[str, Any],
        ttl: int = 1800
    ) -> bool:
        """Cache options chain data."""
        key = f"options:{symbol}:{expiration}:{option_type}"
        return await self.redis.set(key, data, ttl=ttl)
    
    async def get_options_chain(
        self,
        symbol: str,
        expiration: str,
        option_type: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached options chain data."""
        key = f"options:{symbol}:{expiration}:{option_type}"
        return await self.redis.get(key)
    
    async def set_correlation(
        self,
        pair: str,
        correlation: float,
        ttl: int = 300
    ) -> bool:
        """Cache correlation data."""
        key = f"correlation:{pair}"
        return await self.redis.set(key, correlation, ttl=ttl)
    
    async def get_correlation(self, pair: str) -> Optional[float]:
        """Get cached correlation data."""
        key = f"correlation:{pair}"
        value = await self.redis.get(key, deserialize=False)
        return float(value) if value is not None else None
    
    async def set_vix_data(self, vix_value: float, ttl: int = 60) -> bool:
        """Cache VIX data."""
        key = "vix:current"
        return await self.redis.set(key, vix_value, ttl=ttl)
    
    async def get_vix_data(self) -> Optional[float]:
        """Get cached VIX data."""
        key = "vix:current"
        value = await self.redis.get(key, deserialize=False)
        return float(value) if value is not None else None


# Global market data cache instance
market_data_cache = MarketDataCache(redis_manager)

