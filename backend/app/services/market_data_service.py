"""
Smart-0DTE-System Market Data Service

This module coordinates all market data processing components including
Databento integration, options processing, and intelligence engines.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from app.core.config import settings
from app.services.databento_service import databento_service
from app.services.options_service import options_service
from app.services.intelligence_service import smart_cross_ticker_engine, vix_regime_detector
from app.core.redis_client import market_data_cache
from app.core.influxdb_client import market_data_influx

logger = logging.getLogger(__name__)


class MarketDataService:
    """
    Coordinated Market Data Service
    
    Orchestrates all market data processing components and provides
    unified access to market intelligence.
    """
    
    def __init__(self):
        self.is_running = False
        self.services = {
            'databento': databento_service,
            'options': options_service,
            'cross_ticker': smart_cross_ticker_engine,
            'vix_regime': vix_regime_detector
        }
        
        # Service health status
        self.service_health = {}
        
        # Market hours tracking
        self.market_hours = {
            'pre_market_start': '04:00',
            'market_open': '09:30',
            'market_close': '16:00',
            'after_hours_end': '20:00'
        }
    
    async def initialize(self) -> None:
        """Initialize all market data services."""
        try:
            logger.info("Initializing Market Data Service...")
            
            # Initialize all sub-services
            for service_name, service in self.services.items():
                try:
                    await service.initialize()
                    self.service_health[service_name] = True
                    logger.info(f"{service_name} service initialized successfully")
                except Exception as e:
                    logger.error(f"Failed to initialize {service_name} service: {e}")
                    self.service_health[service_name] = False
            
            logger.info("Market Data Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Market Data Service: {e}")
            raise
    
    async def start_real_time_feed(self) -> None:
        """Start all real-time data processing."""
        try:
            self.is_running = True
            
            # Start all services
            await databento_service.start_real_time_feed()
            await options_service.start_options_processing()
            await smart_cross_ticker_engine.start_correlation_analysis()
            await vix_regime_detector.start_regime_detection()
            
            # Start coordination tasks
            asyncio.create_task(self._monitor_service_health())
            asyncio.create_task(self._coordinate_data_flow())
            asyncio.create_task(self._generate_market_summary())
            
            logger.info("Real-time market data feed started")
            
        except Exception as e:
            logger.error(f"Failed to start real-time feed: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop all market data services."""
        try:
            self.is_running = False
            
            # Stop all services
            await databento_service.stop_real_time_feed()
            await options_service.stop_options_processing()
            await smart_cross_ticker_engine.stop_correlation_analysis()
            await vix_regime_detector.stop_regime_detection()
            
            logger.info("Market Data Service stopped")
            
        except Exception as e:
            logger.error(f"Error stopping Market Data Service: {e}")
    
    async def _monitor_service_health(self) -> None:
        """Monitor health of all sub-services."""
        while self.is_running:
            try:
                health_status = {}
                
                for service_name, service in self.services.items():
                    try:
                        is_healthy = await service.health_check()
                        health_status[service_name] = is_healthy
                        self.service_health[service_name] = is_healthy
                    except Exception as e:
                        logger.error(f"Health check failed for {service_name}: {e}")
                        health_status[service_name] = False
                        self.service_health[service_name] = False
                
                # Cache overall health status
                overall_health = all(health_status.values())
                health_data = {
                    'overall_healthy': overall_health,
                    'services': health_status,
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                await market_data_cache.redis.set('service_health', health_data, ttl=60)
                
                # Log health issues
                unhealthy_services = [name for name, healthy in health_status.items() if not healthy]
                if unhealthy_services:
                    logger.warning(f"Unhealthy services: {unhealthy_services}")
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring service health: {e}")
                await asyncio.sleep(5)
    
    async def _coordinate_data_flow(self) -> None:
        """Coordinate data flow between services."""
        while self.is_running:
            try:
                # Check if market is open
                is_market_open = self._is_market_open()
                
                # Update market status
                market_status = {
                    'is_open': is_market_open,
                    'session': self._get_market_session(),
                    'timestamp': datetime.utcnow().isoformat()
                }
                
                await market_data_cache.redis.set('market_status', market_status, ttl=60)
                
                # Coordinate data processing based on market status
                if is_market_open:
                    await self._process_market_hours_data()
                else:
                    await self._process_after_hours_data()
                
                await asyncio.sleep(10)  # Coordinate every 10 seconds
                
            except Exception as e:
                logger.error(f"Error coordinating data flow: {e}")
                await asyncio.sleep(5)
    
    def _is_market_open(self) -> bool:
        """Check if market is currently open."""
        try:
            now = datetime.now()
            current_time = now.strftime('%H:%M')
            
            # Simple market hours check (would be more sophisticated in production)
            weekday = now.weekday()
            
            # Market closed on weekends
            if weekday >= 5:  # Saturday = 5, Sunday = 6
                return False
            
            # Check if within market hours
            market_open = self.market_hours['market_open']
            market_close = self.market_hours['market_close']
            
            return market_open <= current_time <= market_close
            
        except:
            return True  # Default to open for development
    
    def _get_market_session(self) -> str:
        """Get current market session."""
        try:
            now = datetime.now()
            current_time = now.strftime('%H:%M')
            weekday = now.weekday()
            
            if weekday >= 5:
                return 'closed'
            
            if current_time < self.market_hours['pre_market_start']:
                return 'closed'
            elif current_time < self.market_hours['market_open']:
                return 'pre_market'
            elif current_time < self.market_hours['market_close']:
                return 'regular'
            elif current_time < self.market_hours['after_hours_end']:
                return 'after_hours'
            else:
                return 'closed'
                
        except:
            return 'regular'  # Default for development
    
    async def _process_market_hours_data(self) -> None:
        """Process data during market hours."""
        try:
            # Ensure all services are running at full capacity
            # This is where we'd implement any market-hours specific logic
            pass
            
        except Exception as e:
            logger.error(f"Error processing market hours data: {e}")
    
    async def _process_after_hours_data(self) -> None:
        """Process data during after hours."""
        try:
            # Reduce processing frequency during after hours
            # This is where we'd implement any after-hours specific logic
            pass
            
        except Exception as e:
            logger.error(f"Error processing after hours data: {e}")
    
    async def _generate_market_summary(self) -> None:
        """Generate comprehensive market summary."""
        while self.is_running:
            try:
                summary = await self._create_market_summary()
                
                if summary:
                    # Cache market summary
                    await market_data_cache.redis.set('market_summary', summary, ttl=300)
                
                await asyncio.sleep(60)  # Generate summary every minute
                
            except Exception as e:
                logger.error(f"Error generating market summary: {e}")
                await asyncio.sleep(5)
    
    async def _create_market_summary(self) -> Optional[Dict[str, Any]]:
        """Create comprehensive market summary."""
        try:
            summary = {
                'timestamp': datetime.utcnow().isoformat(),
                'market_data': {},
                'options_analysis': {},
                'correlation_analysis': {},
                'regime_analysis': {},
                'cross_ticker_signals': []
            }
            
            # Get market data for all symbols
            for symbol in settings.SUPPORTED_TICKERS:
                market_data = await market_data_cache.get_market_data(symbol)
                if market_data:
                    summary['market_data'][symbol] = market_data
            
            # Get VIX data
            vix_data = await market_data_cache.get_vix_data()
            if vix_data:
                summary['market_data']['VIX'] = vix_data
            
            # Get options analysis
            for symbol in settings.SUPPORTED_TICKERS:
                options_analysis = await market_data_cache.redis.get(f'0dte_analysis:{symbol}')
                if options_analysis:
                    summary['options_analysis'][symbol] = options_analysis
            
            # Get correlation analysis
            correlation_matrix = await smart_cross_ticker_engine.get_correlation_matrix()
            summary['correlation_analysis'] = correlation_matrix
            
            # Get regime analysis
            regime_data = await vix_regime_detector.get_current_regime()
            summary['regime_analysis'] = regime_data
            
            # Get cross-ticker signals
            cross_ticker_signals = await smart_cross_ticker_engine.get_cross_ticker_signals()
            summary['cross_ticker_signals'] = cross_ticker_signals
            
            # Calculate summary statistics
            summary['statistics'] = await self._calculate_summary_statistics(summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error creating market summary: {e}")
            return None
    
    async def _calculate_summary_statistics(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate summary statistics."""
        try:
            stats = {
                'total_symbols': len(summary['market_data']),
                'active_signals': len(summary['cross_ticker_signals']),
                'avg_correlation': 0.0,
                'market_regime': summary['regime_analysis'].get('regime_type', 'unknown'),
                'vix_level': summary['regime_analysis'].get('vix_level', 0),
                'adaptation_factor': summary['regime_analysis'].get('adaptation_factor', 1.0)
            }
            
            # Calculate average correlation
            correlations = []
            for pair_data in summary['correlation_analysis'].values():
                if isinstance(pair_data, dict) and 'current' in pair_data:
                    correlations.append(pair_data['current'])
            
            if correlations:
                stats['avg_correlation'] = sum(correlations) / len(correlations)
            
            # Calculate total options volume
            total_volume = 0
            for symbol_analysis in summary['options_analysis'].values():
                if isinstance(symbol_analysis, dict):
                    total_volume += symbol_analysis.get('total_call_volume', 0)
                    total_volume += symbol_analysis.get('total_put_volume', 0)
            
            stats['total_options_volume'] = total_volume
            
            return stats
            
        except Exception as e:
            logger.error(f"Error calculating summary statistics: {e}")
            return {}
    
    # Public API methods
    
    async def get_market_data(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get market data for a specific symbol."""
        try:
            return await market_data_cache.get_market_data(symbol)
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return None
    
    async def get_options_chain(self, symbol: str) -> Dict[str, Any]:
        """Get options chain for a symbol."""
        try:
            return await options_service.get_options_chain(symbol)
        except Exception as e:
            logger.error(f"Error getting options chain for {symbol}: {e}")
            return {}
    
    async def get_correlation_matrix(self) -> Dict[str, Any]:
        """Get current correlation matrix."""
        try:
            return await smart_cross_ticker_engine.get_correlation_matrix()
        except Exception as e:
            logger.error(f"Error getting correlation matrix: {e}")
            return {}
    
    async def get_market_regime(self) -> Dict[str, Any]:
        """Get current market regime."""
        try:
            return await vix_regime_detector.get_current_regime()
        except Exception as e:
            logger.error(f"Error getting market regime: {e}")
            return {}
    
    async def get_cross_ticker_signals(self) -> List[Dict[str, Any]]:
        """Get cross-ticker signals."""
        try:
            return await smart_cross_ticker_engine.get_cross_ticker_signals()
        except Exception as e:
            logger.error(f"Error getting cross-ticker signals: {e}")
            return []
    
    async def get_market_summary(self) -> Dict[str, Any]:
        """Get comprehensive market summary."""
        try:
            summary = await market_data_cache.redis.get('market_summary')
            return summary or {}
        except Exception as e:
            logger.error(f"Error getting market summary: {e}")
            return {}
    
    async def get_service_health(self) -> Dict[str, Any]:
        """Get service health status."""
        try:
            health_data = await market_data_cache.redis.get('service_health')
            return health_data or {}
        except Exception as e:
            logger.error(f"Error getting service health: {e}")
            return {}
    
    async def get_market_status(self) -> Dict[str, Any]:
        """Get market status."""
        try:
            market_status = await market_data_cache.redis.get('market_status')
            return market_status or {}
        except Exception as e:
            logger.error(f"Error getting market status: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check overall service health."""
        try:
            if not self.is_running:
                return False
            
            # Check if all critical services are healthy
            critical_services = ['databento', 'options', 'cross_ticker', 'vix_regime']
            
            for service_name in critical_services:
                if not self.service_health.get(service_name, False):
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Market Data Service health check failed: {e}")
            return False


# Global market data service instance
market_data_service = MarketDataService()

