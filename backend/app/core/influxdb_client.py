"""
Smart-0DTE-System InfluxDB Client

This module handles InfluxDB connections for time-series data storage
including market data, performance metrics, and correlation data.
"""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
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


def get_influxdb() -> InfluxDBClient:
    """Get InfluxDB client instance."""
    if influxdb_client is None:
        raise RuntimeError("InfluxDB client not initialized")
    return influxdb_client


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
        self.client = get_influxdb()
        self.write_api = write_api
        self.query_api = query_api
    
    def write_point(
        self,
        measurement: str,
        tags: Dict[str, str],
        fields: Dict[str, Union[float, int, str, bool]],
        timestamp: Optional[datetime] = None
    ) -> bool:
        """
        Write a single point to InfluxDB.
        
        Args:
            measurement: Measurement name
            tags: Tag dictionary
            fields: Field dictionary
            timestamp: Point timestamp (defaults to now)
            
        Returns:
            bool: True if successful
        """
        try:
            point = Point(measurement)
            
            # Add tags
            for key, value in tags.items():
                point = point.tag(key, str(value))
            
            # Add fields
            for key, value in fields.items():
                point = point.field(key, value)
            
            # Set timestamp
            if timestamp:
                point = point.time(timestamp, WritePrecision.NS)
            
            # Write point
            self.write_api.write(
                bucket=self.bucket,
                org=self.org,
                record=point
            )
            
            return True
            
        except Exception as e:
            logger.error(f"InfluxDB write error: {e}")
            return False
    
    def write_points(self, points: List[Point]) -> bool:
        """
        Write multiple points to InfluxDB.
        
        Args:
            points: List of Point objects
            
        Returns:
            bool: True if successful
        """
        try:
            self.write_api.write(
                bucket=self.bucket,
                org=self.org,
                record=points
            )
            return True
            
        except Exception as e:
            logger.error(f"InfluxDB batch write error: {e}")
            return False
    
    def query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a Flux query.
        
        Args:
            query: Flux query string
            params: Query parameters
            
        Returns:
            List of query results
        """
        try:
            tables = self.query_api.query(query, org=self.org, params=params)
            
            results = []
            for table in tables:
                for record in table.records:
                    results.append(record.values)
            
            return results
            
        except Exception as e:
            logger.error(f"InfluxDB query error: {e}")
            return []
    
    def query_dataframe(self, query: str, params: Optional[Dict[str, Any]] = None):
        """
        Execute a Flux query and return as DataFrame.
        
        Args:
            query: Flux query string
            params: Query parameters
            
        Returns:
            pandas.DataFrame: Query results
        """
        try:
            return self.query_api.query_data_frame(query, org=self.org, params=params)
        except Exception as e:
            logger.error(f"InfluxDB DataFrame query error: {e}")
            return None
    
    async def health_check(self) -> bool:
        """
        Check InfluxDB health.
        
        Returns:
            bool: True if InfluxDB is healthy
        """
        try:
            health = self.client.health()
            return health.status == "pass"
        except Exception as e:
            logger.error(f"InfluxDB health check failed: {e}")
            return False


# Global InfluxDB manager instance
influxdb_manager = InfluxDBManager()


class MarketDataInflux:
    """Specialized InfluxDB operations for market data."""
    
    def __init__(self, influx_manager: InfluxDBManager):
        self.influx = influx_manager
    
    def write_market_data(
        self,
        symbol: str,
        price: float,
        bid: float,
        ask: float,
        volume: int,
        change_percent: float,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Write market data point."""
        return self.influx.write_point(
            measurement="market_data",
            tags={
                "symbol": symbol,
                "exchange": "ARCA"  # Default exchange
            },
            fields={
                "price": price,
                "bid": bid,
                "ask": ask,
                "volume": volume,
                "change_percent": change_percent
            },
            timestamp=timestamp
        )
    
    def write_options_data(
        self,
        symbol: str,
        underlying: str,
        option_type: str,
        strike: float,
        expiration: str,
        bid: float,
        ask: float,
        last: float,
        volume: int,
        open_interest: int,
        implied_volatility: float,
        delta: float,
        gamma: float,
        theta: float,
        vega: float,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Write options data point."""
        return self.influx.write_point(
            measurement="options_data",
            tags={
                "symbol": symbol,
                "underlying": underlying,
                "option_type": option_type,
                "strike": str(strike),
                "expiration": expiration
            },
            fields={
                "bid": bid,
                "ask": ask,
                "last": last,
                "volume": volume,
                "open_interest": open_interest,
                "implied_volatility": implied_volatility,
                "delta": delta,
                "gamma": gamma,
                "theta": theta,
                "vega": vega
            },
            timestamp=timestamp
        )
    
    def write_correlation_data(
        self,
        pair: str,
        correlation: float,
        rolling_30d: float,
        rolling_7d: float,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Write correlation data point."""
        return self.influx.write_point(
            measurement="correlations",
            tags={"pair": pair},
            fields={
                "correlation": correlation,
                "rolling_30d": rolling_30d,
                "rolling_7d": rolling_7d
            },
            timestamp=timestamp
        )
    
    def write_portfolio_performance(
        self,
        user_id: str,
        account_id: str,
        ticker: str,
        pnl: float,
        unrealized_pnl: float,
        position_count: int,
        exposure: float,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Write portfolio performance data."""
        return self.influx.write_point(
            measurement="portfolio_performance",
            tags={
                "user_id": user_id,
                "account_id": account_id,
                "ticker": ticker
            },
            fields={
                "pnl": pnl,
                "unrealized_pnl": unrealized_pnl,
                "position_count": position_count,
                "exposure": exposure
            },
            timestamp=timestamp
        )
    
    def write_risk_metrics(
        self,
        user_id: str,
        account_id: str,
        metric_type: str,
        value: float,
        threshold: float,
        severity: str,
        timestamp: Optional[datetime] = None
    ) -> bool:
        """Write risk metrics data."""
        return self.influx.write_point(
            measurement="risk_metrics",
            tags={
                "user_id": user_id,
                "account_id": account_id,
                "metric_type": metric_type,
                "severity": severity
            },
            fields={
                "value": value,
                "threshold": threshold
            },
            timestamp=timestamp
        )
    
    def get_market_data_history(
        self,
        symbol: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        interval: str = "2m"
    ) -> List[Dict[str, Any]]:
        """Get historical market data."""
        if end_time is None:
            end_time = datetime.utcnow()
        
        query = f'''
        from(bucket: "{self.influx.bucket}")
          |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
          |> filter(fn: (r) => r._measurement == "market_data")
          |> filter(fn: (r) => r.symbol == "{symbol}")
          |> aggregateWindow(every: {interval}, fn: last, createEmpty: false)
          |> yield(name: "market_data")
        '''
        
        return self.influx.query(query)
    
    def get_options_data_history(
        self,
        underlying: str,
        expiration: str,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get historical options data."""
        if end_time is None:
            end_time = datetime.utcnow()
        
        query = f'''
        from(bucket: "{self.influx.bucket}")
          |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
          |> filter(fn: (r) => r._measurement == "options_data")
          |> filter(fn: (r) => r.underlying == "{underlying}")
          |> filter(fn: (r) => r.expiration == "{expiration}")
          |> yield(name: "options_data")
        '''
        
        return self.influx.query(query)
    
    def get_correlation_history(
        self,
        pair: str,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get historical correlation data."""
        if end_time is None:
            end_time = datetime.utcnow()
        
        query = f'''
        from(bucket: "{self.influx.bucket}")
          |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
          |> filter(fn: (r) => r._measurement == "correlations")
          |> filter(fn: (r) => r.pair == "{pair}")
          |> yield(name: "correlations")
        '''
        
        return self.influx.query(query)
    
    def get_performance_metrics(
        self,
        user_id: str,
        account_id: str,
        start_time: datetime,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get performance metrics."""
        if end_time is None:
            end_time = datetime.utcnow()
        
        query = f'''
        from(bucket: "{self.influx.bucket}")
          |> range(start: {start_time.isoformat()}Z, stop: {end_time.isoformat()}Z)
          |> filter(fn: (r) => r._measurement == "portfolio_performance")
          |> filter(fn: (r) => r.user_id == "{user_id}")
          |> filter(fn: (r) => r.account_id == "{account_id}")
          |> yield(name: "performance")
        '''
        
        return self.influx.query(query)


# Global market data InfluxDB instance
market_data_influx = MarketDataInflux(influxdb_manager)

