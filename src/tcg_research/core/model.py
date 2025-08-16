"""CatBoost model training and prediction."""

import json
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import structlog
from catboost import CatBoostClassifier, CatBoostRegressor, Pool
from sklearn.metrics import (
    accuracy_score,
    r2_score,
)
from sklearn.model_selection import TimeSeriesSplit
from sqlalchemy.orm import Session

from ..models.database import Card, CardFeature, ModelPrediction
from .features import FeatureEngineer

logger = structlog.get_logger()


class TCGMarketModel:
    """CatBoost model for TCG market prediction."""

    def __init__(self, db_session: Session, model_dir: str = "models") -> None:
        self.db_session = db_session
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)

        self.feature_engineer = FeatureEngineer(db_session)

        # Model instances
        self.return_model = None  # Regression model for return prediction
        self.class_model = None   # Classification model for BUY/WATCH/AVOID

        # Feature configuration
        self.feature_columns = [
            'price_momentum_30d', 'price_momentum_90d', 'price_momentum_180d',
            'active_listings_count', 'listing_turnover_30d', 'ask_sold_spread_pct',
            'price_volatility_30d', 'price_volatility_90d', 'psa_pop_growth_30d',
            'time_since_release_days',
        ]

        self.categorical_features = ['set_type']

        # Model parameters
        self.model_params = {
            'iterations': 1000,
            'learning_rate': 0.1,
            'depth': 6,
            'l2_leaf_reg': 3,
            'bootstrap_type': 'Bayesian',
            'bagging_temperature': 1,
            'od_type': 'Iter',
            'od_wait': 50,
            'random_seed': 42,
            'verbose': False,
        }

    def prepare_training_data(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
        """Prepare training data with walk-forward validation."""
        logger.info("Preparing training data", start_date=start_date.date(), end_date=end_date.date())

        # Get feature data
        df = self.feature_engineer.get_training_data(start_date, end_date)

        if df.empty:
            raise ValueError("No training data available")

        # Sort by date to ensure proper time series order
        df = df.sort_values('feature_date')

        # Prepare features
        X = self._prepare_features(df)

        # Prepare targets
        y_return = df['return_3m']
        y_class = self._create_classification_targets(df['return_3m'])

        logger.info("Training data prepared", samples=len(X), features=len(X.columns))

        return X, y_return, y_class

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare feature matrix."""
        X = df[self.feature_columns + self.categorical_features].copy()

        # Handle missing values
        numeric_cols = self.feature_columns
        X[numeric_cols] = X[numeric_cols].fillna(0)

        # Handle categorical features
        X[self.categorical_features] = X[self.categorical_features].fillna('unknown')

        return X

    def _create_classification_targets(self, returns: pd.Series) -> pd.Series:
        """Create classification targets: BUY(2), WATCH(1), AVOID(0)."""
        y_class = pd.Series(index=returns.index, dtype=int)

        # BUY: >10% return
        y_class[returns > 10] = 2

        # WATCH: -10% to +10% return
        y_class[(returns >= -10) & (returns <= 10)] = 1

        # AVOID: <-10% return
        y_class[returns < -10] = 0

        return y_class

    def train_models(
        self,
        X: pd.DataFrame,
        y_return: pd.Series,
        y_class: pd.Series,
        validation_split: float = 0.2,
    ) -> dict[str, float]:
        """Train both regression and classification models."""
        logger.info("Training models", samples=len(X))

        # Time series split for validation
        n_splits = max(3, int(1 / validation_split))
        tscv = TimeSeriesSplit(n_splits=n_splits)

        # Train regression model
        self.return_model = CatBoostRegressor(**self.model_params)

        reg_scores = []
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y_return.iloc[train_idx], y_return.iloc[val_idx]

            # Create pools
            train_pool = Pool(
                X_train,
                y_train,
                cat_features=self.categorical_features,
            )
            val_pool = Pool(
                X_val,
                y_val,
                cat_features=self.categorical_features,
            )

            # Train
            self.return_model.fit(train_pool, eval_set=val_pool, use_best_model=True)

            # Validate
            y_pred = self.return_model.predict(val_pool)
            score = r2_score(y_val, y_pred)
            reg_scores.append(score)

        # Train final regression model on all data
        full_pool = Pool(X, y_return, cat_features=self.categorical_features)
        self.return_model.fit(full_pool)

        # Train classification model
        self.class_model = CatBoostClassifier(
            **{**self.model_params, 'loss_function': 'MultiClass'},
        )

        class_scores = []
        for train_idx, val_idx in tscv.split(X):
            X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
            y_train, y_val = y_class.iloc[train_idx], y_class.iloc[val_idx]

            # Create pools
            train_pool = Pool(
                X_train,
                y_train,
                cat_features=self.categorical_features,
            )
            val_pool = Pool(
                X_val,
                y_val,
                cat_features=self.categorical_features,
            )

            # Train
            self.class_model.fit(train_pool, eval_set=val_pool, use_best_model=True)

            # Validate
            y_pred = self.class_model.predict(val_pool)
            score = accuracy_score(y_val, y_pred)
            class_scores.append(score)

        # Train final classification model on all data
        full_pool = Pool(X, y_class, cat_features=self.categorical_features)
        self.class_model.fit(full_pool)

        # Calculate metrics
        metrics = {
            'regression_r2_cv': np.mean(reg_scores),
            'classification_accuracy_cv': np.mean(class_scores),
            'training_samples': len(X),
            'feature_count': len(X.columns),
        }

        logger.info("Model training completed", metrics=metrics)

        return metrics

    def predict(self, X: pd.DataFrame) -> pd.DataFrame:
        """Make predictions for given features."""
        if self.return_model is None or self.class_model is None:
            raise ValueError("Models not trained. Call train_models() first.")

        X_prepared = self._prepare_features(X)

        # Create pool
        pool = Pool(X_prepared, cat_features=self.categorical_features)

        # Get predictions
        return_pred = self.return_model.predict(pool)
        class_pred = self.class_model.predict(pool)
        class_proba = self.class_model.predict_proba(pool)

        # Calculate confidence (max probability)
        confidence = np.max(class_proba, axis=1)

        # Create results DataFrame
        results = pd.DataFrame({
            'predicted_return_3m': return_pred,
            'predicted_class': class_pred,
            'confidence': confidence,
            'recommendation': self._class_to_recommendation(class_pred),
            'risk_level': self._calculate_risk_level(return_pred, confidence),
        })

        return results

    def _class_to_recommendation(self, class_pred: np.ndarray) -> list[str]:
        """Convert class predictions to recommendations."""
        mapping = {0: 'AVOID', 1: 'WATCH', 2: 'BUY'}
        return [mapping[int(pred)] for pred in class_pred]

    def _calculate_risk_level(self, returns: np.ndarray, confidence: np.ndarray) -> list[str]:
        """Calculate risk level based on predictions and confidence."""
        risk_levels = []

        for ret, conf in zip(returns, confidence, strict=False):
            if conf < 0.6 or abs(ret) > 20:
                risk_levels.append('HIGH')
            elif abs(ret) > 10:
                risk_levels.append('MEDIUM')
            else:
                risk_levels.append('LOW')

        return risk_levels

    def get_feature_importance(self) -> dict[str, dict[str, float]]:
        """Get feature importance from trained models."""
        if self.return_model is None or self.class_model is None:
            raise ValueError("Models not trained")

        reg_importance = dict(zip(
            self.feature_columns + self.categorical_features,
            self.return_model.get_feature_importance(), strict=False,
        ))

        class_importance = dict(zip(
            self.feature_columns + self.categorical_features,
            self.class_model.get_feature_importance(), strict=False,
        ))

        return {
            'regression': reg_importance,
            'classification': class_importance,
        }

    def save_models(self, version: str) -> None:
        """Save trained models to disk."""
        if self.return_model is None or self.class_model is None:
            raise ValueError("Models not trained")

        # Save models
        reg_path = self.model_dir / f"return_model_{version}.cbm"
        class_path = self.model_dir / f"class_model_{version}.cbm"

        self.return_model.save_model(str(reg_path))
        self.class_model.save_model(str(class_path))

        # Save metadata
        metadata = {
            'version': version,
            'timestamp': datetime.utcnow().isoformat(),
            'feature_columns': self.feature_columns,
            'categorical_features': self.categorical_features,
            'model_params': self.model_params,
        }

        metadata_path = self.model_dir / f"metadata_{version}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)

        logger.info("Models saved", version=version, path=str(self.model_dir))

    def load_models(self, version: str) -> None:
        """Load trained models from disk."""
        reg_path = self.model_dir / f"return_model_{version}.cbm"
        class_path = self.model_dir / f"class_model_{version}.cbm"
        metadata_path = self.model_dir / f"metadata_{version}.json"

        if not all(p.exists() for p in [reg_path, class_path, metadata_path]):
            raise FileNotFoundError(f"Model files not found for version {version}")

        # Load models
        self.return_model = CatBoostRegressor()
        self.return_model.load_model(str(reg_path))

        self.class_model = CatBoostClassifier()
        self.class_model.load_model(str(class_path))

        # Load metadata
        with open(metadata_path) as f:
            metadata = json.load(f)

        self.feature_columns = metadata['feature_columns']
        self.categorical_features = metadata['categorical_features']
        self.model_params = metadata['model_params']

        logger.info("Models loaded", version=version)

    def generate_predictions_for_cards(self, card_ids: list[int] | None = None) -> int:
        """Generate predictions for cards and save to database."""
        if self.return_model is None or self.class_model is None:
            raise ValueError("Models not trained")

        # Get cards to predict
        if card_ids:
            cards = self.db_session.query(Card).filter(Card.id.in_(card_ids)).all()
        else:
            cards = self.db_session.query(Card).all()

        predictions_created = 0
        current_date = datetime.utcnow()
        model_version = f"catboost_{current_date.strftime('%Y%m%d')}"

        for card in cards:
            try:
                # Get latest features for card
                latest_features = self.db_session.query(CardFeature).filter_by(
                    card_id=card.id,
                ).order_by(CardFeature.feature_date.desc()).first()

                if not latest_features:
                    continue

                # Prepare feature data
                feature_data = {
                    'price_momentum_30d': latest_features.price_momentum_30d,
                    'price_momentum_90d': latest_features.price_momentum_90d,
                    'price_momentum_180d': latest_features.price_momentum_180d,
                    'active_listings_count': latest_features.active_listings_count,
                    'listing_turnover_30d': latest_features.listing_turnover_30d,
                    'ask_sold_spread_pct': latest_features.ask_sold_spread_pct,
                    'price_volatility_30d': latest_features.price_volatility_30d,
                    'price_volatility_90d': latest_features.price_volatility_90d,
                    'psa_pop_growth_30d': latest_features.psa_pop_growth_30d,
                    'time_since_release_days': latest_features.time_since_release_days,
                    'set_type': latest_features.set_type,
                }

                X = pd.DataFrame([feature_data])

                # Make prediction
                predictions = self.predict(X)
                pred = predictions.iloc[0]

                # Save prediction
                model_pred = ModelPrediction(
                    card_id=card.id,
                    model_version=model_version,
                    prediction_date=current_date,
                    predicted_return_3m=pred['predicted_return_3m'],
                    confidence=pred['confidence'],
                    recommendation=pred['recommendation'],
                    risk_level=pred['risk_level'],
                    key_features=json.dumps(self._get_key_features(card.id)),
                    rationale=self._generate_rationale(pred, latest_features),
                    price_target_low=self._calculate_price_target(card, pred['predicted_return_3m'], -0.1),
                    price_target_high=self._calculate_price_target(card, pred['predicted_return_3m'], 0.1),
                )

                self.db_session.add(model_pred)
                predictions_created += 1

            except Exception as e:
                logger.error("Prediction failed", card_id=card.id, error=str(e))

        self.db_session.commit()
        logger.info("Predictions generated", count=predictions_created)

        return predictions_created

    def _get_key_features(self, card_id: int) -> dict[str, float]:
        """Get key feature values for a card."""
        # Get feature importance and latest values
        importance = self.get_feature_importance()
        reg_importance = importance['regression']

        # Return top 5 most important features
        top_features = sorted(reg_importance.items(), key=lambda x: x[1], reverse=True)[:5]

        return dict(top_features)

    def _generate_rationale(self, prediction: pd.Series, features: CardFeature) -> str:
        """Generate human-readable rationale for prediction."""
        rationale_parts = []

        recommendation = prediction['recommendation']
        predicted_return = prediction['predicted_return_3m']
        confidence = prediction['confidence']

        if recommendation == 'BUY':
            rationale_parts.append(f"Expected {predicted_return:.1f}% return based on strong momentum")
        elif recommendation == 'AVOID':
            rationale_parts.append(f"Projected {predicted_return:.1f}% decline due to weak fundamentals")
        else:
            rationale_parts.append(f"Expected flat performance ({predicted_return:.1f}% return)")

        # Add key factor
        if features.price_momentum_30d and features.price_momentum_30d > 5:
            rationale_parts.append("Strong recent price momentum")
        elif features.active_listings_count and features.active_listings_count > 20:
            rationale_parts.append("High liquidity")

        rationale_parts.append(f"Confidence: {confidence:.0%}")

        return ". ".join(rationale_parts) + "."

    def _calculate_price_target(self, card: Card, predicted_return: float, adjustment: float) -> float | None:
        """Calculate price target based on current market data."""
        # Get latest price from features
        latest_features = self.db_session.query(CardFeature).filter_by(
            card_id=card.id,
        ).order_by(CardFeature.feature_date.desc()).first()

        if not latest_features or not latest_features.sold_median_30d:
            return None

        current_price = latest_features.sold_median_30d
        target_return = predicted_return + (adjustment * 100)  # Add/subtract 10%

        return current_price * (1 + target_return / 100)


class ModelTrainer:
    """Utility class for training and evaluating models."""

    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session
        self.model = TCGMarketModel(db_session)

    def run_backtest(
        self,
        start_date: datetime,
        end_date: datetime,
        retrain_frequency_days: int = 30,
    ) -> dict[str, float]:
        """Run walk-forward backtest."""
        logger.info("Starting backtest", start_date=start_date.date(), end_date=end_date.date())

        results = []
        current_date = start_date

        while current_date < end_date:
            try:
                # Define training window (use past 180 days)
                train_start = current_date - timedelta(days=180)
                train_end = current_date

                # Prepare training data
                X, y_return, y_class = self.model.prepare_training_data(train_start, train_end)

                if len(X) < 50:  # Need minimum samples
                    current_date += timedelta(days=retrain_frequency_days)
                    continue

                # Train models
                self.model.train_models(X, y_return, y_class)

                # Test on next period
                test_start = current_date
                test_end = current_date + timedelta(days=retrain_frequency_days)

                X_test, y_test_return, y_test_class = self.model.prepare_training_data(test_start, test_end)

                if len(X_test) > 0:
                    predictions = self.model.predict(X_test)

                    # Calculate metrics
                    r2 = r2_score(y_test_return, predictions['predicted_return_3m'])
                    accuracy = accuracy_score(y_test_class, predictions['predicted_class'])

                    results.append({
                        'date': current_date,
                        'r2': r2,
                        'accuracy': accuracy,
                        'test_samples': len(X_test),
                    })

                    logger.info("Backtest period completed",
                               date=current_date.date(),
                               r2=r2,
                               accuracy=accuracy)

            except Exception as e:
                logger.error("Backtest period failed", date=current_date.date(), error=str(e))

            current_date += timedelta(days=retrain_frequency_days)

        # Calculate overall metrics
        if results:
            overall_metrics = {
                'avg_r2': np.mean([r['r2'] for r in results]),
                'avg_accuracy': np.mean([r['accuracy'] for r in results]),
                'periods_tested': len(results),
            }

            logger.info("Backtest completed", metrics=overall_metrics)
            return overall_metrics

        return {}
