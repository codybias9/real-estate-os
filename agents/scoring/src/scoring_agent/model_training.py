"""LightGBM model training for property scoring

Trains gradient boosting model to predict "bird-dog score" (0-100).
"""
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import numpy as np
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
import joblib
import json
import os

logger = logging.getLogger(__name__)


class ModelTrainer:
    """
    LightGBM model trainer for property scoring

    Features:
    - Train gradient boosting model
    - Hyperparameter tuning
    - Cross-validation
    - Feature importance analysis
    - Model versioning
    - Performance metrics
    """

    DEFAULT_PARAMS = {
        'objective': 'regression',
        'metric': 'rmse',
        'boosting_type': 'gbdt',
        'num_leaves': 31,
        'learning_rate': 0.05,
        'feature_fraction': 0.9,
        'bagging_fraction': 0.8,
        'bagging_freq': 5,
        'verbose': -1,
        'min_data_in_leaf': 20,
        'max_depth': 7,
    }

    def __init__(self, params: Optional[Dict] = None):
        """
        Initialize model trainer

        Args:
            params: LightGBM parameters (uses defaults if not provided)
        """
        self.params = params or self.DEFAULT_PARAMS.copy()
        self.model = None
        self.feature_names = None
        self.training_history = []

    def train(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str],
        validation_split: float = 0.2,
        num_boost_round: int = 1000,
        early_stopping_rounds: int = 50
    ) -> Dict[str, Any]:
        """
        Train LightGBM model

        Args:
            X: Feature matrix (n_samples, n_features)
            y: Target values (n_samples,)
            feature_names: List of feature names
            validation_split: Fraction of data for validation
            num_boost_round: Maximum boosting rounds
            early_stopping_rounds: Stop if no improvement

        Returns:
            Dictionary with training metrics
        """
        logger.info("Starting model training...")
        logger.info(f"Training samples: {len(X)}")
        logger.info(f"Features: {len(feature_names)}")

        self.feature_names = feature_names

        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y,
            test_size=validation_split,
            random_state=42
        )

        logger.info(f"Train set: {len(X_train)}, Validation set: {len(X_val)}")

        # Create datasets
        train_data = lgb.Dataset(
            X_train,
            label=y_train,
            feature_name=feature_names
        )

        val_data = lgb.Dataset(
            X_val,
            label=y_val,
            feature_name=feature_names,
            reference=train_data
        )

        # Train model
        callbacks = [
            lgb.log_evaluation(period=100),
            lgb.early_stopping(stopping_rounds=early_stopping_rounds)
        ]

        self.model = lgb.train(
            self.params,
            train_data,
            num_boost_round=num_boost_round,
            valid_sets=[train_data, val_data],
            valid_names=['train', 'valid'],
            callbacks=callbacks
        )

        logger.info(f"Training completed. Best iteration: {self.model.best_iteration}")

        # Evaluate model
        metrics = self.evaluate(X_val, y_val)

        logger.info("Training Metrics:")
        logger.info(f"  RMSE: {metrics['rmse']:.2f}")
        logger.info(f"  MAE: {metrics['mae']:.2f}")
        logger.info(f"  R²: {metrics['r2']:.4f}")

        # Store training record
        training_record = {
            'timestamp': datetime.now().isoformat(),
            'n_samples': len(X),
            'n_features': len(feature_names),
            'best_iteration': self.model.best_iteration,
            'params': self.params,
            'metrics': metrics
        }

        self.training_history.append(training_record)

        return training_record

    def evaluate(self, X: np.ndarray, y: np.ndarray) -> Dict[str, float]:
        """
        Evaluate model performance

        Args:
            X: Feature matrix
            y: True target values

        Returns:
            Dictionary with evaluation metrics
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        # Predict
        y_pred = self.model.predict(X)

        # Calculate metrics
        metrics = {
            'rmse': float(np.sqrt(mean_squared_error(y, y_pred))),
            'mae': float(mean_absolute_error(y, y_pred)),
            'r2': float(r2_score(y, y_pred)),
            'mean_target': float(np.mean(y)),
            'std_target': float(np.std(y)),
            'mean_pred': float(np.mean(y_pred)),
            'std_pred': float(np.std(y_pred))
        }

        return metrics

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        Make predictions

        Args:
            X: Feature matrix

        Returns:
            Predicted scores
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        return self.model.predict(X)

    def get_feature_importance(self) -> Dict[str, float]:
        """
        Get feature importance scores

        Returns:
            Dictionary mapping feature names to importance
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        importance = self.model.feature_importance(importance_type='gain')

        return dict(zip(self.feature_names, importance.tolist()))

    def save_model(self, path: str, metadata: Optional[Dict] = None):
        """
        Save model to disk

        Args:
            path: File path (without extension)
            metadata: Additional metadata to save
        """
        if self.model is None:
            raise ValueError("Model not trained yet")

        # Save LightGBM model
        model_path = f"{path}.txt"
        self.model.save_model(model_path)

        logger.info(f"Model saved to {model_path}")

        # Save metadata
        meta_path = f"{path}_metadata.json"
        metadata_dict = {
            'feature_names': self.feature_names,
            'params': self.params,
            'best_iteration': self.model.best_iteration,
            'training_history': self.training_history,
            'feature_importance': self.get_feature_importance(),
            **(metadata or {})
        }

        with open(meta_path, 'w') as f:
            json.dump(metadata_dict, f, indent=2)

        logger.info(f"Metadata saved to {meta_path}")

    def load_model(self, path: str):
        """
        Load model from disk

        Args:
            path: File path (without extension)
        """
        # Load LightGBM model
        model_path = f"{path}.txt"
        self.model = lgb.Booster(model_file=model_path)

        logger.info(f"Model loaded from {model_path}")

        # Load metadata
        meta_path = f"{path}_metadata.json"
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                metadata = json.load(f)

            self.feature_names = metadata.get('feature_names')
            self.params = metadata.get('params', self.DEFAULT_PARAMS)
            self.training_history = metadata.get('training_history', [])

            logger.info(f"Metadata loaded from {meta_path}")

    def tune_hyperparameters(
        self,
        X: np.ndarray,
        y: np.ndarray,
        feature_names: List[str],
        n_trials: int = 50
    ) -> Dict[str, Any]:
        """
        Hyperparameter tuning using Optuna

        Args:
            X: Feature matrix
            y: Target values
            feature_names: List of feature names
            n_trials: Number of optimization trials

        Returns:
            Best parameters and metrics
        """
        try:
            import optuna
            from optuna.samplers import TPESampler
        except ImportError:
            logger.error("Optuna not installed. Install with: pip install optuna")
            return {}

        logger.info(f"Starting hyperparameter tuning ({n_trials} trials)...")

        self.feature_names = feature_names

        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        def objective(trial):
            """Optuna objective function"""
            params = {
                'objective': 'regression',
                'metric': 'rmse',
                'boosting_type': 'gbdt',
                'num_leaves': trial.suggest_int('num_leaves', 20, 100),
                'learning_rate': trial.suggest_float('learning_rate', 0.01, 0.3),
                'feature_fraction': trial.suggest_float('feature_fraction', 0.5, 1.0),
                'bagging_fraction': trial.suggest_float('bagging_fraction', 0.5, 1.0),
                'bagging_freq': trial.suggest_int('bagging_freq', 1, 10),
                'min_data_in_leaf': trial.suggest_int('min_data_in_leaf', 10, 100),
                'max_depth': trial.suggest_int('max_depth', 3, 12),
                'verbose': -1
            }

            # Create datasets
            train_data = lgb.Dataset(X_train, label=y_train, feature_name=feature_names)
            val_data = lgb.Dataset(X_val, label=y_val, feature_name=feature_names, reference=train_data)

            # Train
            model = lgb.train(
                params,
                train_data,
                num_boost_round=1000,
                valid_sets=[val_data],
                callbacks=[lgb.early_stopping(stopping_rounds=50), lgb.log_evaluation(period=0)]
            )

            # Evaluate
            y_pred = model.predict(X_val)
            rmse = np.sqrt(mean_squared_error(y_val, y_pred))

            return rmse

        # Run optimization
        study = optuna.create_study(
            direction='minimize',
            sampler=TPESampler(seed=42)
        )

        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

        logger.info(f"Best RMSE: {study.best_value:.2f}")
        logger.info(f"Best params: {study.best_params}")

        # Update params with best found
        self.params.update(study.best_params)

        return {
            'best_params': study.best_params,
            'best_rmse': study.best_value,
            'n_trials': n_trials
        }


