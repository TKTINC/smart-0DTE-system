"""
Smart-0DTE-System Options Chain Processing Service

This module handles options chain data processing, including
0DTE options tracking, Greeks calculation, and strike analysis.
"""

import asyncio
import logging
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
import math

import numpy as np
from scipy.stats import norm
from scipy.optimize import brentq

from app.core.config import settings
from app.core.redis_client import market_data_cache
from app.core.influxdb_client import market_data_influx
from app.models.market_data_models import OptionsChain, Ticker
from app.core.database import db_manager
from app.services.databento_service import databento_service

logger = logging.getLogger(__name__)


class OptionsService:
    """Service for processing options chain data and calculations."""
    
    def __init__(self):
        self.supported_symbols = settings.SUPPORTED_TICKERS
        self.risk_free_rate = 0.05  # 5% risk-free rate (would be dynamic in production)
        self.is_running = False
        
        # Options chain cache
        self.options_chains = {}
        self.last_update = {}
    
    async def initialize(self) -> None:
        """Initialize options service."""
        try:
            logger.info("Options service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize options service: {e}")
            raise
    
    async def start_options_processing(self) -> None:
        """Start options chain processing."""
        try:
            self.is_running = True
            
            # Start background tasks
            asyncio.create_task(self._process_options_chains())
            asyncio.create_task(self._calculate_greeks())
            asyncio.create_task(self._analyze_0dte_options())
            
            logger.info("Options processing started")
            
        except Exception as e:
            logger.error(f"Failed to start options processing: {e}")
            raise
    
    async def stop_options_processing(self) -> None:
        """Stop options processing."""
        try:
            self.is_running = False
            logger.info("Options processing stopped")
        except Exception as e:
            logger.error(f"Error stopping options processing: {e}")
    
    async def _process_options_chains(self) -> None:
        """Process options chains for all supported symbols."""
        while self.is_running:
            try:
                for symbol in self.supported_symbols:
                    await self._update_options_chain(symbol)
                
                # Wait before next update
                await asyncio.sleep(settings.OPTIONS_CHAIN_REFRESH_INTERVAL)
                
            except Exception as e:
                logger.error(f"Error processing options chains: {e}")
                await asyncio.sleep(5)
    
    async def _update_options_chain(self, symbol: str) -> None:
        """Update options chain for a specific symbol."""
        try:
            # Get current underlying price
            market_data = await market_data_cache.get_market_data(symbol)
            if not market_data or 'price' not in market_data:
                return
            
            underlying_price = float(market_data['price'])
            
            # Get 0DTE expiration date
            today = date.today()
            
            # Generate strike range around ATM
            strikes = self._generate_strike_range(underlying_price)
            
            # Process calls and puts
            for option_type in ['call', 'put']:
                options_data = {}
                
                for strike in strikes:
                    # Get cached options data
                    cached_option = await self._get_cached_option_data(
                        symbol, today, option_type, strike
                    )
                    
                    if cached_option:
                        # Calculate theoretical values and Greeks
                        option_data = await self._calculate_option_metrics(
                            underlying_price, strike, 0, option_type, cached_option
                        )
                        
                        options_data[str(strike)] = option_data
                
                # Cache the complete options chain
                await market_data_cache.set_options_chain(
                    symbol, today.strftime('%Y-%m-%d'), option_type, options_data
                )
            
            self.last_update[symbol] = datetime.utcnow()
            
        except Exception as e:
            logger.error(f"Error updating options chain for {symbol}: {e}")
    
    def _generate_strike_range(self, underlying_price: float, num_strikes: int = 10) -> List[float]:
        """Generate strike range around ATM."""
        try:
            # Round to nearest dollar for strike spacing
            atm_strike = round(underlying_price)
            
            strikes = []
            for i in range(-num_strikes, num_strikes + 1):
                strikes.append(atm_strike + i)
            
            return sorted(strikes)
            
        except Exception as e:
            logger.error(f"Error generating strike range: {e}")
            return []
    
    async def _get_cached_option_data(
        self,
        underlying: str,
        expiration: date,
        option_type: str,
        strike: float
    ) -> Optional[Dict[str, Any]]:
        """Get cached option data."""
        try:
            # Try to get from options chain cache
            options_chain = await market_data_cache.get_options_chain(
                underlying, expiration.strftime('%Y-%m-%d'), option_type
            )
            
            if options_chain and str(strike) in options_chain:
                return options_chain[str(strike)]
            
            # Generate mock data for development
            return self._generate_mock_option_data(underlying, strike, option_type)
            
        except Exception as e:
            logger.error(f"Error getting cached option data: {e}")
            return None
    
    def _generate_mock_option_data(
        self,
        underlying: str,
        strike: float,
        option_type: str
    ) -> Dict[str, Any]:
        """Generate mock option data for development."""
        try:
            import random
            
            # Get underlying price
            base_prices = {'SPY': 445.67, 'QQQ': 378.45, 'IWM': 198.23}
            underlying_price = base_prices.get(underlying, 400.0)
            
            # Calculate rough intrinsic value
            if option_type == 'call':
                intrinsic = max(0, underlying_price - strike)
            else:
                intrinsic = max(0, strike - underlying_price)
            
            # Add time value (small for 0DTE)
            time_value = random.uniform(0.05, 0.50)
            theoretical_price = intrinsic + time_value
            
            # Generate bid/ask around theoretical
            spread = theoretical_price * 0.02  # 2% spread
            bid = max(0.01, theoretical_price - spread / 2)
            ask = theoretical_price + spread / 2
            
            return {
                'bid': bid,
                'ask': ask,
                'last': theoretical_price,
                'volume': random.randint(0, 1000),
                'open_interest': random.randint(0, 5000),
                'timestamp': datetime.utcnow()
            }
            
        except Exception as e:
            logger.error(f"Error generating mock option data: {e}")
            return {}
    
    async def _calculate_option_metrics(
        self,
        underlying_price: float,
        strike: float,
        time_to_expiry: float,
        option_type: str,
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate option metrics including Greeks."""
        try:
            # Get market prices
            bid = market_data.get('bid', 0)
            ask = market_data.get('ask', 0)
            last = market_data.get('last', 0)
            
            # Calculate mid price
            mid_price = (bid + ask) / 2 if bid > 0 and ask > 0 else last
            
            # Calculate implied volatility
            if mid_price > 0 and time_to_expiry > 0:
                try:
                    iv = self._calculate_implied_volatility(
                        underlying_price, strike, time_to_expiry, 
                        self.risk_free_rate, mid_price, option_type
                    )
                except:
                    iv = 0.20  # Default to 20% IV if calculation fails
            else:
                iv = 0.20
            
            # Calculate Greeks
            greeks = self._calculate_greeks(
                underlying_price, strike, time_to_expiry, 
                self.risk_free_rate, iv, option_type
            )
            
            # Calculate additional metrics
            intrinsic_value = self._calculate_intrinsic_value(
                underlying_price, strike, option_type
            )
            
            time_value = max(0, mid_price - intrinsic_value)
            
            # Moneyness
            moneyness = underlying_price / strike if strike > 0 else 0
            
            # Distance from ATM
            distance_from_atm = abs(underlying_price - strike)
            
            return {
                **market_data,
                'mid_price': mid_price,
                'implied_volatility': iv,
                'intrinsic_value': intrinsic_value,
                'time_value': time_value,
                'moneyness': moneyness,
                'distance_from_atm': distance_from_atm,
                **greeks
            }
            
        except Exception as e:
            logger.error(f"Error calculating option metrics: {e}")
            return market_data
    
    def _calculate_implied_volatility(
        self,
        S: float,  # Underlying price
        K: float,  # Strike price
        T: float,  # Time to expiry
        r: float,  # Risk-free rate
        market_price: float,  # Market price of option
        option_type: str
    ) -> float:
        """Calculate implied volatility using Brent's method."""
        try:
            def objective_function(vol):
                theoretical_price = self._black_scholes_price(S, K, T, r, vol, option_type)
                return theoretical_price - market_price
            
            # Use Brent's method to find IV
            iv = brentq(objective_function, 0.001, 5.0, xtol=1e-6, maxiter=100)
            return max(0.001, min(5.0, iv))  # Clamp between 0.1% and 500%
            
        except Exception:
            return 0.20  # Default to 20% if calculation fails
    
    def _black_scholes_price(
        self,
        S: float,  # Underlying price
        K: float,  # Strike price
        T: float,  # Time to expiry
        r: float,  # Risk-free rate
        sigma: float,  # Volatility
        option_type: str
    ) -> float:
        """Calculate Black-Scholes option price."""
        try:
            if T <= 0:
                # For 0DTE at expiry, return intrinsic value
                if option_type == 'call':
                    return max(0, S - K)
                else:
                    return max(0, K - S)
            
            d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            
            if option_type == 'call':
                price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
            else:
                price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)
            
            return max(0, price)
            
        except Exception as e:
            logger.error(f"Error calculating Black-Scholes price: {e}")
            return 0
    
    def _calculate_greeks(
        self,
        S: float,  # Underlying price
        K: float,  # Strike price
        T: float,  # Time to expiry
        r: float,  # Risk-free rate
        sigma: float,  # Volatility
        option_type: str
    ) -> Dict[str, float]:
        """Calculate option Greeks."""
        try:
            if T <= 0:
                # For expired options, most Greeks are 0
                return {
                    'delta': 1.0 if (option_type == 'call' and S > K) or (option_type == 'put' and S < K) else 0.0,
                    'gamma': 0.0,
                    'theta': 0.0,
                    'vega': 0.0,
                    'rho': 0.0
                }
            
            d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))
            d2 = d1 - sigma * math.sqrt(T)
            
            # Delta
            if option_type == 'call':
                delta = norm.cdf(d1)
            else:
                delta = norm.cdf(d1) - 1
            
            # Gamma
            gamma = norm.pdf(d1) / (S * sigma * math.sqrt(T))
            
            # Theta
            theta_part1 = -(S * norm.pdf(d1) * sigma) / (2 * math.sqrt(T))
            if option_type == 'call':
                theta_part2 = -r * K * math.exp(-r * T) * norm.cdf(d2)
                theta = (theta_part1 + theta_part2) / 365  # Per day
            else:
                theta_part2 = r * K * math.exp(-r * T) * norm.cdf(-d2)
                theta = (theta_part1 + theta_part2) / 365  # Per day
            
            # Vega
            vega = S * norm.pdf(d1) * math.sqrt(T) / 100  # Per 1% change in vol
            
            # Rho
            if option_type == 'call':
                rho = K * T * math.exp(-r * T) * norm.cdf(d2) / 100
            else:
                rho = -K * T * math.exp(-r * T) * norm.cdf(-d2) / 100
            
            return {
                'delta': delta,
                'gamma': gamma,
                'theta': theta,
                'vega': vega,
                'rho': rho
            }
            
        except Exception as e:
            logger.error(f"Error calculating Greeks: {e}")
            return {
                'delta': 0.0,
                'gamma': 0.0,
                'theta': 0.0,
                'vega': 0.0,
                'rho': 0.0
            }
    
    def _calculate_intrinsic_value(
        self,
        underlying_price: float,
        strike: float,
        option_type: str
    ) -> float:
        """Calculate intrinsic value of option."""
        if option_type == 'call':
            return max(0, underlying_price - strike)
        else:
            return max(0, strike - underlying_price)
    
    async def _calculate_greeks(self) -> None:
        """Background task to calculate and update Greeks."""
        while self.is_running:
            try:
                for symbol in self.supported_symbols:
                    await self._update_greeks_for_symbol(symbol)
                
                await asyncio.sleep(30)  # Update Greeks every 30 seconds
                
            except Exception as e:
                logger.error(f"Error calculating Greeks: {e}")
                await asyncio.sleep(5)
    
    async def _update_greeks_for_symbol(self, symbol: str) -> None:
        """Update Greeks for all options of a symbol."""
        try:
            today = date.today()
            
            for option_type in ['call', 'put']:
                options_chain = await market_data_cache.get_options_chain(
                    symbol, today.strftime('%Y-%m-%d'), option_type
                )
                
                if not options_chain:
                    continue
                
                # Get underlying price
                market_data = await market_data_cache.get_market_data(symbol)
                if not market_data:
                    continue
                
                underlying_price = float(market_data['price'])
                
                # Update Greeks for each strike
                for strike_str, option_data in options_chain.items():
                    strike = float(strike_str)
                    
                    # Calculate time to expiry (0 for 0DTE)
                    time_to_expiry = 0.0
                    
                    # Update option metrics
                    updated_data = await self._calculate_option_metrics(
                        underlying_price, strike, time_to_expiry, option_type, option_data
                    )
                    
                    options_chain[strike_str] = updated_data
                
                # Update cache
                await market_data_cache.set_options_chain(
                    symbol, today.strftime('%Y-%m-%d'), option_type, options_chain
                )
            
        except Exception as e:
            logger.error(f"Error updating Greeks for {symbol}: {e}")
    
    async def _analyze_0dte_options(self) -> None:
        """Analyze 0DTE options for trading opportunities."""
        while self.is_running:
            try:
                for symbol in self.supported_symbols:
                    analysis = await self._perform_0dte_analysis(symbol)
                    if analysis:
                        # Cache analysis results
                        await market_data_cache.redis.set(
                            f"0dte_analysis:{symbol}",
                            analysis,
                            ttl=300
                        )
                
                await asyncio.sleep(60)  # Analyze every minute
                
            except Exception as e:
                logger.error(f"Error analyzing 0DTE options: {e}")
                await asyncio.sleep(5)
    
    async def _perform_0dte_analysis(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Perform 0DTE options analysis for a symbol."""
        try:
            today = date.today()
            
            # Get options chains
            calls = await market_data_cache.get_options_chain(
                symbol, today.strftime('%Y-%m-%d'), 'call'
            )
            puts = await market_data_cache.get_options_chain(
                symbol, today.strftime('%Y-%m-%d'), 'put'
            )
            
            if not calls or not puts:
                return None
            
            # Get underlying data
            market_data = await market_data_cache.get_market_data(symbol)
            if not market_data:
                return None
            
            underlying_price = float(market_data['price'])
            
            # Find ATM strikes
            atm_strike = self._find_atm_strike(underlying_price, list(calls.keys()))
            
            # Analyze call/put skew
            call_put_skew = self._calculate_call_put_skew(calls, puts, atm_strike)
            
            # Find high gamma strikes
            high_gamma_strikes = self._find_high_gamma_strikes(calls, puts)
            
            # Calculate total volume and open interest
            total_call_volume = sum(opt.get('volume', 0) for opt in calls.values())
            total_put_volume = sum(opt.get('volume', 0) for opt in puts.values())
            
            # Put/call ratio
            put_call_ratio = total_put_volume / total_call_volume if total_call_volume > 0 else 0
            
            # Identify potential pin levels
            pin_levels = self._identify_pin_levels(calls, puts)
            
            return {
                'symbol': symbol,
                'underlying_price': underlying_price,
                'atm_strike': atm_strike,
                'call_put_skew': call_put_skew,
                'put_call_ratio': put_call_ratio,
                'high_gamma_strikes': high_gamma_strikes,
                'pin_levels': pin_levels,
                'total_call_volume': total_call_volume,
                'total_put_volume': total_put_volume,
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error performing 0DTE analysis for {symbol}: {e}")
            return None
    
    def _find_atm_strike(self, underlying_price: float, strikes: List[str]) -> float:
        """Find the at-the-money strike."""
        try:
            strike_floats = [float(s) for s in strikes]
            return min(strike_floats, key=lambda x: abs(x - underlying_price))
        except:
            return round(underlying_price)
    
    def _calculate_call_put_skew(
        self,
        calls: Dict[str, Any],
        puts: Dict[str, Any],
        atm_strike: float
    ) -> float:
        """Calculate call/put implied volatility skew."""
        try:
            atm_call = calls.get(str(atm_strike), {})
            atm_put = puts.get(str(atm_strike), {})
            
            call_iv = atm_call.get('implied_volatility', 0)
            put_iv = atm_put.get('implied_volatility', 0)
            
            return put_iv - call_iv
            
        except:
            return 0.0
    
    def _find_high_gamma_strikes(
        self,
        calls: Dict[str, Any],
        puts: Dict[str, Any]
    ) -> List[float]:
        """Find strikes with high gamma exposure."""
        try:
            high_gamma = []
            
            for strike_str, call_data in calls.items():
                gamma = call_data.get('gamma', 0)
                volume = call_data.get('volume', 0)
                
                if gamma > 0.01 and volume > 100:  # High gamma and volume
                    high_gamma.append(float(strike_str))
            
            for strike_str, put_data in puts.items():
                gamma = put_data.get('gamma', 0)
                volume = put_data.get('volume', 0)
                
                if gamma > 0.01 and volume > 100:  # High gamma and volume
                    strike = float(strike_str)
                    if strike not in high_gamma:
                        high_gamma.append(strike)
            
            return sorted(high_gamma)
            
        except:
            return []
    
    def _identify_pin_levels(
        self,
        calls: Dict[str, Any],
        puts: Dict[str, Any]
    ) -> List[float]:
        """Identify potential pin levels based on open interest."""
        try:
            pin_levels = []
            
            # Combine call and put open interest by strike
            oi_by_strike = {}
            
            for strike_str, call_data in calls.items():
                strike = float(strike_str)
                oi_by_strike[strike] = call_data.get('open_interest', 0)
            
            for strike_str, put_data in puts.items():
                strike = float(strike_str)
                oi_by_strike[strike] = oi_by_strike.get(strike, 0) + put_data.get('open_interest', 0)
            
            # Find strikes with high open interest
            if oi_by_strike:
                max_oi = max(oi_by_strike.values())
                threshold = max_oi * 0.5  # 50% of max OI
                
                for strike, oi in oi_by_strike.items():
                    if oi >= threshold:
                        pin_levels.append(strike)
            
            return sorted(pin_levels)
            
        except:
            return []
    
    async def get_options_chain(
        self,
        symbol: str,
        expiration: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get options chain for a symbol."""
        try:
            if expiration is None:
                expiration = date.today()
            
            exp_str = expiration.strftime('%Y-%m-%d')
            
            calls = await market_data_cache.get_options_chain(symbol, exp_str, 'call')
            puts = await market_data_cache.get_options_chain(symbol, exp_str, 'put')
            
            return {
                'symbol': symbol,
                'expiration': exp_str,
                'calls': calls or {},
                'puts': puts or {},
                'last_updated': self.last_update.get(symbol)
            }
            
        except Exception as e:
            logger.error(f"Error getting options chain for {symbol}: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check options service health."""
        try:
            if not self.is_running:
                return False
            
            # Check if we have recent options data
            for symbol in self.supported_symbols:
                if symbol in self.last_update:
                    last_update = self.last_update[symbol]
                    if (datetime.utcnow() - last_update).seconds > 300:  # 5 minutes
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"Options service health check failed: {e}")
            return False


# Global options service instance
options_service = OptionsService()

