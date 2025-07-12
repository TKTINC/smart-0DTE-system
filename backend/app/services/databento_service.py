"""
Smart-0DTE-System Databento Integration Service

This module handles real-time market data streaming from Databento
for SPY, QQQ, and IWM tickers and their options chains.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Callable, Any
from decimal import Decimal
import json

import databento as db
from databento import DBNStore
from databento.common.enums import Dataset, Schema, SType
from databento.live.session import LiveSession

from app.core.config import settings
from app.core.redis_client import market_data_cache
from app.core.influxdb_client import market_data_influx
from app.models.market_data_models import MarketDataSnapshot, OptionsChain, VIXData
from app.core.database import db_manager

logger = logging.getLogger(__name__)


class DatabentoService:
    """Service for handling Databento real-time market data."""
    
    def __init__(self):
        self.client = None
        self.live_session: Optional[LiveSession] = None
        self.is_running = False
        self.subscriptions = {}
        self.callbacks = {}
        self.supported_symbols = settings.SUPPORTED_TICKERS
        self.vix_symbol = "VIX"
        
        # Data handlers
        self.data_handlers = {
            Schema.TRADES: self._handle_trade_data,
            Schema.MBO: self._handle_order_book_data,
            Schema.TBBO: self._handle_quote_data,
            Schema.OHLCV_1M: self._handle_ohlcv_data,
        }
    
    async def initialize(self) -> None:
        """Initialize Databento client and connection."""
        try:
            if not settings.DATABENTO_API_KEY:
                logger.warning("Databento API key not configured, using mock data")
                return
            
            # Initialize Databento client
            self.client = db.Historical(key=settings.DATABENTO_API_KEY)
            
            # Initialize live session for real-time data
            self.live_session = db.Live(
                key=settings.DATABENTO_API_KEY,
                dataset=Dataset.XNAS_ITCH,  # NASDAQ dataset
                upgrade_policy=db.UpgradePolicy.UPGRADE
            )
            
            logger.info("Databento service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Databento service: {e}")
            raise
    
    async def start_real_time_feed(self) -> None:
        """Start real-time market data feed."""
        if not self.live_session:
            logger.warning("Databento not configured, starting mock data feed")
            await self._start_mock_feed()
            return
        
        try:
            self.is_running = True
            
            # Subscribe to market data for supported symbols
            await self._subscribe_to_symbols()
            
            # Start data processing loop
            asyncio.create_task(self._process_real_time_data())
            
            logger.info("Real-time market data feed started")
            
        except Exception as e:
            logger.error(f"Failed to start real-time feed: {e}")
            self.is_running = False
            raise
    
    async def stop_real_time_feed(self) -> None:
        """Stop real-time market data feed."""
        try:
            self.is_running = False
            
            if self.live_session:
                await self.live_session.stop()
            
            logger.info("Real-time market data feed stopped")
            
        except Exception as e:
            logger.error(f"Error stopping real-time feed: {e}")
    
    async def _subscribe_to_symbols(self) -> None:
        """Subscribe to market data for supported symbols."""
        try:
            # Subscribe to equity data
            symbols = self.supported_symbols + [self.vix_symbol]
            
            await self.live_session.subscribe(
                dataset=Dataset.XNAS_ITCH,
                schema=Schema.TRADES,
                stype_in=SType.RAW_SYMBOL,
                symbols=symbols
            )
            
            await self.live_session.subscribe(
                dataset=Dataset.XNAS_ITCH,
                schema=Schema.TBBO,
                stype_in=SType.RAW_SYMBOL,
                symbols=symbols
            )
            
            # Subscribe to options data for 0DTE options
            await self._subscribe_to_options()
            
            logger.info(f"Subscribed to market data for symbols: {symbols}")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to symbols: {e}")
            raise
    
    async def _subscribe_to_options(self) -> None:
        """Subscribe to options data for 0DTE options."""
        try:
            today = date.today()
            
            for symbol in self.supported_symbols:
                # Get options symbols for today's expiration
                options_symbols = await self._get_0dte_options_symbols(symbol, today)
                
                if options_symbols:
                    await self.live_session.subscribe(
                        dataset=Dataset.OPRA_PILLAR,
                        schema=Schema.TRADES,
                        stype_in=SType.RAW_SYMBOL,
                        symbols=options_symbols
                    )
                    
                    await self.live_session.subscribe(
                        dataset=Dataset.OPRA_PILLAR,
                        schema=Schema.TBBO,
                        stype_in=SType.RAW_SYMBOL,
                        symbols=options_symbols
                    )
            
            logger.info("Subscribed to 0DTE options data")
            
        except Exception as e:
            logger.error(f"Failed to subscribe to options: {e}")
    
    async def _get_0dte_options_symbols(self, underlying: str, expiration: date) -> List[str]:
        """Get options symbols for 0DTE options."""
        try:
            # This would typically query Databento for available options
            # For now, we'll generate common strike ranges
            
            # Get current underlying price (mock for now)
            current_price = await self._get_current_price(underlying)
            if not current_price:
                return []
            
            # Generate strikes around ATM (±10 strikes)
            strikes = []
            base_strike = round(current_price)
            
            for i in range(-10, 11):
                strikes.append(base_strike + i)
            
            # Generate options symbols
            exp_str = expiration.strftime("%y%m%d")
            options_symbols = []
            
            for strike in strikes:
                # Call option
                call_symbol = f"{underlying}{exp_str}C{strike:08.0f}"
                options_symbols.append(call_symbol)
                
                # Put option
                put_symbol = f"{underlying}{exp_str}P{strike:08.0f}"
                options_symbols.append(put_symbol)
            
            return options_symbols
            
        except Exception as e:
            logger.error(f"Failed to get options symbols for {underlying}: {e}")
            return []
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol."""
        try:
            # Try to get from cache first
            cached_data = await market_data_cache.get_market_data(symbol)
            if cached_data and 'price' in cached_data:
                return float(cached_data['price'])
            
            # Mock prices for development
            mock_prices = {
                'SPY': 445.67,
                'QQQ': 378.45,
                'IWM': 198.23,
                'VIX': 18.5
            }
            
            return mock_prices.get(symbol)
            
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
            return None
    
    async def _process_real_time_data(self) -> None:
        """Process incoming real-time data."""
        try:
            async for record in self.live_session:
                if not self.is_running:
                    break
                
                # Route data to appropriate handler
                schema = record.schema
                if schema in self.data_handlers:
                    await self.data_handlers[schema](record)
                
        except Exception as e:
            logger.error(f"Error processing real-time data: {e}")
    
    async def _handle_trade_data(self, record) -> None:
        """Handle trade data records."""
        try:
            symbol = record.instrument_id
            price = record.price / 1e9  # Convert from fixed-point
            size = record.size
            timestamp = datetime.fromtimestamp(record.ts_event / 1e9)
            
            # Update market data
            await self._update_market_data(symbol, {
                'price': price,
                'volume': size,
                'timestamp': timestamp
            })
            
        except Exception as e:
            logger.error(f"Error handling trade data: {e}")
    
    async def _handle_quote_data(self, record) -> None:
        """Handle quote (bid/ask) data records."""
        try:
            symbol = record.instrument_id
            bid_price = record.bid_px / 1e9 if record.bid_px else None
            ask_price = record.ask_px / 1e9 if record.ask_px else None
            bid_size = record.bid_sz if record.bid_sz else None
            ask_size = record.ask_sz if record.ask_sz else None
            timestamp = datetime.fromtimestamp(record.ts_event / 1e9)
            
            # Update market data
            await self._update_market_data(symbol, {
                'bid': bid_price,
                'ask': ask_price,
                'bid_size': bid_size,
                'ask_size': ask_size,
                'timestamp': timestamp
            })
            
        except Exception as e:
            logger.error(f"Error handling quote data: {e}")
    
    async def _handle_order_book_data(self, record) -> None:
        """Handle order book data records."""
        try:
            # Process order book updates for detailed market microstructure
            symbol = record.instrument_id
            timestamp = datetime.fromtimestamp(record.ts_event / 1e9)
            
            # For now, we'll just log order book updates
            logger.debug(f"Order book update for {symbol} at {timestamp}")
            
        except Exception as e:
            logger.error(f"Error handling order book data: {e}")
    
    async def _handle_ohlcv_data(self, record) -> None:
        """Handle OHLCV (candlestick) data records."""
        try:
            symbol = record.instrument_id
            open_price = record.open / 1e9
            high_price = record.high / 1e9
            low_price = record.low / 1e9
            close_price = record.close / 1e9
            volume = record.volume
            timestamp = datetime.fromtimestamp(record.ts_event / 1e9)
            
            # Update market data with OHLCV
            await self._update_market_data(symbol, {
                'price': close_price,
                'open': open_price,
                'high': high_price,
                'low': low_price,
                'volume': volume,
                'timestamp': timestamp
            })
            
        except Exception as e:
            logger.error(f"Error handling OHLCV data: {e}")
    
    async def _update_market_data(self, symbol: str, data: Dict[str, Any]) -> None:
        """Update market data in cache and database."""
        try:
            # Determine if this is an equity or option
            if symbol in self.supported_symbols or symbol == self.vix_symbol:
                await self._update_equity_data(symbol, data)
            else:
                await self._update_options_data(symbol, data)
                
        except Exception as e:
            logger.error(f"Error updating market data for {symbol}: {e}")
    
    async def _update_equity_data(self, symbol: str, data: Dict[str, Any]) -> None:
        """Update equity market data."""
        try:
            # Get existing data from cache
            existing_data = await market_data_cache.get_market_data(symbol) or {}
            
            # Merge new data
            existing_data.update(data)
            
            # Calculate change if we have previous close
            if 'price' in data and 'previous_close' in existing_data:
                price = data['price']
                prev_close = existing_data['previous_close']
                change = price - prev_close
                change_percent = (change / prev_close) * 100 if prev_close > 0 else 0
                
                existing_data.update({
                    'change': change,
                    'change_percent': change_percent
                })
            
            # Update cache
            await market_data_cache.set_market_data(symbol, existing_data)
            
            # Write to InfluxDB
            if 'price' in data:
                market_data_influx.write_market_data(
                    symbol=symbol,
                    price=data['price'],
                    bid=data.get('bid', 0),
                    ask=data.get('ask', 0),
                    volume=data.get('volume', 0),
                    change_percent=existing_data.get('change_percent', 0),
                    timestamp=data.get('timestamp')
                )
            
            # Handle VIX data specially
            if symbol == self.vix_symbol:
                await self._update_vix_data(data)
            
        except Exception as e:
            logger.error(f"Error updating equity data for {symbol}: {e}")
    
    async def _update_options_data(self, symbol: str, data: Dict[str, Any]) -> None:
        """Update options market data."""
        try:
            # Parse options symbol to extract components
            option_info = self._parse_options_symbol(symbol)
            if not option_info:
                return
            
            # Update options cache
            cache_key = f"options:{option_info['underlying']}:{option_info['expiration']}:{option_info['type']}"
            existing_options = await market_data_cache.redis.get(cache_key) or {}
            
            strike_key = str(option_info['strike'])
            if strike_key not in existing_options:
                existing_options[strike_key] = {}
            
            existing_options[strike_key].update(data)
            
            # Update cache
            await market_data_cache.redis.set(cache_key, existing_options, ttl=1800)
            
            # Write to InfluxDB
            if 'price' in data:
                market_data_influx.write_options_data(
                    symbol=symbol,
                    underlying=option_info['underlying'],
                    option_type=option_info['type'],
                    strike=option_info['strike'],
                    expiration=option_info['expiration'],
                    bid=data.get('bid', 0),
                    ask=data.get('ask', 0),
                    last=data['price'],
                    volume=data.get('volume', 0),
                    open_interest=0,  # Would need separate data feed
                    implied_volatility=0,  # Would need calculation
                    delta=0,  # Would need calculation
                    gamma=0,  # Would need calculation
                    theta=0,  # Would need calculation
                    vega=0,  # Would need calculation
                    timestamp=data.get('timestamp')
                )
            
        except Exception as e:
            logger.error(f"Error updating options data for {symbol}: {e}")
    
    def _parse_options_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Parse options symbol to extract underlying, expiration, type, and strike."""
        try:
            # Example: SPY240115C445000
            # Format: [UNDERLYING][YYMMDD][C/P][STRIKE*1000]
            
            if len(symbol) < 15:
                return None
            
            # Extract underlying (first 3 characters for SPY, QQQ, IWM)
            underlying = symbol[:3]
            if underlying not in self.supported_symbols:
                return None
            
            # Extract expiration (next 6 characters)
            exp_str = symbol[3:9]
            exp_date = datetime.strptime(f"20{exp_str}", "%Y%m%d").date()
            
            # Extract option type (next character)
            option_type = symbol[9].lower()
            if option_type not in ['c', 'p']:
                return None
            
            option_type = 'call' if option_type == 'c' else 'put'
            
            # Extract strike (remaining characters, divide by 1000)
            strike_str = symbol[10:]
            strike = float(strike_str) / 1000
            
            return {
                'underlying': underlying,
                'expiration': exp_date.strftime('%Y-%m-%d'),
                'type': option_type,
                'strike': strike
            }
            
        except Exception as e:
            logger.error(f"Error parsing options symbol {symbol}: {e}")
            return None
    
    async def _update_vix_data(self, data: Dict[str, Any]) -> None:
        """Update VIX data and regime detection."""
        try:
            vix_value = data.get('price')
            if not vix_value:
                return
            
            # Cache VIX data
            await market_data_cache.set_vix_data(vix_value)
            
            # Determine regime type
            if vix_value < 15:
                regime_type = 'low'
            elif vix_value <= 25:
                regime_type = 'normal'
            elif vix_value <= 35:
                regime_type = 'high'
            else:
                regime_type = 'extreme'
            
            # Cache regime data
            regime_data = {
                'type': regime_type,
                'vix_level': vix_value,
                'adaptation_factor': self._calculate_adaptation_factor(vix_value),
                'timestamp': data.get('timestamp', datetime.utcnow()).isoformat()
            }
            
            await market_data_cache.redis.set('regime:current', regime_data, ttl=300)
            
        except Exception as e:
            logger.error(f"Error updating VIX data: {e}")
    
    def _calculate_adaptation_factor(self, vix_value: float) -> float:
        """Calculate risk adaptation factor based on VIX level."""
        if vix_value < 15:
            return 1.2  # Increase position size in low vol
        elif vix_value <= 25:
            return 1.0  # Normal position size
        elif vix_value <= 35:
            return 0.7  # Reduce position size in high vol
        else:
            return 0.5  # Significantly reduce in extreme vol
    
    async def _start_mock_feed(self) -> None:
        """Start mock data feed for development/testing."""
        try:
            self.is_running = True
            
            # Start mock data generation
            asyncio.create_task(self._generate_mock_data())
            
            logger.info("Mock market data feed started")
            
        except Exception as e:
            logger.error(f"Failed to start mock feed: {e}")
    
    async def _generate_mock_data(self) -> None:
        """Generate mock market data for development."""
        import random
        
        base_prices = {
            'SPY': 445.67,
            'QQQ': 378.45,
            'IWM': 198.23,
            'VIX': 18.5
        }
        
        while self.is_running:
            try:
                for symbol, base_price in base_prices.items():
                    # Generate random price movement
                    change_percent = random.uniform(-0.5, 0.5)
                    new_price = base_price * (1 + change_percent / 100)
                    
                    # Generate bid/ask spread
                    spread = new_price * 0.001  # 0.1% spread
                    bid = new_price - spread / 2
                    ask = new_price + spread / 2
                    
                    # Generate volume
                    volume = random.randint(1000, 10000)
                    
                    data = {
                        'price': new_price,
                        'bid': bid,
                        'ask': ask,
                        'volume': volume,
                        'timestamp': datetime.utcnow()
                    }
                    
                    await self._update_market_data(symbol, data)
                    
                    # Update base price for next iteration
                    base_prices[symbol] = new_price
                
                # Wait before next update
                await asyncio.sleep(settings.MARKET_DATA_REFRESH_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error generating mock data: {e}")
                await asyncio.sleep(5)
    
    async def get_historical_data(
        self,
        symbol: str,
        start_date: date,
        end_date: Optional[date] = None,
        schema: Schema = Schema.TRADES
    ) -> List[Dict[str, Any]]:
        """Get historical market data."""
        try:
            if not self.client:
                logger.warning("Databento client not available for historical data")
                return []
            
            if end_date is None:
                end_date = date.today()
            
            # Query historical data
            data = self.client.timeseries.get_range(
                dataset=Dataset.XNAS_ITCH,
                schema=schema,
                start=start_date,
                end=end_date,
                symbols=[symbol],
                stype_in=SType.RAW_SYMBOL
            )
            
            # Convert to list of dictionaries
            results = []
            for record in data:
                results.append({
                    'symbol': record.instrument_id,
                    'timestamp': datetime.fromtimestamp(record.ts_event / 1e9),
                    'price': record.price / 1e9 if hasattr(record, 'price') else None,
                    'size': record.size if hasattr(record, 'size') else None,
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting historical data for {symbol}: {e}")
            return []
    
    async def health_check(self) -> bool:
        """Check service health."""
        try:
            if not self.is_running:
                return False
            
            # Check if we're receiving data
            for symbol in self.supported_symbols:
                data = await market_data_cache.get_market_data(symbol)
                if data and 'timestamp' in data:
                    last_update = datetime.fromisoformat(data['timestamp'])
                    if (datetime.utcnow() - last_update).seconds > 60:
                        logger.warning(f"Stale data for {symbol}")
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


# Global Databento service instance
databento_service = DatabentoService()