class SyntheticDataGenerator:
    """
    Generate synthetic training data for model development

    In production, this would be replaced with:
    - Historical sales data with known outcomes
    - Expert-labeled examples
    - User feedback data
    """

    @staticmethod
    def generate_synthetic_dataset(n_samples: int = 1000) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate synthetic property data for training

        Creates realistic-looking features and targets with known patterns:
        - Lower price per sqft = higher score
        - Undervalued properties = higher score
        - Better locations = higher score
        - Newer properties = slight boost

        Args:
            n_samples: Number of samples to generate

        Returns:
            Tuple of (X features, y targets)
        """
        np.random.seed(42)

        # Generate features (35 features as defined in feature engineering)
        X = np.zeros((n_samples, 35))

        # Property characteristics
        X[:, 0] = np.random.normal(2000, 800, n_samples)  # square_footage
        X[:, 1] = np.random.choice([2, 3, 4, 5], n_samples)  # bedrooms
        X[:, 2] = np.random.choice([1.5, 2.0, 2.5, 3.0], n_samples)  # bathrooms
        X[:, 3] = np.random.normal(6000, 2000, n_samples)  # lot_size_sqft
        X[:, 4] = np.random.uniform(0, 70, n_samples)  # age_years

        # Financial features
        X[:, 8] = np.random.normal(400000, 150000, n_samples)  # listing_price
        X[:, 9] = X[:, 8] * np.random.uniform(0.8, 1.2, n_samples)  # assessed_value
        X[:, 10] = X[:, 8] * np.random.uniform(0.9, 1.1, n_samples)  # market_value

        # Calculate derived features
        X[:, 5] = X[:, 8] / X[:, 0]  # price_per_sqft
        X[:, 6] = X[:, 1] / X[:, 2]  # bed_bath_ratio
        X[:, 7] = X[:, 3] / X[:, 0]  # lot_to_building_ratio

        # More financial
        X[:, 11] = X[:, 9] / np.maximum(X[:, 10], 1)  # assessed_to_market_ratio
        X[:, 12] = X[:, 8] / np.maximum(X[:, 9], 1)  # listing_to_assessed_ratio
        X[:, 13] = X[:, 8] / np.maximum(X[:, 10], 1)  # listing_to_market_ratio
        X[:, 14] = np.random.normal(5000, 2000, n_samples)  # annual_tax
        X[:, 15] = X[:, 14] / np.maximum(X[:, 9], 1)  # tax_rate
        X[:, 16] = X[:, 10]  # estimated_equity

        # Temporal
        X[:, 17] = np.random.uniform(0, 20, n_samples)  # years_since_last_sale
        X[:, 18] = X[:, 8] * np.random.uniform(0.5, 0.9, n_samples)  # last_sale_price
        X[:, 19] = X[:, 8] - X[:, 18]  # price_appreciation
        X[:, 20] = np.random.normal(0.05, 0.03, n_samples)  # annual_appreciation_rate

        # Market
        X[:, 21] = np.random.uniform(0, 180, n_samples)  # days_on_market
        X[:, 22] = np.random.choice([0, 1], n_samples, p=[0.3, 0.7])  # listing_status_active
        X[:, 23] = np.random.choice([0, 1], n_samples, p=[0.3, 0.7])  # property_type_single_family
        X[:, 24] = np.random.choice([0, 1], n_samples, p=[0.8, 0.2])  # property_type_condo
        X[:, 25] = np.random.choice([0, 1], n_samples, p=[0.9, 0.1])  # property_type_townhouse

        # Location (Census data)
        X[:, 26] = np.random.normal(30000, 10000, n_samples)  # zip_population
        X[:, 27] = np.random.normal(70000, 20000, n_samples)  # zip_median_income
        X[:, 28] = np.random.normal(350000, 100000, n_samples)  # zip_median_home_value
        X[:, 29] = np.random.uniform(0.5, 0.8, n_samples)  # zip_owner_occupied_rate
        X[:, 30] = np.random.uniform(0.03, 0.10, n_samples)  # zip_unemployment_rate

        # Derived features
        X[:, 31] = X[:, 27] / np.maximum(X[:, 8], 1)  # income_to_price_ratio
        X[:, 32] = X[:, 8] / np.maximum(X[:, 28], 1)  # relative_price_in_zip
        X[:, 33] = (X[:, 8] < X[:, 9] * 0.9).astype(float)  # is_undervalued
        X[:, 34] = np.maximum(X[:, 20], 0)  # potential_roi

        # Generate target scores (bird-dog score 0-100)
        # Score formula: based on multiple factors
        y = np.zeros(n_samples)

        # Base score
        y += 50

        # Price per sqft (lower is better)
        avg_price_per_sqft = np.median(X[:, 5])
        y += (avg_price_per_sqft - X[:, 5]) / avg_price_per_sqft * 15

        # Undervalued (big bonus)
        y += X[:, 33] * 20

        # Good location (higher income area)
        y += (X[:, 27] / np.median(X[:, 27]) - 1) * 10

        # Newer property (slight bonus)
        y += (70 - X[:, 4]) / 70 * 5

        # Lower days on market (indicates demand)
        y += (180 - X[:, 21]) / 180 * 5

        # Add some noise
        y += np.random.normal(0, 5, n_samples)

        # Clip to 0-100
        y = np.clip(y, 0, 100)

        return X, y
