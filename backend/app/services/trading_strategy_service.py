"""
Smart-0DTE-System Trading Strategy Service

This module implements sophisticated 0DTE options trading strategies with
AI-enhanced signal generation and complete options strategies.
"""

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
from decimal import Decimal
from enum import Enum

import numpy as np
import pandas as pd

from app.core.config import settings
from app.core.redis_client import market_data_cache
from app.services.market_data_service import market_data_service
from app.services.options_service import options_service
from app.services.intelligence_service import smart_cross_ticker_engine, vix_regime_detector
from app.services.ai_learning_service import ai_learning_service
from app.models.signal_models import Signal, SignalType, SignalStrength
from app.models.trading_models import OptionsStrategy, StrategyType, TradeLeg

logger = logging.getLogger(__name__)


class StrategyType(Enum):
    """Options strategy types."""
    BULL_CALL_SPREAD = "bull_call_spread"
    BEAR_PUT_SPREAD = "bear_put_spread"
    IRON_CONDOR = "iron_condor"
    IRON_BUTTERFLY = "iron_butterfly"
    STRADDLE = "straddle"
    STRANGLE = "strangle"
    COVERED_CALL = "covered_call"
    PROTECTIVE_PUT = "protective_put"
    COLLAR = "collar"
    CALENDAR_SPREAD = "calendar_spread"


class SignalType(Enum):
    """Signal types for trading."""
    CORRELATION_BREAKDOWN = "correlation_breakdown"
    EXTREME_DIVERGENCE = "extreme_divergence"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM_BREAKOUT = "momentum_breakout"
    VOLATILITY_EXPANSION = "volatility_expansion"
    VOLATILITY_CONTRACTION = "volatility_contraction"
    REGIME_CHANGE = "regime_change"
    AI_PREDICTION = "ai_prediction"


