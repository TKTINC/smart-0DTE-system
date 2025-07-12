"""
Smart-0DTE-System AI Learning Service

This module implements machine learning capabilities that learn from daily market data,
trading performance, and pattern recognition to continuously improve signal accuracy.
"""

import asyncio
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
import pickle
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
from sklearn.cluster import KMeans
import joblib

from app.core.config import settings
from app.core.redis_client import market_data_cache
from app.core.influxdb_client import market_data_influx
from app.core.database import db_manager
from app.models.market_data_models import MarketDataSnapshot, OptionsChain
from app.models.signal_models import Signal, SignalPerformance
from app.models.trading_models import Trade, TradeLeg

logger = logging.getLogger(__name__)


class AILearningService:
    """
    AI Learning Service that continuously learns from market data and trading performance
    to improve signal generation and strategy selection over time.
    """
    
    def __init__(self):
        self.is_running = False
        self.models_dir = Path("app/data/models")
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        # ML Models
        self.models = {
            'signal_classifier': None,      # Predicts signal success probability
            'volatility_predictor': None,   # Predicts next-period volatility
            'correlation_predictor': None,  # Predicts correlation changes
            'regime_classifier': None,      # Classifies market regimes
            'strategy_selector': None,      # Selects optimal strategy
            'risk_predictor': None         # Predicts risk metrics
        }
        
        # Feature scalers
        self.scalers = {}
        
        # Learning parameters
        self.learning_config = {
            'retrain_frequency_days': 7,    # Retrain models weekly
            'min_samples_for_training': 100,
            'feature_lookback_days': 30,
            'performance_lookback_days': 90,
            'model_validation_split': 0.2
        }
        
        # Performance tracking
        self.model_performance = {}
        self.learning_history = []
        
        # Feature engineering parameters
        self.feature_config = {
            'price_features': ['returns', 'volatility', 'momentum', 'rsi', 'bollinger'],
            'volume_features': ['volume_ratio', 'volume_trend', 'volume_spike'],
            'correlation_features': ['correlation_change', 'correlation_stability'],
            'options_features': ['iv_rank', 'put_call_ratio', 'gamma_exposure'],
            'regime_features': ['vix_level', 'vix_change', 'regime_stability']
        }
    
    async def initialize(self) -> None:
        """Initialize AI Learning Service."""
        try:
            # Load existing models if available
            await self._load_models()
            
            # Initialize feature scalers
            await self._initialize_scalers()
            
            logger.info("AI Learning Service initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize AI Learning Service: {e}")
            raise
    
    async def start_learning(self) -> None:
        """Start AI learning processes."""
        try:
            self.is_running = True
            
            # Start background learning tasks
            asyncio.create_task(self._continuous_learning_loop())
            asyncio.create_task(self._real_time_feature_extraction())
            asyncio.create_task(self._model_performance_monitoring())
            asyncio.create_task(self._adaptive_parameter_tuning())
            
            logger.info("AI learning processes started")
            
        except Exception as e:
            logger.error(f"Failed to start AI learning: {e}")
            raise
    
    async def stop_learning(self) -> None:
        """Stop AI learning processes."""
        try:
            self.is_running = False
            
            # Save models before stopping
            await self._save_models()
            
            logger.info("AI learning processes stopped")
            
        except Exception as e:
            logger.error(f"Error stopping AI learning: {e}")
    
    async def _continuous_learning_loop(self) -> None:
        """Main continuous learning loop that retrains models periodically."""
        while self.is_running:
            try:
                # Check if it's time to retrain models
                should_retrain = await self._should_retrain_models()
                
                if should_retrain:
                    logger.info("Starting model retraining...")
                    
                    # Collect training data
                    training_data = await self._collect_training_data()
                    
                    if training_data and len(training_data) >= self.learning_config['min_samples_for_training']:
                        # Retrain all models
                        await self._retrain_models(training_data)
                        
                        # Evaluate model performance
                        await self._evaluate_models(training_data)
                        
                        # Save updated models
                        await self._save_models()
                        
                        logger.info("Model retraining completed successfully")
                    else:
                        logger.warning("Insufficient training data for model retraining")
                
                # Wait before next check (daily)
                await asyncio.sleep(24 * 3600)
                
            except Exception as e:
                logger.error(f"Error in continuous learning loop: {e}")
                await asyncio.sleep(3600)  # Wait 1 hour on error
    
    async def _should_retrain_models(self) -> bool:
        """Determine if models should be retrained."""
        try:
            # Check last training date
            last_training = await market_data_cache.redis.get('last_model_training')
            
            if not last_training:
                return True
            
            last_training_date = datetime.fromisoformat(last_training)
            days_since_training = (datetime.utcnow() - last_training_date).days
            
            # Retrain if enough time has passed
            if days_since_training >= self.learning_config['retrain_frequency_days']:
                return True
            
            # Also retrain if model performance has degraded
            performance_degraded = await self._check_performance_degradation()
            
            return performance_degraded
            
        except Exception as e:
            logger.error(f"Error checking retrain condition: {e}")
            return False
    
    async def _check_performance_degradation(self) -> bool:
        """Check if model performance has degraded significantly."""
        try:
            # Get recent signal performance
            recent_performance = await self._get_recent_signal_performance()
            
            if not recent_performance:
                return False
            
            # Compare with historical baseline
            baseline_accuracy = self.model_performance.get('signal_classifier', {}).get('accuracy', 0.6)
            recent_accuracy = recent_performance.get('accuracy', 0.0)
            
            # Retrain if accuracy dropped by more than 10%
            return recent_accuracy < (baseline_accuracy * 0.9)
            
        except Exception as e:
            logger.error(f"Error checking performance degradation: {e}")
            return False
    
    async def _collect_training_data(self) -> Optional[pd.DataFrame]:
        """Collect and prepare training data from historical records."""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=self.learning_config['feature_lookback_days'])
            
            # Collect market data
            market_data = await self._collect_market_data(start_date, end_date)
            
            # Collect signal data
            signal_data = await self._collect_signal_data(start_date, end_date)
            
            # Collect trading performance data
            trading_data = await self._collect_trading_data(start_date, end_date)
            
            # Combine and engineer features
            training_df = await self._engineer_features(market_data, signal_data, trading_data)
            
            return training_df
            
        except Exception as e:
            logger.error(f"Error collecting training data: {e}")
            return None
    
    async def _collect_market_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Collect historical market data."""
        try:
            all_data = []
            
            for symbol in settings.SUPPORTED_TICKERS:
                # Get market data from InfluxDB
                historical_data = market_data_influx.get_market_data_history(
                    symbol, start_date, end_date, "2m"
                )
                
                if historical_data:
                    df = pd.DataFrame(historical_data)
                    df['symbol'] = symbol
                    all_data.append(df)
            
            if all_data:
                combined_df = pd.concat(all_data, ignore_index=True)
                return combined_df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error collecting market data: {e}")
            return pd.DataFrame()
    
    async def _collect_signal_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Collect historical signal data."""
        try:
            # This would query the signals table from the database
            # For now, return empty DataFrame
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error collecting signal data: {e}")
            return pd.DataFrame()
    
    async def _collect_trading_data(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Collect historical trading performance data."""
        try:
            # This would query the trades table from the database
            # For now, return empty DataFrame
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error collecting trading data: {e}")
            return pd.DataFrame()
    
    async def _engineer_features(
        self,
        market_data: pd.DataFrame,
        signal_data: pd.DataFrame,
        trading_data: pd.DataFrame
    ) -> pd.DataFrame:
        """Engineer features for machine learning."""
        try:
            if market_data.empty:
                return pd.DataFrame()
            
            features_list = []
            
            for symbol in settings.SUPPORTED_TICKERS:
                symbol_data = market_data[market_data['symbol'] == symbol].copy()
                
                if len(symbol_data) < 20:  # Need minimum data points
                    continue
                
                # Sort by timestamp
                symbol_data = symbol_data.sort_values('_time')
                
                # Price-based features
                symbol_data['returns'] = symbol_data['_value'].pct_change()
                symbol_data['volatility'] = symbol_data['returns'].rolling(20).std()
                symbol_data['momentum'] = symbol_data['_value'].pct_change(10)
                
                # RSI calculation
                symbol_data['rsi'] = self._calculate_rsi(symbol_data['_value'])
                
                # Bollinger Bands
                symbol_data['bb_upper'], symbol_data['bb_lower'] = self._calculate_bollinger_bands(symbol_data['_value'])
                symbol_data['bb_position'] = (symbol_data['_value'] - symbol_data['bb_lower']) / (symbol_data['bb_upper'] - symbol_data['bb_lower'])
                
                # Volume features (if available)
                if 'volume' in symbol_data.columns:
                    symbol_data['volume_ratio'] = symbol_data['volume'] / symbol_data['volume'].rolling(20).mean()
                    symbol_data['volume_trend'] = symbol_data['volume'].pct_change(5)
                
                # Time-based features
                symbol_data['hour'] = pd.to_datetime(symbol_data['_time']).dt.hour
                symbol_data['minute'] = pd.to_datetime(symbol_data['_time']).dt.minute
                symbol_data['day_of_week'] = pd.to_datetime(symbol_data['_time']).dt.dayofweek
                
                # Add symbol identifier
                symbol_data['symbol'] = symbol
                
                features_list.append(symbol_data)
            
            if features_list:
                combined_features = pd.concat(features_list, ignore_index=True)
                
                # Add cross-symbol features
                combined_features = await self._add_cross_symbol_features(combined_features)
                
                # Add regime features
                combined_features = await self._add_regime_features(combined_features)
                
                # Drop NaN values
                combined_features = combined_features.dropna()
                
                return combined_features
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Error engineering features: {e}")
            return pd.DataFrame()
    
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI indicator."""
        try:
            delta = prices.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            return rsi
        except:
            return pd.Series(index=prices.index, dtype=float)
    
    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series]:
        """Calculate Bollinger Bands."""
        try:
            sma = prices.rolling(window=period).mean()
            std = prices.rolling(window=period).std()
            upper_band = sma + (std * std_dev)
            lower_band = sma - (std * std_dev)
            return upper_band, lower_band
        except:
            return pd.Series(index=prices.index, dtype=float), pd.Series(index=prices.index, dtype=float)
    
    async def _add_cross_symbol_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add cross-symbol correlation and divergence features."""
        try:
            # Get correlation data
            correlation_matrix = await market_data_cache.redis.get('correlation_matrix')
            
            if correlation_matrix:
                # Add correlation features for each timestamp
                for pair, corr_data in correlation_matrix.items():
                    if isinstance(corr_data, dict):
                        df[f'correlation_{pair}'] = corr_data.get('current', 0)
            
            return df
            
        except Exception as e:
            logger.error(f"Error adding cross-symbol features: {e}")
            return df
    
    async def _add_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add market regime features."""
        try:
            # Get regime data
            regime_data = await market_data_cache.redis.get('market_regime')
            
            if regime_data:
                df['vix_level'] = regime_data.get('vix_level', 20)
                df['adaptation_factor'] = regime_data.get('adaptation_factor', 1.0)
                
                # Encode regime type
                regime_type = regime_data.get('regime_type', 'normal_volatility')
                regime_mapping = {
                    'low_volatility': 0,
                    'normal_volatility': 1,
                    'high_volatility': 2,
                    'extreme_volatility': 3
                }
                df['regime_encoded'] = regime_mapping.get(regime_type, 1)
            
            return df
            
        except Exception as e:
            logger.error(f"Error adding regime features: {e}")
            return df
    
    async def _retrain_models(self, training_data: pd.DataFrame) -> None:
        """Retrain all ML models with new data."""
        try:
            # Prepare features and targets
            feature_columns = self._get_feature_columns(training_data)
            X = training_data[feature_columns].fillna(0)
            
            # Scale features
            if 'main_scaler' not in self.scalers:
                self.scalers['main_scaler'] = StandardScaler()
            
            X_scaled = self.scalers['main_scaler'].fit_transform(X)
            
            # Train signal classifier
            await self._train_signal_classifier(X_scaled, training_data)
            
            # Train volatility predictor
            await self._train_volatility_predictor(X_scaled, training_data)
            
            # Train correlation predictor
            await self._train_correlation_predictor(X_scaled, training_data)
            
            # Train regime classifier
            await self._train_regime_classifier(X_scaled, training_data)
            
            # Train strategy selector
            await self._train_strategy_selector(X_scaled, training_data)
            
            # Update last training timestamp
            await market_data_cache.redis.set(
                'last_model_training',
                datetime.utcnow().isoformat(),
                ttl=86400 * 30  # 30 days
            )
            
            logger.info("All models retrained successfully")
            
        except Exception as e:
            logger.error(f"Error retraining models: {e}")
    
    def _get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Get list of feature columns for ML models."""
        feature_columns = []
        
        # Price features
        for feature in ['returns', 'volatility', 'momentum', 'rsi', 'bb_position']:
            if feature in df.columns:
                feature_columns.append(feature)
        
        # Volume features
        for feature in ['volume_ratio', 'volume_trend']:
            if feature in df.columns:
                feature_columns.append(feature)
        
        # Time features
        for feature in ['hour', 'minute', 'day_of_week']:
            if feature in df.columns:
                feature_columns.append(feature)
        
        # Correlation features
        correlation_cols = [col for col in df.columns if col.startswith('correlation_')]
        feature_columns.extend(correlation_cols)
        
        # Regime features
        for feature in ['vix_level', 'adaptation_factor', 'regime_encoded']:
            if feature in df.columns:
                feature_columns.append(feature)
        
        return feature_columns
    
    async def _train_signal_classifier(self, X: np.ndarray, training_data: pd.DataFrame) -> None:
        """Train signal success classifier."""
        try:
            # Create synthetic target for demonstration (would use actual signal performance)
            y = self._create_synthetic_signal_targets(training_data)
            
            if len(y) != len(X):
                return
            
            # Train Random Forest classifier
            self.models['signal_classifier'] = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42,
                class_weight='balanced'
            )
            
            self.models['signal_classifier'].fit(X, y)
            
            # Calculate feature importance
            feature_importance = self.models['signal_classifier'].feature_importances_
            
            logger.info("Signal classifier trained successfully")
            
        except Exception as e:
            logger.error(f"Error training signal classifier: {e}")
    
    async def _train_volatility_predictor(self, X: np.ndarray, training_data: pd.DataFrame) -> None:
        """Train volatility predictor."""
        try:
            # Create target (next period volatility)
            y = training_data['volatility'].shift(-1).fillna(training_data['volatility'].mean())
            
            if len(y) != len(X):
                return
            
            # Train Gradient Boosting regressor
            self.models['volatility_predictor'] = GradientBoostingRegressor(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                random_state=42
            )
            
            self.models['volatility_predictor'].fit(X, y)
            
            logger.info("Volatility predictor trained successfully")
            
        except Exception as e:
            logger.error(f"Error training volatility predictor: {e}")
    
    async def _train_correlation_predictor(self, X: np.ndarray, training_data: pd.DataFrame) -> None:
        """Train correlation change predictor."""
        try:
            # Create synthetic correlation change target
            y = self._create_synthetic_correlation_targets(training_data)
            
            if len(y) != len(X):
                return
            
            # Train logistic regression for correlation direction
            self.models['correlation_predictor'] = LogisticRegression(
                random_state=42,
                max_iter=1000
            )
            
            self.models['correlation_predictor'].fit(X, y)
            
            logger.info("Correlation predictor trained successfully")
            
        except Exception as e:
            logger.error(f"Error training correlation predictor: {e}")
    
    async def _train_regime_classifier(self, X: np.ndarray, training_data: pd.DataFrame) -> None:
        """Train market regime classifier."""
        try:
            # Use regime_encoded as target
            if 'regime_encoded' not in training_data.columns:
                return
            
            y = training_data['regime_encoded']
            
            # Train Random Forest classifier
            self.models['regime_classifier'] = RandomForestClassifier(
                n_estimators=50,
                max_depth=8,
                random_state=42
            )
            
            self.models['regime_classifier'].fit(X, y)
            
            logger.info("Regime classifier trained successfully")
            
        except Exception as e:
            logger.error(f"Error training regime classifier: {e}")
    
    async def _train_strategy_selector(self, X: np.ndarray, training_data: pd.DataFrame) -> None:
        """Train optimal strategy selector."""
        try:
            # Create synthetic strategy targets
            y = self._create_synthetic_strategy_targets(training_data)
            
            if len(y) != len(X):
                return
            
            # Train strategy selector
            self.models['strategy_selector'] = RandomForestClassifier(
                n_estimators=100,
                max_depth=8,
                random_state=42
            )
            
            self.models['strategy_selector'].fit(X, y)
            
            logger.info("Strategy selector trained successfully")
            
        except Exception as e:
            logger.error(f"Error training strategy selector: {e}")
    
    def _create_synthetic_signal_targets(self, df: pd.DataFrame) -> np.ndarray:
        """Create synthetic signal success targets for training."""
        try:
            # Create targets based on future price movements
            targets = []
            
            for i in range(len(df)):
                # Simple logic: signal success if next period return is positive
                if i < len(df) - 1:
                    current_return = df.iloc[i].get('returns', 0)
                    target = 1 if current_return > 0.001 else 0  # 0.1% threshold
                else:
                    target = 0
                
                targets.append(target)
            
            return np.array(targets)
            
        except Exception as e:
            logger.error(f"Error creating synthetic signal targets: {e}")
            return np.zeros(len(df))
    
    def _create_synthetic_correlation_targets(self, df: pd.DataFrame) -> np.ndarray:
        """Create synthetic correlation change targets."""
        try:
            # Create targets based on correlation stability
            targets = []
            
            for i in range(len(df)):
                # Simple logic: predict if correlation will increase
                volatility = df.iloc[i].get('volatility', 0.02)
                target = 1 if volatility < 0.02 else 0  # Low vol = stable correlation
                targets.append(target)
            
            return np.array(targets)
            
        except Exception as e:
            logger.error(f"Error creating synthetic correlation targets: {e}")
            return np.zeros(len(df))
    
    def _create_synthetic_strategy_targets(self, df: pd.DataFrame) -> np.ndarray:
        """Create synthetic strategy selection targets."""
        try:
            # Create targets based on market conditions
            targets = []
            
            strategy_mapping = {
                0: 'bull_call_spread',
                1: 'bear_put_spread', 
                2: 'iron_condor',
                3: 'straddle'
            }
            
            for i in range(len(df)):
                volatility = df.iloc[i].get('volatility', 0.02)
                
                if volatility < 0.015:
                    target = 2  # Iron condor for low vol
                elif volatility > 0.03:
                    target = 3  # Straddle for high vol
                else:
                    momentum = df.iloc[i].get('momentum', 0)
                    target = 0 if momentum > 0 else 1  # Directional spreads
                
                targets.append(target)
            
            return np.array(targets)
            
        except Exception as e:
            logger.error(f"Error creating synthetic strategy targets: {e}")
            return np.zeros(len(df))
    
    async def _real_time_feature_extraction(self) -> None:
        """Extract features from real-time data for model predictions."""
        while self.is_running:
            try:
                # Extract current market features
                current_features = await self._extract_current_features()
                
                if current_features is not None:
                    # Make predictions with trained models
                    predictions = await self._make_predictions(current_features)
                    
                    # Cache predictions for use by other services
                    await market_data_cache.redis.set(
                        'ai_predictions',
                        predictions,
                        ttl=300
                    )
                
                await asyncio.sleep(60)  # Extract features every minute
                
            except Exception as e:
                logger.error(f"Error in real-time feature extraction: {e}")
                await asyncio.sleep(5)
    
    async def _extract_current_features(self) -> Optional[np.ndarray]:
        """Extract features from current market state."""
        try:
            features = {}
            
            # Get current market data for all symbols
            for symbol in settings.SUPPORTED_TICKERS:
                market_data = await market_data_cache.get_market_data(symbol)
                if market_data:
                    # Extract basic features (would need historical data for full features)
                    features[f'{symbol}_price'] = market_data.get('price', 0)
                    features[f'{symbol}_change'] = market_data.get('change_percent', 0)
            
            # Get correlation features
            correlation_matrix = await market_data_cache.redis.get('correlation_matrix')
            if correlation_matrix:
                for pair, corr_data in correlation_matrix.items():
                    if isinstance(corr_data, dict):
                        features[f'correlation_{pair}'] = corr_data.get('current', 0)
            
            # Get regime features
            regime_data = await market_data_cache.redis.get('market_regime')
            if regime_data:
                features['vix_level'] = regime_data.get('vix_level', 20)
                features['adaptation_factor'] = regime_data.get('adaptation_factor', 1.0)
            
            # Convert to array
            if features:
                feature_array = np.array(list(features.values())).reshape(1, -1)
                
                # Scale features if scaler is available
                if 'main_scaler' in self.scalers:
                    # Pad or truncate to match training dimensions
                    expected_features = self.scalers['main_scaler'].n_features_in_
                    current_features = len(features)
                    
                    if current_features < expected_features:
                        # Pad with zeros
                        padding = np.zeros((1, expected_features - current_features))
                        feature_array = np.hstack([feature_array, padding])
                    elif current_features > expected_features:
                        # Truncate
                        feature_array = feature_array[:, :expected_features]
                    
                    feature_array = self.scalers['main_scaler'].transform(feature_array)
                
                return feature_array
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting current features: {e}")
            return None
    
    async def _make_predictions(self, features: np.ndarray) -> Dict[str, Any]:
        """Make predictions using trained models."""
        try:
            predictions = {}
            
            # Signal success probability
            if self.models['signal_classifier'] is not None:
                signal_prob = self.models['signal_classifier'].predict_proba(features)[0]
                predictions['signal_success_probability'] = float(signal_prob[1])
            
            # Volatility prediction
            if self.models['volatility_predictor'] is not None:
                vol_pred = self.models['volatility_predictor'].predict(features)[0]
                predictions['predicted_volatility'] = float(vol_pred)
            
            # Correlation prediction
            if self.models['correlation_predictor'] is not None:
                corr_prob = self.models['correlation_predictor'].predict_proba(features)[0]
                predictions['correlation_increase_probability'] = float(corr_prob[1])
            
            # Regime prediction
            if self.models['regime_classifier'] is not None:
                regime_pred = self.models['regime_classifier'].predict(features)[0]
                regime_mapping = {0: 'low_volatility', 1: 'normal_volatility', 2: 'high_volatility', 3: 'extreme_volatility'}
                predictions['predicted_regime'] = regime_mapping.get(int(regime_pred), 'normal_volatility')
            
            # Strategy recommendation
            if self.models['strategy_selector'] is not None:
                strategy_pred = self.models['strategy_selector'].predict(features)[0]
                strategy_mapping = {0: 'bull_call_spread', 1: 'bear_put_spread', 2: 'iron_condor', 3: 'straddle'}
                predictions['recommended_strategy'] = strategy_mapping.get(int(strategy_pred), 'bull_call_spread')
            
            predictions['timestamp'] = datetime.utcnow().isoformat()
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error making predictions: {e}")
            return {}
    
    async def _model_performance_monitoring(self) -> None:
        """Monitor model performance and trigger retraining if needed."""
        while self.is_running:
            try:
                # Evaluate recent predictions vs actual outcomes
                performance_metrics = await self._evaluate_recent_performance()
                
                if performance_metrics:
                    # Update performance tracking
                    self.model_performance.update(performance_metrics)
                    
                    # Cache performance metrics
                    await market_data_cache.redis.set(
                        'ai_model_performance',
                        performance_metrics,
                        ttl=3600
                    )
                
                await asyncio.sleep(3600)  # Check every hour
                
            except Exception as e:
                logger.error(f"Error monitoring model performance: {e}")
                await asyncio.sleep(300)
    
    async def _evaluate_recent_performance(self) -> Dict[str, Any]:
        """Evaluate recent model performance."""
        try:
            # This would compare recent predictions with actual outcomes
            # For now, return mock performance metrics
            
            performance = {
                'signal_classifier': {
                    'accuracy': 0.65,
                    'precision': 0.62,
                    'recall': 0.68,
                    'f1_score': 0.65
                },
                'volatility_predictor': {
                    'mae': 0.015,
                    'rmse': 0.022,
                    'r2_score': 0.45
                },
                'strategy_selector': {
                    'accuracy': 0.58,
                    'avg_return': 0.08
                },
                'last_evaluation': datetime.utcnow().isoformat()
            }
            
            return performance
            
        except Exception as e:
            logger.error(f"Error evaluating recent performance: {e}")
            return {}
    
    async def _adaptive_parameter_tuning(self) -> None:
        """Adaptively tune trading parameters based on AI insights."""
        while self.is_running:
            try:
                # Get AI predictions
                predictions = await market_data_cache.redis.get('ai_predictions')
                
                if predictions:
                    # Adjust parameters based on predictions
                    adaptive_params = await self._calculate_adaptive_parameters(predictions)
                    
                    # Cache adaptive parameters
                    await market_data_cache.redis.set(
                        'ai_adaptive_params',
                        adaptive_params,
                        ttl=300
                    )
                
                await asyncio.sleep(300)  # Update every 5 minutes
                
            except Exception as e:
                logger.error(f"Error in adaptive parameter tuning: {e}")
                await asyncio.sleep(60)
    
    async def _calculate_adaptive_parameters(self, predictions: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate adaptive trading parameters based on AI predictions."""
        try:
            adaptive_params = {}
            
            # Adjust confidence threshold based on signal success probability
            signal_prob = predictions.get('signal_success_probability', 0.5)
            base_confidence = settings.DEFAULT_CONFIDENCE_THRESHOLD
            
            if signal_prob > 0.7:
                adaptive_params['confidence_threshold'] = base_confidence * 0.9  # Lower threshold for high-confidence periods
            elif signal_prob < 0.4:
                adaptive_params['confidence_threshold'] = base_confidence * 1.2  # Higher threshold for low-confidence periods
            else:
                adaptive_params['confidence_threshold'] = base_confidence
            
            # Adjust position sizing based on predicted volatility
            predicted_vol = predictions.get('predicted_volatility', 0.02)
            base_position_size = settings.DEFAULT_POSITION_SIZE
            
            if predicted_vol > 0.03:
                adaptive_params['position_size_multiplier'] = 0.8  # Reduce size in high vol
            elif predicted_vol < 0.015:
                adaptive_params['position_size_multiplier'] = 1.1  # Increase size in low vol
            else:
                adaptive_params['position_size_multiplier'] = 1.0
            
            # Strategy preference based on AI recommendation
            recommended_strategy = predictions.get('recommended_strategy', 'bull_call_spread')
            adaptive_params['preferred_strategy'] = recommended_strategy
            
            # Regime-based adjustments
            predicted_regime = predictions.get('predicted_regime', 'normal_volatility')
            if predicted_regime == 'extreme_volatility':
                adaptive_params['emergency_mode'] = True
                adaptive_params['max_positions'] = 3
            else:
                adaptive_params['emergency_mode'] = False
                adaptive_params['max_positions'] = settings.MAX_POSITIONS_PER_USER
            
            adaptive_params['timestamp'] = datetime.utcnow().isoformat()
            
            return adaptive_params
            
        except Exception as e:
            logger.error(f"Error calculating adaptive parameters: {e}")
            return {}
    
    async def _save_models(self) -> None:
        """Save trained models to disk."""
        try:
            for model_name, model in self.models.items():
                if model is not None:
                    model_path = self.models_dir / f"{model_name}.joblib"
                    joblib.dump(model, model_path)
            
            # Save scalers
            for scaler_name, scaler in self.scalers.items():
                scaler_path = self.models_dir / f"{scaler_name}.joblib"
                joblib.dump(scaler, scaler_path)
            
            # Save performance metrics
            performance_path = self.models_dir / "model_performance.json"
            with open(performance_path, 'w') as f:
                json.dump(self.model_performance, f, indent=2)
            
            logger.info("Models saved successfully")
            
        except Exception as e:
            logger.error(f"Error saving models: {e}")
    
    async def _load_models(self) -> None:
        """Load trained models from disk."""
        try:
            for model_name in self.models.keys():
                model_path = self.models_dir / f"{model_name}.joblib"
                if model_path.exists():
                    self.models[model_name] = joblib.load(model_path)
                    logger.info(f"Loaded {model_name} model")
            
            # Load scalers
            scaler_path = self.models_dir / "main_scaler.joblib"
            if scaler_path.exists():
                self.scalers['main_scaler'] = joblib.load(scaler_path)
                logger.info("Loaded main scaler")
            
            # Load performance metrics
            performance_path = self.models_dir / "model_performance.json"
            if performance_path.exists():
                with open(performance_path, 'r') as f:
                    self.model_performance = json.load(f)
                logger.info("Loaded model performance metrics")
            
        except Exception as e:
            logger.error(f"Error loading models: {e}")
    
    async def _initialize_scalers(self) -> None:
        """Initialize feature scalers."""
        try:
            if 'main_scaler' not in self.scalers:
                self.scalers['main_scaler'] = StandardScaler()
            
            logger.info("Scalers initialized")
            
        except Exception as e:
            logger.error(f"Error initializing scalers: {e}")
    
    async def get_ai_predictions(self) -> Dict[str, Any]:
        """Get current AI predictions."""
        try:
            predictions = await market_data_cache.redis.get('ai_predictions')
            return predictions or {}
        except Exception as e:
            logger.error(f"Error getting AI predictions: {e}")
            return {}
    
    async def get_adaptive_parameters(self) -> Dict[str, Any]:
        """Get current adaptive parameters."""
        try:
            params = await market_data_cache.redis.get('ai_adaptive_params')
            return params or {}
        except Exception as e:
            logger.error(f"Error getting adaptive parameters: {e}")
            return {}
    
    async def get_model_performance(self) -> Dict[str, Any]:
        """Get model performance metrics."""
        try:
            performance = await market_data_cache.redis.get('ai_model_performance')
            return performance or self.model_performance
        except Exception as e:
            logger.error(f"Error getting model performance: {e}")
            return {}
    
    async def health_check(self) -> bool:
        """Check AI learning service health."""
        try:
            if not self.is_running:
                return False
            
            # Check if at least some models are loaded
            loaded_models = sum(1 for model in self.models.values() if model is not None)
            
            return loaded_models > 0
            
        except Exception as e:
            logger.error(f"AI Learning Service health check failed: {e}")
            return False


# Global AI learning service instance
ai_learning_service = AILearningService()

