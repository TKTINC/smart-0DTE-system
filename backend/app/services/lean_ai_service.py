"""
Lean AI Service for Smart-0DTE-System
Optimized AI/ML service with efficient learning and reduced computational costs.
"""

import asyncio
import logging
import pickle
import gzip
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import numpy as np
from dataclasses import dataclass
import json

# Lightweight ML libraries for lean deployment
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib

from app.core.lean_config import lean_config, ai_optimization
from app.core.lean_cache import lean_cache_manager, cache_result
from app.core.lean_database import lean_db_manager

logger = logging.getLogger(__name__)


@dataclass
class ModelPerformance:
    """Track model performance metrics."""
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    last_updated: datetime = None
    training_samples: int = 0
    prediction_count: int = 0


@dataclass
class AIUsageStats:
    """Track AI usage for cost optimization."""
    predictions_today: int = 0
    model_updates_today: int = 0
    feature_extractions: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    compute_time_ms: float = 0.0


class LeanAIService:
    """Optimized AI service with efficient learning and prediction."""
    
    def __init__(self):
        # Lightweight models for lean deployment
        self.signal_classifier = None
        self.volatility_predictor = None
        self.correlation_predictor = None
        self.strategy_selector = None
        
        # Model performance tracking
        self.model_performance = {
            'signal_classifier': ModelPerformance(),
            'volatility_predictor': ModelPerformance(),
            'correlation_predictor': ModelPerformance(),
            'strategy_selector': ModelPerformance()
        }
        
        # Feature engineering
        self.feature_scaler = StandardScaler()
        self.feature_cache = {}
        self.feature_importance = {}
        
        # Optimization settings
        self.max_features = ai_optimization.FEATURE_COUNT_LIMIT
        self.batch_size = ai_optimization.INFERENCE_BATCH_SIZE
        self.model_cache_size = lean_config.AI_MODEL_CACHE_SIZE
        
        # Usage statistics
        self.usage_stats = AIUsageStats()
        
        # Prediction cache for efficiency
        self.prediction_cache = {}
        self.prediction_cache_ttl = lean_config.AI_PREDICTION_CACHE_TTL
        
        # Model update scheduling
        self.last_model_update = {}
        self.model_update_interval = lean_config.AI_MODEL_UPDATE_INTERVAL
        
        # Lightweight feature set for cost optimization
        self.essential_features = [
            'price_change_1m', 'price_change_5m', 'price_change_15m',
            'volume_ratio', 'volatility_1h', 'correlation_spy_qqq',
            'correlation_spy_iwm', 'vix_level', 'vix_change',
            'time_to_close', 'market_regime', 'momentum_score'
        ]
    
    async def initialize(self) -> None:
        """Initialize AI service with lean configuration."""
        try:
            # Load pre-trained models if available
            await self._load_models()
            
            # Initialize feature scaler
            await self._initialize_feature_scaler()
            
            # Start model monitoring
            asyncio.create_task(self._model_monitoring_loop())
            
            # Start usage tracking
            asyncio.create_task(self._usage_tracking_loop())
            
            logger.info("Lean AI service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize lean AI service: {e}")
            # Initialize with default models
            await self._initialize_default_models()
    
    async def _load_models(self) -> None:
        """Load pre-trained models from cache or storage."""
        try:
            # Try to load from cache first
            cached_models = await lean_cache_manager.get("ai_models")
            
            if cached_models:
                self.signal_classifier = cached_models.get('signal_classifier')
                self.volatility_predictor = cached_models.get('volatility_predictor')
                self.correlation_predictor = cached_models.get('correlation_predictor')
                self.strategy_selector = cached_models.get('strategy_selector')
                
                logger.info("Loaded models from cache")
            else:
                # Initialize new models
                await self._initialize_default_models()
                
        except Exception as e:
            logger.error(f"Failed to load models: {e}")
            await self._initialize_default_models()
    
    async def _initialize_default_models(self) -> None:
        """Initialize default lightweight models."""
        try:
            # Signal classifier - lightweight Random Forest
            self.signal_classifier = RandomForestClassifier(
                n_estimators=ai_optimization.TRAINING_EPOCHS,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=1  # Single thread for cost optimization
            )
            
            # Volatility predictor - lightweight Gradient Boosting
            self.volatility_predictor = GradientBoostingRegressor(
                n_estimators=ai_optimization.TRAINING_EPOCHS,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
            
            # Correlation predictor - lightweight Logistic Regression
            self.correlation_predictor = LogisticRegression(
                random_state=42,
                max_iter=100,
                solver='liblinear'  # Faster for small datasets
            )
            
            # Strategy selector - lightweight Random Forest
            self.strategy_selector = RandomForestClassifier(
                n_estimators=20,  # Reduced for speed
                max_depth=8,
                random_state=42,
                n_jobs=1
            )
            
            logger.info("Initialized default lightweight models")
            
        except Exception as e:
            logger.error(f"Failed to initialize default models: {e}")
            raise
    
    async def _initialize_feature_scaler(self) -> None:
        """Initialize feature scaler with cached data if available."""
        try:
            cached_scaler = await lean_cache_manager.get("feature_scaler")
            
            if cached_scaler:
                self.feature_scaler = cached_scaler
                logger.info("Loaded feature scaler from cache")
            else:
                # Initialize with dummy data
                dummy_features = np.random.randn(100, len(self.essential_features))
                self.feature_scaler.fit(dummy_features)
                
                # Cache the scaler
                await lean_cache_manager.set("feature_scaler", self.feature_scaler, ttl=86400)
                
        except Exception as e:
            logger.error(f"Failed to initialize feature scaler: {e}")
    
    def _extract_essential_features(self, market_data: Dict[str, Any]) -> np.ndarray:
        """Extract essential features for lean AI processing."""
        try:
            start_time = datetime.utcnow()
            
            features = []
            
            # Price change features (lightweight)
            price = market_data.get('price', 0)
            prev_prices = market_data.get('price_history', [price])
            
            if len(prev_prices) >= 15:
                features.extend([
                    (price - prev_prices[-1]) / prev_prices[-1] if prev_prices[-1] > 0 else 0,  # 1m change
                    (price - prev_prices[-5]) / prev_prices[-5] if prev_prices[-5] > 0 else 0,  # 5m change
                    (price - prev_prices[-15]) / prev_prices[-15] if prev_prices[-15] > 0 else 0  # 15m change
                ])
            else:
                features.extend([0, 0, 0])
            
            # Volume ratio
            volume = market_data.get('volume', 0)
            avg_volume = market_data.get('avg_volume', volume)
            volume_ratio = volume / avg_volume if avg_volume > 0 else 1
            features.append(volume_ratio)
            
            # Volatility (simplified calculation)
            if len(prev_prices) >= 60:
                price_changes = np.diff(prev_prices[-60:])
                volatility = np.std(price_changes) if len(price_changes) > 0 else 0
            else:
                volatility = 0
            features.append(volatility)
            
            # Correlation features (simplified)
            spy_price = market_data.get('spy_price', price)
            qqq_price = market_data.get('qqq_price', price)
            iwm_price = market_data.get('iwm_price', price)
            
            # Simple correlation approximation
            correlation_spy_qqq = 0.8 + np.random.normal(0, 0.1)  # Mock correlation
            correlation_spy_iwm = 0.7 + np.random.normal(0, 0.1)  # Mock correlation
            features.extend([correlation_spy_qqq, correlation_spy_iwm])
            
            # VIX features
            vix_level = market_data.get('vix', 20)
            vix_change = market_data.get('vix_change', 0)
            features.extend([vix_level, vix_change])
            
            # Time features
            current_time = datetime.utcnow()
            market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
            time_to_close = (market_close - current_time).total_seconds() / 3600  # Hours
            features.append(max(0, time_to_close))
            
            # Market regime (simplified)
            if vix_level < 15:
                market_regime = 0  # Low volatility
            elif vix_level < 25:
                market_regime = 1  # Normal volatility
            else:
                market_regime = 2  # High volatility
            features.append(market_regime)
            
            # Momentum score (simplified)
            momentum_score = sum(features[:3])  # Sum of price changes
            features.append(momentum_score)
            
            # Ensure we have the right number of features
            while len(features) < len(self.essential_features):
                features.append(0)
            
            features = features[:len(self.essential_features)]
            
            # Track computation time
            compute_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.usage_stats.compute_time_ms += compute_time
            self.usage_stats.feature_extractions += 1
            
            return np.array(features).reshape(1, -1)
            
        except Exception as e:
            logger.error(f"Failed to extract features: {e}")
            return np.zeros((1, len(self.essential_features)))
    
    @cache_result(ttl=1800, key_prefix="ai_prediction")
    async def generate_signal_prediction(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate signal prediction with caching for efficiency."""
        try:
            start_time = datetime.utcnow()
            
            # Extract features
            features = self._extract_essential_features(market_data)
            
            # Scale features
            scaled_features = self.feature_scaler.transform(features)
            
            # Generate prediction
            if self.signal_classifier is not None:
                # Predict signal type and confidence
                signal_proba = self.signal_classifier.predict_proba(scaled_features)[0]
                signal_class = self.signal_classifier.predict(scaled_features)[0]
                
                # Map to signal types
                signal_types = ['correlation', 'momentum', 'volatility', 'ai_prediction']
                signal_type = signal_types[signal_class] if signal_class < len(signal_types) else 'ai_prediction'
                
                confidence = float(np.max(signal_proba))
                
                prediction = {
                    'signal_type': signal_type,
                    'confidence': confidence,
                    'timestamp': datetime.utcnow(),
                    'symbol': market_data.get('symbol', 'UNKNOWN'),
                    'features_used': len(self.essential_features),
                    'model_version': 'lean_v1.0'
                }
                
                # Track performance
                compute_time = (datetime.utcnow() - start_time).total_seconds() * 1000
                self.usage_stats.compute_time_ms += compute_time
                self.usage_stats.predictions_today += 1
                
                return prediction
            
            else:
                # Fallback prediction
                return {
                    'signal_type': 'ai_prediction',
                    'confidence': 0.5,
                    'timestamp': datetime.utcnow(),
                    'symbol': market_data.get('symbol', 'UNKNOWN'),
                    'features_used': 0,
                    'model_version': 'fallback'
                }
                
        except Exception as e:
            logger.error(f"Failed to generate signal prediction: {e}")
            return {
                'signal_type': 'error',
                'confidence': 0.0,
                'timestamp': datetime.utcnow(),
                'symbol': market_data.get('symbol', 'UNKNOWN'),
                'error': str(e)
            }
    
    @cache_result(ttl=3600, key_prefix="volatility_prediction")
    async def predict_volatility(self, market_data: Dict[str, Any]) -> float:
        """Predict volatility with caching."""
        try:
            features = self._extract_essential_features(market_data)
            scaled_features = self.feature_scaler.transform(features)
            
            if self.volatility_predictor is not None:
                volatility = self.volatility_predictor.predict(scaled_features)[0]
                return max(0.0, float(volatility))
            
            # Fallback to current VIX level
            return market_data.get('vix', 20.0) / 100.0
            
        except Exception as e:
            logger.error(f"Failed to predict volatility: {e}")
            return 0.2  # Default 20% volatility
    
    @cache_result(ttl=600, key_prefix="strategy_recommendation")
    async def recommend_strategy(self, market_data: Dict[str, Any], signal: Dict[str, Any]) -> str:
        """Recommend optimal strategy based on market conditions."""
        try:
            features = self._extract_essential_features(market_data)
            scaled_features = self.feature_scaler.transform(features)
            
            if self.strategy_selector is not None:
                strategy_idx = self.strategy_selector.predict(scaled_features)[0]
                
                strategies = [
                    'iron_condor', 'bull_call_spread', 'bear_put_spread',
                    'long_straddle', 'long_strangle', 'iron_butterfly',
                    'short_straddle'
                ]
                
                if 0 <= strategy_idx < len(strategies):
                    return strategies[strategy_idx]
            
            # Fallback strategy selection based on signal type and market conditions
            signal_type = signal.get('signal_type', 'ai_prediction')
            confidence = signal.get('confidence', 0.5)
            vix = market_data.get('vix', 20)
            
            if signal_type == 'correlation' and confidence > 0.7:
                return 'iron_condor'
            elif signal_type == 'momentum' and confidence > 0.75:
                if vix < 20:
                    return 'bull_call_spread'
                else:
                    return 'bear_put_spread'
            elif signal_type == 'volatility':
                if vix > 25:
                    return 'long_straddle'
                else:
                    return 'iron_butterfly'
            else:
                return 'iron_condor'  # Conservative default
                
        except Exception as e:
            logger.error(f"Failed to recommend strategy: {e}")
            return 'iron_condor'
    
    async def update_models_with_feedback(self, trading_results: List[Dict[str, Any]]) -> None:
        """Update models with trading feedback for continuous learning."""
        try:
            if not trading_results:
                return
            
            start_time = datetime.utcnow()
            
            # Prepare training data
            features_list = []
            labels_list = []
            
            for result in trading_results:
                if 'market_data' in result and 'outcome' in result:
                    features = self._extract_essential_features(result['market_data'])
                    outcome = 1 if result['outcome'] > 0 else 0  # Binary classification
                    
                    features_list.append(features[0])
                    labels_list.append(outcome)
            
            if len(features_list) < ai_optimization.TRAINING_BATCH_SIZE:
                logger.debug(f"Insufficient data for model update: {len(features_list)} samples")
                return
            
            # Convert to numpy arrays
            X = np.array(features_list)
            y = np.array(labels_list)
            
            # Update feature scaler
            self.feature_scaler.partial_fit(X)
            X_scaled = self.feature_scaler.transform(X)
            
            # Update signal classifier
            if self.signal_classifier is not None:
                # For incremental learning, we'll retrain with recent data
                if hasattr(self.signal_classifier, 'partial_fit'):
                    self.signal_classifier.partial_fit(X_scaled, y)
                else:
                    # Retrain with subset of data
                    if len(X_scaled) > 100:
                        X_subset, _, y_subset, _ = train_test_split(
                            X_scaled, y, train_size=100, random_state=42
                        )
                        self.signal_classifier.fit(X_subset, y_subset)
                    else:
                        self.signal_classifier.fit(X_scaled, y)
                
                # Update performance metrics
                y_pred = self.signal_classifier.predict(X_scaled)
                self.model_performance['signal_classifier'].accuracy = accuracy_score(y, y_pred)
                self.model_performance['signal_classifier'].last_updated = datetime.utcnow()
                self.model_performance['signal_classifier'].training_samples += len(y)
            
            # Cache updated models
            await self._cache_models()
            
            # Track usage
            compute_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            self.usage_stats.compute_time_ms += compute_time
            self.usage_stats.model_updates_today += 1
            
            logger.info(f"Updated models with {len(trading_results)} feedback samples")
            
        except Exception as e:
            logger.error(f"Failed to update models with feedback: {e}")
    
    async def _cache_models(self) -> None:
        """Cache models for persistence and quick loading."""
        try:
            models_dict = {
                'signal_classifier': self.signal_classifier,
                'volatility_predictor': self.volatility_predictor,
                'correlation_predictor': self.correlation_predictor,
                'strategy_selector': self.strategy_selector
            }
            
            # Cache with compression for efficiency
            await lean_cache_manager.set("ai_models", models_dict, ttl=86400)  # 24 hours
            await lean_cache_manager.set("feature_scaler", self.feature_scaler, ttl=86400)
            
            logger.debug("Cached updated models")
            
        except Exception as e:
            logger.error(f"Failed to cache models: {e}")
    
    async def get_model_performance(self) -> Dict[str, Any]:
        """Get model performance metrics."""
        try:
            performance_dict = {}
            
            for model_name, performance in self.model_performance.items():
                performance_dict[model_name] = {
                    'accuracy': round(performance.accuracy, 4),
                    'precision': round(performance.precision, 4),
                    'recall': round(performance.recall, 4),
                    'f1_score': round(performance.f1_score, 4),
                    'last_updated': performance.last_updated.isoformat() if performance.last_updated else None,
                    'training_samples': performance.training_samples,
                    'prediction_count': performance.prediction_count
                }
            
            return {
                'model_performance': performance_dict,
                'usage_stats': {
                    'predictions_today': self.usage_stats.predictions_today,
                    'model_updates_today': self.usage_stats.model_updates_today,
                    'feature_extractions': self.usage_stats.feature_extractions,
                    'cache_hits': self.usage_stats.cache_hits,
                    'cache_misses': self.usage_stats.cache_misses,
                    'avg_compute_time_ms': round(
                        self.usage_stats.compute_time_ms / max(1, self.usage_stats.predictions_today), 2
                    )
                },
                'configuration': {
                    'max_features': self.max_features,
                    'batch_size': self.batch_size,
                    'model_cache_size': self.model_cache_size,
                    'prediction_cache_ttl': self.prediction_cache_ttl,
                    'essential_features_count': len(self.essential_features)
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to get model performance: {e}")
            return {}
    
    async def _model_monitoring_loop(self) -> None:
        """Monitor model performance and trigger updates when needed."""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour
                
                # Check if models need updating
                current_time = datetime.utcnow()
                
                for model_name, performance in self.model_performance.items():
                    if performance.last_updated:
                        time_since_update = (current_time - performance.last_updated).total_seconds()
                        
                        if time_since_update > self.model_update_interval:
                            logger.info(f"Model {model_name} needs updating")
                            # Could trigger model retraining here
                    
                    # Check performance degradation
                    if performance.accuracy < 0.6 and performance.training_samples > 100:
                        logger.warning(f"Model {model_name} performance degraded: {performance.accuracy}")
                
            except Exception as e:
                logger.error(f"Model monitoring error: {e}")
                await asyncio.sleep(300)
    
    async def _usage_tracking_loop(self) -> None:
        """Track usage statistics for cost optimization."""
        while True:
            try:
                await asyncio.sleep(3600)  # Reset hourly
                
                # Log usage statistics
                stats = await self.get_model_performance()
                logger.info(f"AI usage stats: {stats.get('usage_stats', {})}")
                
                # Reset daily counters at midnight
                current_time = datetime.utcnow()
                if current_time.hour == 0 and current_time.minute < 5:
                    self.usage_stats.predictions_today = 0
                    self.usage_stats.model_updates_today = 0
                    self.usage_stats.feature_extractions = 0
                    self.usage_stats.compute_time_ms = 0.0
                
            except Exception as e:
                logger.error(f"Usage tracking error: {e}")
                await asyncio.sleep(300)
    
    async def close(self) -> None:
        """Close AI service and save models."""
        try:
            # Cache final model state
            await self._cache_models()
            
            logger.info("Lean AI service closed")
            
        except Exception as e:
            logger.error(f"Error closing AI service: {e}")


# Global lean AI service instance
lean_ai_service = LeanAIService()