class TradingStrategyService:
    """
    Advanced Trading Strategy Service for 0DTE Options
    
    Implements sophisticated options strategies with AI-enhanced signal generation,
    complete multi-leg strategies, and adaptive risk management.
    """
    
    def __init__(self):
        self.is_running = False
        self.supported_symbols = settings.SUPPORTED_TICKERS
        
        # Strategy configuration
        self.strategy_config = {
            'max_positions_per_symbol': 3,
            'profit_target': 0.10,  # 10% profit target
            'stop_loss': 0.10,      # 10% stop loss
            'min_confidence': settings.DEFAULT_CONFIDENCE_THRESHOLD,
            'max_dte': 0,           # 0DTE only
            'strike_range': 10      # ATM ±10 strikes
        }
        
        # Signal generation parameters
        self.signal_params = {
            'correlation_threshold': settings.CORRELATION_BREAKDOWN_THRESHOLD,
            'divergence_threshold': 2.0,  # Z-score threshold
            'momentum_threshold': 0.02,   # 2% momentum threshold
            'volatility_threshold': 0.03, # 3% volatility threshold
            'ai_confidence_threshold': 0.65
        }
        
        # Active signals and strategies
        self.active_signals = {}
        self.active_strategies = {}
        
        # Performance tracking
        self.strategy_performance = {}
        self.signal_performance = {}
    
    async def initialize(self) -> None:
        """Initialize Trading Strategy Service."""
        try:
            # Load historical performance data
            await self._load_performance_data()
            
            logger.info("Trading Strategy Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Trading Strategy Service: {e}")
            raise
    
    async def start_strategy_engine(self) -> None:
        """Start the trading strategy engine."""
        try:
            self.is_running = True
            
            # Start background tasks
            asyncio.create_task(self._monitor_0dte_opportunities())
            asyncio.create_task(self._generate_signals())
            asyncio.create_task(self._execute_strategies())
            asyncio.create_task(self._monitor_positions())
            asyncio.create_task(self._update_performance_metrics())
            
            logger.info("Trading strategy engine started")
            
        except Exception as e:
            logger.error(f"Failed to start strategy engine: {e}")
            raise
    
    async def stop_strategy_engine(self) -> None:
        """Stop the trading strategy engine."""
        try:
            self.is_running = False
            
            # Save performance data
            await self._save_performance_data()
            
            logger.info("Trading strategy engine stopped")
            
        except Exception as e:
            logger.error(f"Error stopping strategy engine: {e}")
    
    async def _monitor_0dte_opportunities(self) -> None:
        """Monitor 0DTE options for trading opportunities."""
        while self.is_running:
            try:
                for symbol in self.supported_symbols:
                    # Get 0DTE options analysis
                    options_analysis = await market_data_cache.redis.get(f'0dte_analysis:{symbol}')
                    
                    if options_analysis:
                        # Analyze for opportunities
                        opportunities = await self._analyze_0dte_opportunities(symbol, options_analysis)
                        
                        if opportunities:
                            # Cache opportunities
                            await market_data_cache.redis.set(
                                f'0dte_opportunities:{symbol}',
                                opportunities,
                                ttl=300
                            )
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring 0DTE opportunities: {e}")
                await asyncio.sleep(5)
    
    async def _analyze_0dte_opportunities(
        self,
        symbol: str,
        options_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Analyze 0DTE options for specific opportunities."""
        try:
            opportunities = []
            
            underlying_price = options_analysis.get('underlying_price', 0)
            atm_strike = options_analysis.get('atm_strike', underlying_price)
            put_call_ratio = options_analysis.get('put_call_ratio', 1.0)
            high_gamma_strikes = options_analysis.get('high_gamma_strikes', [])
            pin_levels = options_analysis.get('pin_levels', [])
            
            # Get current market regime
            regime_data = await vix_regime_detector.get_current_regime()
            regime_type = regime_data.get('regime_type', 'normal_volatility')
            
            # Get AI predictions
            ai_predictions = await ai_learning_service.get_ai_predictions()
            
            # Opportunity 1: High Gamma Squeeze
            if high_gamma_strikes and len(high_gamma_strikes) >= 2:
                gamma_opportunity = {
                    'type': 'gamma_squeeze',
                    'symbol': symbol,
                    'strikes': high_gamma_strikes,
                    'confidence': 0.7,
                    'strategy_suggestion': 'iron_condor',
                    'reasoning': 'High gamma concentration suggests limited movement'
                }
                opportunities.append(gamma_opportunity)
            
            # Opportunity 2: Pin Risk
            if pin_levels and abs(underlying_price - pin_levels[0]) < 2.0:
                pin_opportunity = {
                    'type': 'pin_risk',
                    'symbol': symbol,
                    'pin_level': pin_levels[0],
                    'confidence': 0.6,
                    'strategy_suggestion': 'iron_butterfly',
                    'reasoning': f'Price near pin level {pin_levels[0]}'
                }
                opportunities.append(pin_opportunity)
            
            # Opportunity 3: Extreme Put/Call Ratio
            if put_call_ratio > 2.0:
                sentiment_opportunity = {
                    'type': 'extreme_sentiment',
                    'symbol': symbol,
                    'put_call_ratio': put_call_ratio,
                    'confidence': 0.65,
                    'strategy_suggestion': 'bull_call_spread',
                    'reasoning': 'Extreme bearish sentiment may reverse'
                }
                opportunities.append(sentiment_opportunity)
            elif put_call_ratio < 0.5:
                sentiment_opportunity = {
                    'type': 'extreme_sentiment',
                    'symbol': symbol,
                    'put_call_ratio': put_call_ratio,
                    'confidence': 0.65,
                    'strategy_suggestion': 'bear_put_spread',
                    'reasoning': 'Extreme bullish sentiment may reverse'
                }
                opportunities.append(sentiment_opportunity)
            
            # Opportunity 4: AI-Based Prediction
            if ai_predictions:
                ai_confidence = ai_predictions.get('signal_success_probability', 0)
                recommended_strategy = ai_predictions.get('recommended_strategy', '')
                
                if ai_confidence > self.signal_params['ai_confidence_threshold']:
                    ai_opportunity = {
                        'type': 'ai_prediction',
                        'symbol': symbol,
                        'ai_confidence': ai_confidence,
                        'confidence': ai_confidence,
                        'strategy_suggestion': recommended_strategy,
                        'reasoning': f'AI model predicts {ai_confidence:.1%} success probability'
                    }
                    opportunities.append(ai_opportunity)
            
            # Opportunity 5: Volatility Regime
            if regime_type == 'low_volatility':
                vol_opportunity = {
                    'type': 'volatility_regime',
                    'symbol': symbol,
                    'regime': regime_type,
                    'confidence': 0.6,
                    'strategy_suggestion': 'iron_condor',
                    'reasoning': 'Low volatility regime favors range-bound strategies'
                }
                opportunities.append(vol_opportunity)
            elif regime_type == 'high_volatility':
                vol_opportunity = {
                    'type': 'volatility_regime',
                    'symbol': symbol,
                    'regime': regime_type,
                    'confidence': 0.65,
                    'strategy_suggestion': 'straddle',
                    'reasoning': 'High volatility regime favors directional strategies'
                }
                opportunities.append(vol_opportunity)
            
            return opportunities
            
        except Exception as e:
            logger.error(f"Error analyzing 0DTE opportunities for {symbol}: {e}")
            return []
    
    async def _generate_signals(self) -> None:
        """Generate trading signals based on multiple factors."""
        while self.is_running:
            try:
                signals = []
                
                for symbol in self.supported_symbols:
                    # Generate signals from different sources
                    correlation_signals = await self._generate_correlation_signals(symbol)
                    momentum_signals = await self._generate_momentum_signals(symbol)
                    volatility_signals = await self._generate_volatility_signals(symbol)
                    ai_signals = await self._generate_ai_signals(symbol)
                    
                    # Combine all signals
                    symbol_signals = correlation_signals + momentum_signals + volatility_signals + ai_signals
                    
                    # Filter and rank signals
                    filtered_signals = await self._filter_and_rank_signals(symbol_signals)
                    
                    signals.extend(filtered_signals)
                
                # Cache generated signals
                if signals:
                    await market_data_cache.redis.set('trading_signals', signals, ttl=300)
                    
                    # Update active signals
                    self.active_signals = {signal['id']: signal for signal in signals}
                
                await asyncio.sleep(60)  # Generate signals every minute
                
            except Exception as e:
                logger.error(f"Error generating signals: {e}")
                await asyncio.sleep(5)
    
    async def _generate_correlation_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """Generate signals based on correlation analysis."""
        try:
            signals = []
            
            # Get cross-ticker signals
            cross_ticker_signals = await smart_cross_ticker_engine.get_cross_ticker_signals()
            
            for signal_data in cross_ticker_signals:
                if signal_data.get('target_symbol') == symbol:
                    signal = {
                        'id': f"corr_{symbol}_{datetime.utcnow().timestamp()}",
                        'symbol': symbol,
                        'type': SignalType.CORRELATION_BREAKDOWN.value,
                        'strength': self._calculate_signal_strength(signal_data.get('confidence', 0)),
                        'confidence': signal_data.get('confidence', 0),
                        'reasoning': signal_data.get('reasoning', []),
                        'source_data': signal_data,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating correlation signals for {symbol}: {e}")
            return []
    
    async def _generate_momentum_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """Generate signals based on momentum analysis."""
        try:
            signals = []
            
            # Get market data
            market_data = await market_data_cache.get_market_data(symbol)
            
            if not market_data:
                return signals
            
            change_percent = market_data.get('change_percent', 0)
            
            # Strong momentum signal
            if abs(change_percent) > self.signal_params['momentum_threshold'] * 100:
                direction = 'bullish' if change_percent > 0 else 'bearish'
                
                signal = {
                    'id': f"momentum_{symbol}_{datetime.utcnow().timestamp()}",
                    'symbol': symbol,
                    'type': SignalType.MOMENTUM_BREAKOUT.value,
                    'strength': self._calculate_signal_strength(min(abs(change_percent) / 5, 1.0)),
                    'confidence': min(abs(change_percent) / 3, 0.8),
                    'direction': direction,
                    'reasoning': [f"Strong {direction} momentum: {change_percent:.2f}%"],
                    'source_data': market_data,
                    'timestamp': datetime.utcnow().isoformat()
                }
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating momentum signals for {symbol}: {e}")
            return []
    
    async def _generate_volatility_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """Generate signals based on volatility analysis."""
        try:
            signals = []
            
            # Get regime data
            regime_data = await vix_regime_detector.get_current_regime()
            
            if not regime_data:
                return signals
            
            regime_type = regime_data.get('regime_type', 'normal_volatility')
            vix_level = regime_data.get('vix_level', 20)
            regime_change = regime_data.get('regime_change', False)
            
            # Volatility expansion signal
            if regime_type == 'high_volatility' and regime_change:
                signal = {
                    'id': f"vol_expansion_{symbol}_{datetime.utcnow().timestamp()}",
                    'symbol': symbol,
                    'type': SignalType.VOLATILITY_EXPANSION.value,
                    'strength': self._calculate_signal_strength(min(vix_level / 40, 1.0)),
                    'confidence': 0.7,
                    'reasoning': [f"Volatility expansion detected: VIX {vix_level:.1f}"],
                    'source_data': regime_data,
                    'timestamp': datetime.utcnow().isoformat()
                }
                signals.append(signal)
            
            # Volatility contraction signal
            elif regime_type == 'low_volatility' and regime_change:
                signal = {
                    'id': f"vol_contraction_{symbol}_{datetime.utcnow().timestamp()}",
                    'symbol': symbol,
                    'type': SignalType.VOLATILITY_CONTRACTION.value,
                    'strength': self._calculate_signal_strength(max(1 - vix_level / 20, 0.3)),
                    'confidence': 0.65,
                    'reasoning': [f"Volatility contraction detected: VIX {vix_level:.1f}"],
                    'source_data': regime_data,
                    'timestamp': datetime.utcnow().isoformat()
                }
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating volatility signals for {symbol}: {e}")
            return []
    
    async def _generate_ai_signals(self, symbol: str) -> List[Dict[str, Any]]:
        """Generate signals based on AI predictions."""
        try:
            signals = []
            
            # Get AI predictions
            ai_predictions = await ai_learning_service.get_ai_predictions()
            
            if not ai_predictions:
                return signals
            
            signal_probability = ai_predictions.get('signal_success_probability', 0)
            predicted_volatility = ai_predictions.get('predicted_volatility', 0)
            recommended_strategy = ai_predictions.get('recommended_strategy', '')
            
            # High-confidence AI signal
            if signal_probability > self.signal_params['ai_confidence_threshold']:
                signal = {
                    'id': f"ai_{symbol}_{datetime.utcnow().timestamp()}",
                    'symbol': symbol,
                    'type': SignalType.AI_PREDICTION.value,
                    'strength': self._calculate_signal_strength(signal_probability),
                    'confidence': signal_probability,
                    'recommended_strategy': recommended_strategy,
                    'predicted_volatility': predicted_volatility,
                    'reasoning': [f"AI model confidence: {signal_probability:.1%}"],
                    'source_data': ai_predictions,
                    'timestamp': datetime.utcnow().isoformat()
                }
                signals.append(signal)
            
            return signals
            
        except Exception as e:
            logger.error(f"Error generating AI signals for {symbol}: {e}")
            return []
    
    def _calculate_signal_strength(self, confidence: float) -> str:
        """Calculate signal strength based on confidence."""
        if confidence >= 0.8:
            return 'STRONG'
        elif confidence >= 0.65:
            return 'MODERATE'
        elif confidence >= 0.5:
            return 'WEAK'
        else:
            return 'VERY_WEAK'
    
    async def _filter_and_rank_signals(self, signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter and rank signals by quality and confidence."""
        try:
            # Filter by minimum confidence
            filtered_signals = [
                signal for signal in signals
                if signal.get('confidence', 0) >= self.strategy_config['min_confidence']
            ]
            
            # Get adaptive parameters
            adaptive_params = await ai_learning_service.get_adaptive_parameters()
            adjusted_threshold = adaptive_params.get('confidence_threshold', self.strategy_config['min_confidence'])
            
            # Apply adaptive filtering
            filtered_signals = [
                signal for signal in filtered_signals
                if signal.get('confidence', 0) >= adjusted_threshold
            ]
            
            # Rank by confidence and strength
            ranked_signals = sorted(
                filtered_signals,
                key=lambda x: (x.get('confidence', 0), self._strength_to_numeric(x.get('strength', 'WEAK'))),
                reverse=True
            )
            
            # Limit to top signals per symbol
            symbol_counts = {}
            final_signals = []
            
            for signal in ranked_signals:
                symbol = signal.get('symbol', '')
                count = symbol_counts.get(symbol, 0)
                
                if count < 2:  # Max 2 signals per symbol
                    final_signals.append(signal)
                    symbol_counts[symbol] = count + 1
            
            return final_signals
            
        except Exception as e:
            logger.error(f"Error filtering and ranking signals: {e}")
            return signals
    
    def _strength_to_numeric(self, strength: str) -> float:
        """Convert strength string to numeric value for sorting."""
        strength_map = {
            'STRONG': 4.0,
            'MODERATE': 3.0,
            'WEAK': 2.0,
            'VERY_WEAK': 1.0
        }
        return strength_map.get(strength, 1.0)
    
    async def _execute_strategies(self) -> None:
        """Execute trading strategies based on signals."""
        while self.is_running:
            try:
                # Get current signals
                signals = await market_data_cache.redis.get('trading_signals')
                
                if not signals:
                    await asyncio.sleep(30)
                    continue
                
                for signal in signals:
                    # Check if we should execute this signal
                    should_execute = await self._should_execute_signal(signal)
                    
                    if should_execute:
                        # Generate strategy for signal
                        strategy = await self._generate_strategy_for_signal(signal)
                        
                        if strategy:
                            # Execute strategy (would integrate with IBKR in production)
                            execution_result = await self._simulate_strategy_execution(strategy)
                            
                            if execution_result.get('success'):
                                # Track active strategy
                                self.active_strategies[strategy['id']] = strategy
                                
                                # Cache strategy
                                await market_data_cache.redis.set(
                                    f"active_strategy:{strategy['id']}",
                                    strategy,
                                    ttl=86400  # 24 hours
                                )
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error executing strategies: {e}")
                await asyncio.sleep(5)
    
    async def _should_execute_signal(self, signal: Dict[str, Any]) -> bool:
        """Determine if a signal should be executed."""
        try:
            symbol = signal.get('symbol', '')
            confidence = signal.get('confidence', 0)
            
            # Check position limits
            active_positions = len([
                s for s in self.active_strategies.values()
                if s.get('symbol') == symbol and s.get('status') == 'active'
            ])
            
            if active_positions >= self.strategy_config['max_positions_per_symbol']:
                return False
            
            # Check confidence threshold
            if confidence < self.strategy_config['min_confidence']:
                return False
            
            # Check market hours (would be more sophisticated in production)
            current_hour = datetime.now().hour
            if current_hour < 9 or current_hour > 16:  # Outside market hours
                return False
            
            # Get adaptive parameters
            adaptive_params = await ai_learning_service.get_adaptive_parameters()
            
            # Check emergency mode
            if adaptive_params.get('emergency_mode', False):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking signal execution: {e}")
            return False
    
    async def _generate_strategy_for_signal(self, signal: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Generate options strategy for a signal."""
        try:
            symbol = signal.get('symbol', '')
            signal_type = signal.get('type', '')
            confidence = signal.get('confidence', 0)
            
            # Get recommended strategy from signal or AI
            recommended_strategy = signal.get('recommended_strategy')
            if not recommended_strategy:
                # Default strategy selection based on signal type
                strategy_map = {
                    SignalType.CORRELATION_BREAKDOWN.value: StrategyType.STRADDLE.value,
                    SignalType.MOMENTUM_BREAKOUT.value: StrategyType.BULL_CALL_SPREAD.value,
                    SignalType.VOLATILITY_EXPANSION.value: StrategyType.STRADDLE.value,
                    SignalType.VOLATILITY_CONTRACTION.value: StrategyType.IRON_CONDOR.value,
                    SignalType.AI_PREDICTION.value: StrategyType.BULL_CALL_SPREAD.value
                }
                recommended_strategy = strategy_map.get(signal_type, StrategyType.BULL_CALL_SPREAD.value)
            
            # Get current market data
            market_data = await market_data_cache.get_market_data(symbol)
            if not market_data:
                return None
            
            underlying_price = market_data.get('price', 0)
            
            # Get options chain
            options_chain = await options_service.get_options_chain(symbol)
            if not options_chain.get('calls') or not options_chain.get('puts'):
                return None
            
            # Generate strategy based on type
            strategy = await self._build_options_strategy(
                symbol, recommended_strategy, underlying_price, options_chain, signal
            )
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error generating strategy for signal: {e}")
            return None
    
    async def _build_options_strategy(
        self,
        symbol: str,
        strategy_type: str,
        underlying_price: float,
        options_chain: Dict[str, Any],
        signal: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Build specific options strategy."""
        try:
            strategy_id = f"{strategy_type}_{symbol}_{datetime.utcnow().timestamp()}"
            
            # Get ATM strike
            atm_strike = round(underlying_price)
            
            # Build strategy based on type
            if strategy_type == StrategyType.BULL_CALL_SPREAD.value:
                legs = await self._build_bull_call_spread(atm_strike, options_chain)
            elif strategy_type == StrategyType.BEAR_PUT_SPREAD.value:
                legs = await self._build_bear_put_spread(atm_strike, options_chain)
            elif strategy_type == StrategyType.IRON_CONDOR.value:
                legs = await self._build_iron_condor(atm_strike, options_chain)
            elif strategy_type == StrategyType.STRADDLE.value:
                legs = await self._build_straddle(atm_strike, options_chain)
            elif strategy_type == StrategyType.STRANGLE.value:
                legs = await self._build_strangle(atm_strike, options_chain)
            else:
                legs = await self._build_bull_call_spread(atm_strike, options_chain)  # Default
            
            if not legs:
                return None
            
            # Calculate strategy metrics
            net_premium = sum(leg.get('premium', 0) * leg.get('quantity', 0) for leg in legs)
            max_profit = await self._calculate_max_profit(legs, strategy_type)
            max_loss = await self._calculate_max_loss(legs, strategy_type)
            
            strategy = {
                'id': strategy_id,
                'symbol': symbol,
                'strategy_type': strategy_type,
                'underlying_price': underlying_price,
                'legs': legs,
                'net_premium': net_premium,
                'max_profit': max_profit,
                'max_loss': max_loss,
                'profit_target': net_premium * self.strategy_config['profit_target'],
                'stop_loss': net_premium * self.strategy_config['stop_loss'],
                'signal_id': signal.get('id'),
                'confidence': signal.get('confidence', 0),
                'status': 'pending',
                'created_at': datetime.utcnow().isoformat(),
                'expiration': date.today().isoformat()  # 0DTE
            }
            
            return strategy
            
        except Exception as e:
            logger.error(f"Error building options strategy: {e}")
            return None
    
    async def _build_bull_call_spread(
        self,
        atm_strike: float,
        options_chain: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build bull call spread strategy."""
        try:
            calls = options_chain.get('calls', {})
            
            # Buy ATM call, sell OTM call
            long_strike = atm_strike
            short_strike = atm_strike + 5  # $5 wide spread
            
            long_call = calls.get(str(long_strike))
            short_call = calls.get(str(short_strike))
            
            if not long_call or not short_call:
                return []
            
            legs = [
                {
                    'option_type': 'call',
                    'strike': long_strike,
                    'action': 'buy',
                    'quantity': 1,
                    'premium': long_call.get('ask', 0)
                },
                {
                    'option_type': 'call',
                    'strike': short_strike,
                    'action': 'sell',
                    'quantity': 1,
                    'premium': short_call.get('bid', 0)
                }
            ]
            
            return legs
            
        except Exception as e:
            logger.error(f"Error building bull call spread: {e}")
            return []
    
    async def _build_bear_put_spread(
        self,
        atm_strike: float,
        options_chain: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build bear put spread strategy."""
        try:
            puts = options_chain.get('puts', {})
            
            # Buy OTM put, sell ITM put
            long_strike = atm_strike - 5
            short_strike = atm_strike
            
            long_put = puts.get(str(long_strike))
            short_put = puts.get(str(short_strike))
            
            if not long_put or not short_put:
                return []
            
            legs = [
                {
                    'option_type': 'put',
                    'strike': long_strike,
                    'action': 'buy',
                    'quantity': 1,
                    'premium': long_put.get('ask', 0)
                },
                {
                    'option_type': 'put',
                    'strike': short_strike,
                    'action': 'sell',
                    'quantity': 1,
                    'premium': short_put.get('bid', 0)
                }
            ]
            
            return legs
            
        except Exception as e:
            logger.error(f"Error building bear put spread: {e}")
            return []
    
    async def _build_iron_condor(
        self,
        atm_strike: float,
        options_chain: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build iron condor strategy."""
        try:
            calls = options_chain.get('calls', {})
            puts = options_chain.get('puts', {})
            
            # Sell ATM call and put, buy OTM call and put
            call_short_strike = atm_strike + 2
            call_long_strike = atm_strike + 7
            put_short_strike = atm_strike - 2
            put_long_strike = atm_strike - 7
            
            call_short = calls.get(str(call_short_strike))
            call_long = calls.get(str(call_long_strike))
            put_short = puts.get(str(put_short_strike))
            put_long = puts.get(str(put_long_strike))
            
            if not all([call_short, call_long, put_short, put_long]):
                return []
            
            legs = [
                {
                    'option_type': 'call',
                    'strike': call_short_strike,
                    'action': 'sell',
                    'quantity': 1,
                    'premium': call_short.get('bid', 0)
                },
                {
                    'option_type': 'call',
                    'strike': call_long_strike,
                    'action': 'buy',
                    'quantity': 1,
                    'premium': call_long.get('ask', 0)
                },
                {
                    'option_type': 'put',
                    'strike': put_short_strike,
                    'action': 'sell',
                    'quantity': 1,
                    'premium': put_short.get('bid', 0)
                },
                {
                    'option_type': 'put',
                    'strike': put_long_strike,
                    'action': 'buy',
                    'quantity': 1,
                    'premium': put_long.get('ask', 0)
                }
            ]
            
            return legs
            
        except Exception as e:
            logger.error(f"Error building iron condor: {e}")
            return []
    
    async def _build_straddle(
        self,
        atm_strike: float,
        options_chain: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build straddle strategy."""
        try:
            calls = options_chain.get('calls', {})
            puts = options_chain.get('puts', {})
            
            # Buy ATM call and put
            atm_call = calls.get(str(atm_strike))
            atm_put = puts.get(str(atm_strike))
            
            if not atm_call or not atm_put:
                return []
            
            legs = [
                {
                    'option_type': 'call',
                    'strike': atm_strike,
                    'action': 'buy',
                    'quantity': 1,
                    'premium': atm_call.get('ask', 0)
                },
                {
                    'option_type': 'put',
                    'strike': atm_strike,
                    'action': 'buy',
                    'quantity': 1,
                    'premium': atm_put.get('ask', 0)
                }
            ]
            
            return legs
            
        except Exception as e:
            logger.error(f"Error building straddle: {e}")
            return []
    
    async def _build_strangle(
        self,
        atm_strike: float,
        options_chain: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Build strangle strategy."""
        try:
            calls = options_chain.get('calls', {})
            puts = options_chain.get('puts', {})
            
            # Buy OTM call and put
            call_strike = atm_strike + 3
            put_strike = atm_strike - 3
            
            otm_call = calls.get(str(call_strike))
            otm_put = puts.get(str(put_strike))
            
            if not otm_call or not otm_put:
                return []
            
            legs = [
                {
                    'option_type': 'call',
                    'strike': call_strike,
                    'action': 'buy',
                    'quantity': 1,
                    'premium': otm_call.get('ask', 0)
                },
                {
                    'option_type': 'put',
                    'strike': put_strike,
                    'action': 'buy',
                    'quantity': 1,
                    'premium': otm_put.get('ask', 0)
                }
            ]
            
            return legs
            
        except Exception as e:
            logger.error(f"Error building strangle: {e}")
            return []
    
    async def _calculate_max_profit(self, legs: List[Dict[str, Any]], strategy_type: str) -> float:
        """Calculate maximum profit for strategy."""
        try:
            if strategy_type == StrategyType.BULL_CALL_SPREAD.value:
                # Max profit = spread width - net premium paid
                strikes = [leg['strike'] for leg in legs]
                spread_width = max(strikes) - min(strikes)
                net_premium = sum(leg['premium'] * leg['quantity'] * (1 if leg['action'] == 'sell' else -1) for leg in legs)
                return spread_width - abs(net_premium)
            
            elif strategy_type == StrategyType.IRON_CONDOR.value:
                # Max profit = net premium received
                return sum(leg['premium'] * leg['quantity'] * (1 if leg['action'] == 'sell' else -1) for leg in legs)
            
            elif strategy_type in [StrategyType.STRADDLE.value, StrategyType.STRANGLE.value]:
                # Unlimited profit potential
                return float('inf')
            
            else:
                # Default calculation
                return sum(leg['premium'] * leg['quantity'] * (1 if leg['action'] == 'sell' else -1) for leg in legs)
                
        except Exception as e:
            logger.error(f"Error calculating max profit: {e}")
            return 0.0
    
    async def _calculate_max_loss(self, legs: List[Dict[str, Any]], strategy_type: str) -> float:
        """Calculate maximum loss for strategy."""
        try:
            net_premium = sum(leg['premium'] * leg['quantity'] * (1 if leg['action'] == 'sell' else -1) for leg in legs)
            
            if strategy_type in [StrategyType.BULL_CALL_SPREAD.value, StrategyType.BEAR_PUT_SPREAD.value]:
                # Max loss = net premium paid
                return abs(net_premium) if net_premium < 0 else 0
            
            elif strategy_type == StrategyType.IRON_CONDOR.value:
                # Max loss = spread width - net premium received
                call_strikes = [leg['strike'] for leg in legs if leg['option_type'] == 'call']
                put_strikes = [leg['strike'] for leg in legs if leg['option_type'] == 'put']
                
                call_spread = max(call_strikes) - min(call_strikes) if call_strikes else 0
                put_spread = max(put_strikes) - min(put_strikes) if put_strikes else 0
                
                max_spread = max(call_spread, put_spread)
                return max_spread - net_premium
            
            elif strategy_type in [StrategyType.STRADDLE.value, StrategyType.STRANGLE.value]:
                # Max loss = net premium paid
                return abs(net_premium)
            
            else:
                return abs(net_premium)
                
        except Exception as e:
            logger.error(f"Error calculating max loss: {e}")
            return 0.0
    
    async def _simulate_strategy_execution(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate strategy execution (would integrate with IBKR in production)."""
        try:
            # Simulate successful execution
            execution_result = {
                'success': True,
                'strategy_id': strategy['id'],
                'execution_time': datetime.utcnow().isoformat(),
                'fill_price': strategy.get('net_premium', 0),
                'status': 'filled'
            }
            
            # Update strategy status
            strategy['status'] = 'active'
            strategy['executed_at'] = datetime.utcnow().isoformat()
            
            return execution_result
            
        except Exception as e:
            logger.error(f"Error simulating strategy execution: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _monitor_positions(self) -> None:
        """Monitor active positions for profit/loss targets."""
        while self.is_running:
            try:
                for strategy_id, strategy in self.active_strategies.items():
                    if strategy.get('status') != 'active':
                        continue
                    
                    # Check if position should be closed
                    should_close = await self._should_close_position(strategy)
                    
                    if should_close:
                        # Close position
                        close_result = await self._close_position(strategy)
                        
                        if close_result.get('success'):
                            strategy['status'] = 'closed'
                            strategy['closed_at'] = datetime.utcnow().isoformat()
                            strategy['pnl'] = close_result.get('pnl', 0)
                
                await asyncio.sleep(10)  # Monitor every 10 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring positions: {e}")
                await asyncio.sleep(5)
    
    async def _should_close_position(self, strategy: Dict[str, Any]) -> bool:
        """Determine if position should be closed."""
        try:
            # Check time-based exit (close before market close for 0DTE)
            current_time = datetime.now()
            if current_time.hour >= 15 and current_time.minute >= 45:  # 3:45 PM
                return True
            
            # Check profit/loss targets
            current_pnl = await self._calculate_current_pnl(strategy)
            
            profit_target = strategy.get('profit_target', 0)
            stop_loss = strategy.get('stop_loss', 0)
            
            if current_pnl >= profit_target:
                return True  # Profit target hit
            
            if current_pnl <= -stop_loss:
                return True  # Stop loss hit
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking position close condition: {e}")
            return False
    
    async def _calculate_current_pnl(self, strategy: Dict[str, Any]) -> float:
        """Calculate current P&L for strategy."""
        try:
            # This would calculate real-time P&L based on current option prices
            # For simulation, return random P&L
            import random
            return random.uniform(-50, 100)  # Random P&L for demo
            
        except Exception as e:
            logger.error(f"Error calculating current P&L: {e}")
            return 0.0
    
    async def _close_position(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """Close an active position."""
        try:
            # Simulate position closing
            pnl = await self._calculate_current_pnl(strategy)
            
            close_result = {
                'success': True,
                'strategy_id': strategy['id'],
                'close_time': datetime.utcnow().isoformat(),
                'pnl': pnl,
                'close_reason': 'target_hit' if pnl > 0 else 'stop_loss'
            }
            
            return close_result
            
        except Exception as e:
            logger.error(f"Error closing position: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _update_performance_metrics(self) -> None:
        """Update strategy and signal performance metrics."""
        while self.is_running:
            try:
                # Calculate strategy performance
                strategy_metrics = await self._calculate_strategy_performance()
                
                # Calculate signal performance
                signal_metrics = await self._calculate_signal_performance()
                
                # Cache performance metrics
                performance_data = {
                    'strategy_performance': strategy_metrics,
                    'signal_performance': signal_metrics,
                    'last_updated': datetime.utcnow().isoformat()
                }
                
                await market_data_cache.redis.set(
                    'trading_performance',
                    performance_data,
                    ttl=3600
                )
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"Error updating performance metrics: {e}")
                await asyncio.sleep(60)
    
    async def _calculate_strategy_performance(self) -> Dict[str, Any]:
        """Calculate strategy performance metrics."""
        try:
            closed_strategies = [
                s for s in self.active_strategies.values()
                if s.get('status') == 'closed'
            ]
            
            if not closed_strategies:
                return {}
            
            total_pnl = sum(s.get('pnl', 0) for s in closed_strategies)
            winning_trades = len([s for s in closed_strategies if s.get('pnl', 0) > 0])
            total_trades = len(closed_strategies)
            
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            avg_pnl = total_pnl / total_trades if total_trades > 0 else 0
            
            return {
                'total_trades': total_trades,
                'winning_trades': winning_trades,
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'average_pnl': avg_pnl
            }
            
        except Exception as e:
            logger.error(f"Error calculating strategy performance: {e}")
            return {}
    
    async def _calculate_signal_performance(self) -> Dict[str, Any]:
        """Calculate signal performance metrics."""
        try:
            # This would track signal accuracy over time
            # For now, return mock metrics
            return {
                'total_signals': len(self.active_signals),
                'successful_signals': 0,
                'signal_accuracy': 0.65
            }
            
        except Exception as e:
            logger.error(f"Error calculating signal performance: {e}")
            return {}
    
    async def _load_performance_data(self) -> None:
        """Load historical performance data."""
        try:
            # Load from cache or database
            performance_data = await market_data_cache.redis.get('trading_performance')
            
            if performance_data:
                self.strategy_performance = performance_data.get('strategy_performance', {})
                self.signal_performance = performance_data.get('signal_performance', {})
            
            logger.info("Performance data loaded")
            
        except Exception as e:
            logger.error(f"Error loading performance data: {e}")
    
    async def _save_performance_data(self) -> None:
        """Save performance data."""
        try:
            performance_data = {
                'strategy_performance': self.strategy_performance,
                'signal_performance': self.signal_performance,
                'last_saved': datetime.utcnow().isoformat()
            }
            
            await market_data_cache.redis.set(
                'trading_performance',
                performance_data,
                ttl=86400 * 30  # 30 days
            )
            
            logger.info("Performance data saved")
            
        except Exception as e:
            logger.error(f"Error saving performance data: {e}")
    
    # Public API methods
    
    async def get_active_signals(self) -> List[Dict[str, Any]]:
        """Get current active signals."""
        try:
            signals = await market_data_cache.redis.get('trading_signals')
            return signals or []
        except Exception as e:
            logger.error(f"Error getting active signals: {e}")
            return []
    
    async def get_active_strategies(self) -> List[Dict[str, Any]]:
        """Get current active strategies."""
        try:
            return list(self.active_strategies.values())
        except Exception as e:
            logger.error(f"Error getting active strategies: {e}")
            return []
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        try:
            performance_data = await market_data_cache.redis.get('trading_performance')
            return performance_data or {}
        except Exception as e:
            logger.error(f"Error getting performance metrics: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check trading strategy service health."""
        try:
            if not self.is_running:
                return False
            
            # Check if signals are being generated
            signals = await market_data_cache.redis.get('trading_signals')
            if signals is None:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Trading Strategy Service health check failed: {e}")
            return False


# Global trading strategy service instance
trading_strategy_service = TradingStrategyService()

