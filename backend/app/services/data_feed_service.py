"""
Real-time Data Feed Service for Smart-0DTE-System
Optimized for SPY, QQQ, IWM, and VIX real-time data processing

Efficient WebSocket connections and data streaming for 0DTE options trading.
"""

import asyncio
import websockets
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Callable, Any
from dataclasses import asdict
import aiohttp
import time
from concurrent.futures import ThreadPoolExecutor

from ..models.market_data import (
    Symbol, MarketDataPoint, OHLCData, OptionsData, VIXData,
    MarketDataValidator, CorrelationData
)

logger = logging.getLogger(__name__)

class DataFeedService:
    """
    Real-time market data feed service
    Handles WebSocket connections and data processing for focused ETF/VIX trading
    """
    
    def __init__(self):
        self.symbols = [Symbol.SPY, Symbol.QQQ, Symbol.IWM, Symbol.VIX]
        self.subscribers: Dict[str, List[Callable]] = {
            'market_data': [],
            'options_data': [],
            'vix_data': [],
            'correlation_data': []
        }
        self.is_running = False
        self.websocket_connections = {}
        self.data_cache = {}
        self.last_update = {}
        
    async def start(self):
        """Start the real-time data feed service"""
        logger.info("Starting ETF/VIX data feed service...")
        self.is_running = True
        
        # Start data feed tasks
        tasks = [
            self._start_market_data_feed(),
            self._start_options_data_feed(),
            self._start_vix_analysis(),
            self._start_correlation_analysis()
        ]
        
        await asyncio.gather(*tasks)
    
    async def stop(self):
        """Stop the data feed service"""
        logger.info("Stopping data feed service...")
        self.is_running = False
        
        # Close WebSocket connections
        for connection in self.websocket_connections.values():
            if connection:
                await connection.close()
    
    def subscribe(self, data_type: str, callback: Callable):
        """Subscribe to real-time data updates"""
        if data_type in self.subscribers:
            self.subscribers[data_type].append(callback)
            logger.info(f"New subscriber added for {data_type}")
    
    def unsubscribe(self, data_type: str, callback: Callable):
        """Unsubscribe from data updates"""
        if data_type in self.subscribers and callback in self.subscribers[data_type]:
            self.subscribers[data_type].remove(callback)
    
    async def _notify_subscribers(self, data_type: str, data: Any):
        """Notify all subscribers of new data"""
        for callback in self.subscribers[data_type]:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")
    
    async def _start_market_data_feed(self):
        """Start real-time market data feed for ETFs"""
        while self.is_running:
            try:
                # Simulate real-time market data (replace with actual feed)
                for symbol in [Symbol.SPY, Symbol.QQQ, Symbol.IWM]:
                    data_point = await self._fetch_market_data(symbol)
                    if data_point and MarketDataValidator.validate_price_data(data_point):
                        self.data_cache[f"{symbol.value}_market"] = data_point
                        await self._notify_subscribers('market_data', data_point)
                
                await asyncio.sleep(1)  # 1-second updates
                
            except Exception as e:
                logger.error(f"Error in market data feed: {e}")
                await asyncio.sleep(5)
    
    async def _start_options_data_feed(self):
        """Start real-time options data feed"""
        while self.is_running:
            try:
                for symbol in [Symbol.SPY, Symbol.QQQ, Symbol.IWM]:
                    options_data = await self._fetch_options_chain(symbol)
                    if options_data:
                        for option in options_data:
                            if MarketDataValidator.validate_options_data(option):
                                await self._notify_subscribers('options_data', option)
                
                await asyncio.sleep(5)  # 5-second updates for options
                
            except Exception as e:
                logger.error(f"Error in options data feed: {e}")
                await asyncio.sleep(10)
    
    async def _start_vix_analysis(self):
        """Start VIX data analysis and regime detection"""
        while self.is_running:
            try:
                vix_data = await self._fetch_vix_data()
                if vix_data:
                    self.data_cache['vix'] = vix_data
                    await self._notify_subscribers('vix_data', vix_data)
                
                await asyncio.sleep(30)  # 30-second updates for VIX
                
            except Exception as e:
                logger.error(f"Error in VIX analysis: {e}")
                await asyncio.sleep(30)
    
    async def _start_correlation_analysis(self):
        """Start correlation analysis between ETFs and VIX"""
        while self.is_running:
            try:
                correlation_data = await self._calculate_correlations()
                if correlation_data:
                    await self._notify_subscribers('correlation_data', correlation_data)
                
                await asyncio.sleep(60)  # 1-minute updates for correlations
                
            except Exception as e:
                logger.error(f"Error in correlation analysis: {e}")
                await asyncio.sleep(60)
    
    async def _fetch_market_data(self, symbol: Symbol) -> Optional[MarketDataPoint]:
        """Fetch real-time market data for a symbol"""
        try:
            # Simulate market data (replace with actual API call)
            import random
            base_prices = {
                Symbol.SPY: 485.67,
                Symbol.QQQ: 412.89,
                Symbol.IWM: 218.45
            }
            
            base_price = base_prices.get(symbol, 100.0)
            price = base_price + random.uniform(-2.0, 2.0)
            volume = random.randint(10000, 100000)
            bid = price - random.uniform(0.01, 0.05)
            ask = price + random.uniform(0.01, 0.05)
            
            return MarketDataPoint(
                symbol=symbol,
                timestamp=datetime.now(timezone.utc),
                price=round(price, 2),
                volume=volume,
                bid=round(bid, 2),
                ask=round(ask, 2)
            )
            
        except Exception as e:
            logger.error(f"Error fetching market data for {symbol}: {e}")
            return None
    
    async def _fetch_options_chain(self, symbol: Symbol) -> List[OptionsData]:
        """Fetch options chain data for a symbol"""
        try:
            # Simulate options data (replace with actual API call)
            options = []
            current_price = 485.67 if symbol == Symbol.SPY else 412.89 if symbol == Symbol.QQQ else 218.45
            
            # Generate ATM options for today's expiration
            for strike_offset in [-5, -2.5, 0, 2.5, 5]:
                strike = current_price + strike_offset
                
                for option_type in ['call', 'put']:
                    import random
                    option = OptionsData(
                        underlying_symbol=symbol,
                        timestamp=datetime.now(timezone.utc),
                        expiration=datetime.now(timezone.utc).replace(hour=16, minute=0, second=0),
                        strike=round(strike, 2),
                        option_type=option_type,
                        bid=random.uniform(0.10, 5.0),
                        ask=random.uniform(0.15, 5.5),
                        last=random.uniform(0.12, 5.2),
                        volume=random.randint(0, 1000),
                        open_interest=random.randint(0, 5000),
                        implied_volatility=random.uniform(0.15, 0.45),
                        delta=random.uniform(-1.0, 1.0),
                        gamma=random.uniform(0.0, 0.1),
                        theta=random.uniform(-0.1, 0.0),
                        vega=random.uniform(0.0, 0.5)
                    )
                    options.append(option)
            
            return options
            
        except Exception as e:
            logger.error(f"Error fetching options data for {symbol}: {e}")
            return []
    
    async def _fetch_vix_data(self) -> Optional[VIXData]:
        """Fetch VIX data and analyze volatility regime"""
        try:
            import random
            
            vix_level = random.uniform(12.0, 35.0)
            vix_change = random.uniform(-2.0, 2.0)
            vix_change_percent = (vix_change / vix_level) * 100
            
            # Determine volatility regime
            if vix_level < 15:
                regime = 'low'
            elif vix_level < 20:
                regime = 'normal'
            elif vix_level < 30:
                regime = 'elevated'
            else:
                regime = 'high'
            
            return VIXData(
                timestamp=datetime.now(timezone.utc),
                vix_level=round(vix_level, 2),
                vix_change=round(vix_change, 2),
                vix_change_percent=round(vix_change_percent, 2),
                term_structure={
                    'VIX9D': round(vix_level * 0.95, 2),
                    'VIX': round(vix_level, 2),
                    'VIX3M': round(vix_level * 1.05, 2),
                    'VIX6M': round(vix_level * 1.10, 2)
                },
                regime=regime
            )
            
        except Exception as e:
            logger.error(f"Error fetching VIX data: {e}")
            return None
    
    async def _calculate_correlations(self) -> Optional[CorrelationData]:
        """Calculate correlations between ETFs and VIX"""
        try:
            import random
            
            # Simulate correlation calculations (replace with actual calculation)
            return CorrelationData(
                timestamp=datetime.now(timezone.utc),
                spy_qqq_correlation=round(random.uniform(0.7, 0.95), 4),
                spy_iwm_correlation=round(random.uniform(0.6, 0.85), 4),
                qqq_iwm_correlation=round(random.uniform(0.5, 0.80), 4),
                spy_vix_correlation=round(random.uniform(-0.8, -0.4), 4),
                qqq_vix_correlation=round(random.uniform(-0.75, -0.35), 4),
                iwm_vix_correlation=round(random.uniform(-0.7, -0.3), 4),
                regime_change_probability=round(random.uniform(0.1, 0.9), 4)
            )
            
        except Exception as e:
            logger.error(f"Error calculating correlations: {e}")
            return None
    
    def get_latest_data(self, data_type: str, symbol: Optional[Symbol] = None) -> Optional[Any]:
        """Get the latest cached data"""
        if symbol:
            key = f"{symbol.value}_{data_type}"
        else:
            key = data_type
        
        return self.data_cache.get(key)
    
    def get_market_status(self) -> Dict[str, Any]:
        """Get current market status and data feed health"""
        return {
            'is_running': self.is_running,
            'active_connections': len(self.websocket_connections),
            'cached_data_points': len(self.data_cache),
            'last_update': self.last_update,
            'subscribers': {k: len(v) for k, v in self.subscribers.items()}
        }

