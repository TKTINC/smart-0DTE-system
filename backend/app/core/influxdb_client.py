"""
Smart-0DTE-System InfluxDB Client

This module handles InfluxDB connections for time-series data storage
including market data, performance metrics, and correlation data.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta, timezone
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS, ASYNCHRONOUS
from influxdb_client.client.query_api import QueryApi
from influxdb_client.client.write_api import WriteApi

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global InfluxDB client
influxdb_client: Optional[InfluxDBClient] = None
write_api: Optional[WriteApi] = None
query_api: Optional[QueryApi] = None


def to_rfc3339(dt: datetime) -> str:
    """Convert datetime to RFC3339 format for InfluxDB queries."""
    return dt.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


async def init_influxdb() -> None:
    """Initialize InfluxDB connection."""
    global influxdb_client, write_api, query_api
    
    try:
        influxdb_client = InfluxDBClient(
            url=settings.INFLUXDB_URL,
            token=settings.INFLUXDB_TOKEN,
            org=settings.INFLUXDB_ORG,
            timeout=30000,
            enable_gzip=True
        )
        
        # Initialize APIs
        write_api = influxdb_client.write_api(write_options=ASYNCHRONOUS)
        query_api = influxdb_client.query_api()
        
        # Test connection
        health = influxdb_client.health()
        if health.status == "pass":
            logger.info("InfluxDB connection established successfully")
        else:
            raise Exception(f"InfluxDB health check failed: {health.message}")
            
    except Exception as e:
        logger.error(f"Failed to connect to InfluxDB: {e}")
        raise


async def close_influxdb() -> None:
    """Close InfluxDB connection."""
    global influxdb_client, write_api, query_api
    
    if influxdb_client:
        try:
            if write_api:
                write_api.close()
            influxdb_client.close()
            logger.info("InfluxDB connection closed")
        except Exception as e:
            logger.error(f"Error closing InfluxDB connection: {e}")
        finally:
            influxdb_client = None
            write_api = None
            query_api = None


def get_influxdb_client() -> InfluxDBClient:
    """Get InfluxDB client instance."""
    if influxdb_client is None:
        raise RuntimeError("InfluxDB client not initialized")
    return influxdb_client


def get_write_api() -> WriteApi:
    """Get InfluxDB write API instance."""
    if write_api is None:
        raise RuntimeError("InfluxDB write API not initialized")
    return write_api


def get_query_api() -> QueryApi:
    """Get InfluxDB query API instance."""
    if query_api is None:
        raise RuntimeError("InfluxDB query API not initialized")
    return query_api


class InfluxDBManager:
    """InfluxDB manager for handling time-series data operations."""
    
    def __init__(self):
        self.client = None
        self.write_api = None
        self.query_api = None
        self.bucket = settings.INFLUXDB_BUCKET
        self.org = settings.INFLUXDB_ORG
    
    async def initialize(self):
        """Initialize InfluxDB client."""
        self.client = get_influxdb_client()
        self.write_api = get_write_api()
        self.query_api = get_query_api()
    
    async def write_market_data(
        self,
        symbol: str,
        price: float,
        volume: int,
        timestamp: Optional[datetime] = None,
        **additional_fields
    ) -> bool:
        """
        Write market data point to InfluxDB.
        
        Args:
            symbol: Trading symbol
            price: Current price
            volume: Trading volume
            timestamp: Data timestamp (defaults to now)
            **additional_fields: Additional fields to store
            
        Returns:
            bool: True if successful
        """
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            point = Point("market_data") \
                .tag("symbol", symbol) \
                .field("price", price) \
                .field("volume", volume) \
                .time(timestamp, WritePrecision.MS)
            
            # Add additional fields
            for key, value in additional_fields.items():
                if isinstance(value, (int, float)):
                    point = point.field(key, value)
                else:
                    point = point.tag(key, str(value))
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True
            
        except Exception as e:
            logger.error(f"InfluxDB write error for {symbol}: {e}")
            return False
    
    async def write_options_data(
        self,
        underlying_symbol: str,
        strike: float,
        expiration: str,
        option_type: str,
        bid: float,
        ask: float,
        last: float,
        volume: int,
        timestamp: Optional[datetime] = None,
        **additional_fields
    ) -> bool:
        """
        Write options data point to InfluxDB.
        
        Args:
            underlying_symbol: Underlying asset symbol
            strike: Strike price
            expiration: Expiration date
            option_type: 'call' or 'put'
            bid: Bid price
            ask: Ask price
            last: Last trade price
            volume: Trading volume
            timestamp: Data timestamp (defaults to now)
            **additional_fields: Additional fields to store
            
        Returns:
            bool: True if successful
        """
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            point = Point("options_data") \
                .tag("underlying_symbol", underlying_symbol) \
                .tag("expiration", expiration) \
                .tag("option_type", option_type) \
                .field("strike", strike) \
                .field("bid", bid) \
                .field("ask", ask) \
                .field("last", last) \
                .field("volume", volume) \
                .time(timestamp, WritePrecision.MS)
            
            # Add additional fields
            for key, value in additional_fields.items():
                if isinstance(value, (int, float)):
                    point = point.field(key, value)
                else:
                    point = point.tag(key, str(value))
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True
            
        except Exception as e:
            logger.error(f"InfluxDB options write error for {underlying_symbol}: {e}")
            return False
    
    async def write_vix_data(
        self,
        vix_level: float,
        vix_change: float,
        regime: str,
        timestamp: Optional[datetime] = None,
        **additional_fields
    ) -> bool:
        """
        Write VIX data point to InfluxDB.
        
        Args:
            vix_level: Current VIX level
            vix_change: Change from previous close
            regime: Volatility regime (low, medium, high)
            timestamp: Data timestamp (defaults to now)
            **additional_fields: Additional fields to store
            
        Returns:
            bool: True if successful
        """
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            point = Point("vix_data") \
                .tag("regime", regime) \
                .field("vix_level", vix_level) \
                .field("vix_change", vix_change) \
                .time(timestamp, WritePrecision.MS)
            
            # Add additional fields
            for key, value in additional_fields.items():
                if isinstance(value, (int, float)):
                    point = point.field(key, value)
                else:
                    point = point.tag(key, str(value))
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True
            
        except Exception as e:
            logger.error(f"InfluxDB VIX write error: {e}")
            return False
    
    async def write_correlation_data(
        self,
        symbol1: str,
        symbol2: str,
        correlation: float,
        window_size: int,
        timestamp: Optional[datetime] = None,
        **additional_fields
    ) -> bool:
        """
        Write correlation data point to InfluxDB.
        
        Args:
            symbol1: First symbol
            symbol2: Second symbol
            correlation: Correlation coefficient
            window_size: Rolling window size used for calculation
            timestamp: Data timestamp (defaults to now)
            **additional_fields: Additional fields to store
            
        Returns:
            bool: True if successful
        """
        try:
            if timestamp is None:
                timestamp = datetime.utcnow()
            
            point = Point("correlation_data") \
                .tag("symbol1", symbol1) \
                .tag("symbol2", symbol2) \
                .field("correlation", correlation) \
                .field("window_size", window_size) \
                .time(timestamp, WritePrecision.MS)
            
            # Add additional fields
            for key, value in additional_fields.items():
                if isinstance(value, (int, float)):
                    point = point.field(key, value)
                else:
                    point = point.tag(key, str(value))
            
            self.write_api.write(bucket=self.bucket, org=self.org, record=point)
            return True
            
        except Exception as e:
            logger.error(f"InfluxDB correlation write error for {symbol1}-{symbol2}: {e}")
            return False
    
    async def query_market_data(
        self,
        symbol: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        interval: str = "1m"
    ) -> List[Dict[str, Any]]:
        """
        Query market data from InfluxDB.
        
        Args:
            symbol: Trading symbol
            start_time: Start time for query
            end_time: End time for query (defaults to now)
            interval: Aggregation interval
            
        Returns:
            List of market data points
        """
        try:
            if end_time is None:
                end_time = datetime.utcnow()
            
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {to_rfc3339(start_time)}, stop: {to_rfc3339(end_time)})
              |> filter(fn: (r) => r._measurement == "market_data")
              |> filter(fn: (r) => r.symbol == "{symbol}")
              |> aggregateWindow(every: {interval}, fn: last, createEmpty: false)
              |> yield(name: "market_data")
            '''
            
            result = self.query_api.query(query, org=self.org)
            
            data_points = []
            for table in result:
                for record in table.records:
                    data_points.append({
                        'time': record.get_time(),
                        'symbol': record.values.get('symbol'),
                        'price': record.get_value(),
                        'field': record.get_field()
                    })
            
            return data_points
            
        except Exception as e:
            logger.error(f"InfluxDB query error for {symbol}: {e}")
            return []
    
    async def query_options_data(
        self,
        underlying_symbol: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        expiration: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Query options data from InfluxDB.
        
        Args:
            underlying_symbol: Underlying asset symbol
            start_time: Start time for query
            end_time: End time for query (defaults to now)
            expiration: Optional expiration filter
            
        Returns:
            List of options data points
        """
        try:
            if end_time is None:
                end_time = datetime.utcnow()
            
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {to_rfc3339(start_time)}, stop: {to_rfc3339(end_time)})
              |> filter(fn: (r) => r._measurement == "options_data")
              |> filter(fn: (r) => r.underlying_symbol == "{underlying_symbol}")
            '''
            
            if expiration:
                query += f'  |> filter(fn: (r) => r.expiration == "{expiration}")\n'
            
            query += '  |> yield(name: "options_data")'
            
            result = self.query_api.query(query, org=self.org)
            
            data_points = []
            for table in result:
                for record in table.records:
                    data_points.append({
                        'time': record.get_time(),
                        'underlying_symbol': record.values.get('underlying_symbol'),
                        'expiration': record.values.get('expiration'),
                        'option_type': record.values.get('option_type'),
                        'strike': record.values.get('strike'),
                        'value': record.get_value(),
                        'field': record.get_field()
                    })
            
            return data_points
            
        except Exception as e:
            logger.error(f"InfluxDB options query error for {underlying_symbol}: {e}")
            return []
    
    async def query_vix_data(
        self,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        interval: str = "1m"
    ) -> List[Dict[str, Any]]:
        """
        Query VIX data from InfluxDB.
        
        Args:
            start_time: Start time for query
            end_time: End time for query (defaults to now)
            interval: Aggregation interval
            
        Returns:
            List of VIX data points
        """
        try:
            if end_time is None:
                end_time = datetime.utcnow()
            
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {to_rfc3339(start_time)}, stop: {to_rfc3339(end_time)})
              |> filter(fn: (r) => r._measurement == "vix_data")
              |> aggregateWindow(every: {interval}, fn: last, createEmpty: false)
              |> yield(name: "vix_data")
            '''
            
            result = self.query_api.query(query, org=self.org)
            
            data_points = []
            for table in result:
                for record in table.records:
                    data_points.append({
                        'time': record.get_time(),
                        'regime': record.values.get('regime'),
                        'value': record.get_value(),
                        'field': record.get_field()
                    })
            
            return data_points
            
        except Exception as e:
            logger.error(f"InfluxDB VIX query error: {e}")
            return []
    
    async def query_correlation_data(
        self,
        symbol1: str,
        symbol2: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        interval: str = "1h"
    ) -> List[Dict[str, Any]]:
        """
        Query correlation data from InfluxDB.
        
        Args:
            symbol1: First symbol
            symbol2: Second symbol
            start_time: Start time for query
            end_time: End time for query (defaults to now)
            interval: Aggregation interval
            
        Returns:
            List of correlation data points
        """
        try:
            if end_time is None:
                end_time = datetime.utcnow()
            
            query = f'''
            from(bucket: "{self.bucket}")
              |> range(start: {to_rfc3339(start_time)}, stop: {to_rfc3339(end_time)})
              |> filter(fn: (r) => r._measurement == "correlation_data")
              |> filter(fn: (r) => r.symbol1 == "{symbol1}" and r.symbol2 == "{symbol2}")
              |> aggregateWindow(every: {interval}, fn: last, createEmpty: false)
              |> yield(name: "correlation_data")
            '''
            
            result = self.query_api.query(query, org=self.org)
            
            data_points = []
            for table in result:
                for record in table.records:
                    data_points.append({
                        'time': record.get_time(),
                        'symbol1': record.values.get('symbol1'),
                        'symbol2': record.values.get('symbol2'),
                        'correlation': record.get_value(),
                        'window_size': record.values.get('window_size')
                    })
            
            return data_points
            
        except Exception as e:
            logger.error(f"InfluxDB correlation query error for {symbol1}-{symbol2}: {e}")
            return []


# Global manager instance
influx_manager = InfluxDBManager()