class DataAggregationService:
    """
    Service for aggregating and processing market data
    Optimized for 0DTE options trading analysis
    """
    
    def __init__(self, data_feed: DataFeedService):
        self.data_feed = data_feed
        self.aggregated_data = {}
        
    async def start_aggregation(self):
        """Start data aggregation processes"""
        # Subscribe to data feeds
        self.data_feed.subscribe('market_data', self._process_market_data)
        self.data_feed.subscribe('options_data', self._process_options_data)
        self.data_feed.subscribe('vix_data', self._process_vix_data)
        
    async def _process_market_data(self, data: MarketDataPoint):
        """Process incoming market data"""
        # Update OHLC data
        await self._update_ohlc_data(data)
        
        # Calculate technical indicators
        await self._calculate_technical_indicators(data)
    
    async def _process_options_data(self, data: OptionsData):
        """Process incoming options data"""
        # Calculate options metrics
        await self._calculate_options_metrics(data)
        
        # Update options flow analysis
        await self._update_options_flow(data)
    
    async def _process_vix_data(self, data: VIXData):
        """Process VIX data for regime analysis"""
        # Update volatility regime
        await self._update_volatility_regime(data)
    
    async def _update_ohlc_data(self, data: MarketDataPoint):
        """Update OHLC data for charting"""
        # Implementation for OHLC aggregation
        pass
    
    async def _calculate_technical_indicators(self, data: MarketDataPoint):
        """Calculate technical indicators"""
        # Implementation for technical analysis
        pass
    
    async def _calculate_options_metrics(self, data: OptionsData):
        """Calculate options-specific metrics"""
        # Implementation for options analysis
        pass
    
    async def _update_options_flow(self, data: OptionsData):
        """Update options flow analysis"""
        # Implementation for flow analysis
        pass
    
    async def _update_volatility_regime(self, data: VIXData):
        """Update volatility regime analysis"""
        # Implementation for regime detection
        pass

# Global data feed service instance
data_feed_service = DataFeedService()
data_aggregation_service = DataAggregationService(data_feed_service)

