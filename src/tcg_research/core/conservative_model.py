"""Ultra-conservative decision making engine for TCG investments."""

import json
from datetime import datetime
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
import structlog
from sqlalchemy.orm import Session

from tcg_research.models.database import Card, CardFeature, ModelPrediction
from tcg_research.core.model import TCGMarketModel

logger = structlog.get_logger()


class ConservativeDecisionEngine:
    """Ultra-conservative decision engine that only recommends BUY for high-confidence opportunities."""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.base_model = TCGMarketModel(db_session)
        
        # ULTRA CONSERVATIVE CRITERIA
        self.buy_criteria = {
            'min_predicted_return': 20.0,      # Must predict at least 20% return
            'min_confidence': 0.90,            # Must be 90%+ confident
            'max_risk_tolerance': 'MEDIUM',    # No HIGH risk BUYs
            'min_liquidity_score': 7.0,       # Good liquidity required
            'min_momentum_score': 6.0,         # Strong momentum required
            'min_stability_score': 6.0,       # Price stability required
        }
        
        self.watch_criteria = {
            'min_predicted_return': 5.0,       # 5%+ return for WATCH
            'min_confidence': 0.70,            # 70%+ confidence
            'max_predicted_loss': -15.0,       # Don't watch if >15% loss predicted
        }

    def create_ultra_conservative_targets(self, returns: pd.Series) -> pd.Series:
        """Create ultra-conservative classification targets."""
        y_class = pd.Series(index=returns.index, dtype=int)
        
        # BUY: Only for exceptional opportunities (>25% return)
        y_class[returns > 25] = 2
        
        # WATCH: Moderate opportunities (0% to 25% return)
        y_class[(returns >= 0) & (returns <= 25)] = 1
        
        # AVOID: Any negative return
        y_class[returns < 0] = 0
        
        return y_class

    def calculate_liquidity_score(self, features: CardFeature) -> float:
        """Calculate liquidity score (0-10)."""
        score = 0.0
        
        if features.active_listings_count:
            # More listings = better liquidity
            if features.active_listings_count >= 50:
                score += 4.0
            elif features.active_listings_count >= 20:
                score += 3.0
            elif features.active_listings_count >= 10:
                score += 2.0
            elif features.active_listings_count >= 5:
                score += 1.0
        
        if features.listing_turnover_30d:
            # Higher turnover = better liquidity
            if features.listing_turnover_30d >= 0.8:
                score += 3.0
            elif features.listing_turnover_30d >= 0.5:
                score += 2.0
            elif features.listing_turnover_30d >= 0.3:
                score += 1.0
        
        if features.ask_sold_spread_pct:
            # Lower spread = better liquidity
            if features.ask_sold_spread_pct <= 5:
                score += 3.0
            elif features.ask_sold_spread_pct <= 10:
                score += 2.0
            elif features.ask_sold_spread_pct <= 15:
                score += 1.0
        
        return min(score, 10.0)

    def calculate_momentum_score(self, features: CardFeature) -> float:
        """Calculate momentum score (0-10)."""
        score = 0.0
        
        if features.price_momentum_30d:
            if features.price_momentum_30d >= 10:
                score += 4.0
            elif features.price_momentum_30d >= 5:
                score += 3.0
            elif features.price_momentum_30d >= 2:
                score += 2.0
            elif features.price_momentum_30d >= 0:
                score += 1.0
        
        if features.price_momentum_90d:
            if features.price_momentum_90d >= 15:
                score += 3.0
            elif features.price_momentum_90d >= 8:
                score += 2.0
            elif features.price_momentum_90d >= 3:
                score += 1.0
        
        if features.price_momentum_180d:
            if features.price_momentum_180d >= 20:
                score += 3.0
            elif features.price_momentum_180d >= 10:
                score += 2.0
            elif features.price_momentum_180d >= 5:
                score += 1.0
        
        return min(score, 10.0)

    def calculate_stability_score(self, features: CardFeature) -> float:
        """Calculate price stability score (0-10)."""
        score = 10.0  # Start with perfect score, subtract for volatility
        
        if features.price_volatility_30d:
            if features.price_volatility_30d >= 30:
                score -= 5.0
            elif features.price_volatility_30d >= 20:
                score -= 3.0
            elif features.price_volatility_30d >= 15:
                score -= 2.0
            elif features.price_volatility_30d >= 10:
                score -= 1.0
        
        if features.price_volatility_90d:
            if features.price_volatility_90d >= 25:
                score -= 3.0
            elif features.price_volatility_90d >= 15:
                score -= 2.0
            elif features.price_volatility_90d >= 10:
                score -= 1.0
        
        return max(score, 0.0)

    def make_conservative_decision(
        self, 
        card: Card, 
        base_prediction: Dict[str, Any], 
        features: CardFeature
    ) -> Tuple[str, str, Dict[str, float]]:
        """Make ultra-conservative investment decision."""
        
        # Calculate scores
        liquidity_score = self.calculate_liquidity_score(features)
        momentum_score = self.calculate_momentum_score(features)
        stability_score = self.calculate_stability_score(features)
        
        scores = {
            'liquidity': liquidity_score,
            'momentum': momentum_score,
            'stability': stability_score,
            'confidence': base_prediction['confidence'],
            'predicted_return': base_prediction['predicted_return_3m']
        }
        
        # Extract values
        predicted_return = base_prediction['predicted_return_3m']
        confidence = base_prediction['confidence']
        
        # ULTRA CONSERVATIVE BUY CRITERIA
        buy_checks = [
            predicted_return >= self.buy_criteria['min_predicted_return'],
            confidence >= self.buy_criteria['min_confidence'],
            liquidity_score >= self.buy_criteria['min_liquidity_score'],
            momentum_score >= self.buy_criteria['min_momentum_score'],
            stability_score >= self.buy_criteria['min_stability_score'],
        ]
        
        if all(buy_checks):
            decision = 'BUY'
            rationale = self._generate_buy_rationale(card, scores, features)
        else:
            # Check for WATCH criteria
            watch_checks = [
                predicted_return >= self.watch_criteria['min_predicted_return'],
                predicted_return >= self.watch_criteria['max_predicted_loss'],
                confidence >= self.watch_criteria['min_confidence'],
            ]
            
            if all(watch_checks):
                decision = 'WATCH'
                rationale = self._generate_watch_rationale(card, scores, features, buy_checks)
            else:
                decision = 'AVOID'
                rationale = self._generate_avoid_rationale(card, scores, features)
        
        return decision, rationale, scores

    def _generate_buy_rationale(self, card: Card, scores: Dict[str, float], features: CardFeature) -> str:
        """Generate rationale for BUY recommendation."""
        parts = [
            f"STRONG BUY: {scores['predicted_return']:.1f}% predicted return with {scores['confidence']:.0%} confidence"
        ]
        
        if scores['momentum'] >= 8:
            parts.append("Exceptional price momentum")
        elif scores['momentum'] >= 6:
            parts.append("Strong price momentum")
            
        if scores['liquidity'] >= 8:
            parts.append("Excellent liquidity")
        elif scores['liquidity'] >= 6:
            parts.append("Good liquidity")
            
        if scores['stability'] >= 8:
            parts.append("High price stability")
        elif scores['stability'] >= 6:
            parts.append("Stable pricing")
            
        parts.append("All conservative criteria met")
        
        return ". ".join(parts) + "."

    def _generate_watch_rationale(self, card: Card, scores: Dict[str, float], features: CardFeature, failed_buy_checks: list) -> str:
        """Generate rationale for WATCH recommendation."""
        parts = [
            f"WATCH: {scores['predicted_return']:.1f}% predicted return with {scores['confidence']:.0%} confidence"
        ]
        
        # Explain why it didn't make BUY
        if scores['predicted_return'] < self.buy_criteria['min_predicted_return']:
            parts.append(f"Return below {self.buy_criteria['min_predicted_return']}% BUY threshold")
        
        if scores['confidence'] < self.buy_criteria['min_confidence']:
            parts.append(f"Confidence below {self.buy_criteria['min_confidence']:.0%} BUY threshold")
            
        if scores['liquidity'] < self.buy_criteria['min_liquidity_score']:
            parts.append("Liquidity concerns")
            
        if scores['momentum'] < self.buy_criteria['min_momentum_score']:
            parts.append("Insufficient momentum")
            
        if scores['stability'] < self.buy_criteria['min_stability_score']:
            parts.append("Price volatility concerns")
        
        parts.append("Monitor for improvement")
        
        return ". ".join(parts) + "."

    def _generate_avoid_rationale(self, card: Card, scores: Dict[str, float], features: CardFeature) -> str:
        """Generate rationale for AVOID recommendation."""
        parts = [
            f"AVOID: {scores['predicted_return']:.1f}% predicted return with {scores['confidence']:.0%} confidence"
        ]
        
        if scores['predicted_return'] < 0:
            parts.append("Negative return expected")
        elif scores['predicted_return'] < self.watch_criteria['min_predicted_return']:
            parts.append("Low return potential")
            
        if scores['confidence'] < self.watch_criteria['min_confidence']:
            parts.append("Low prediction confidence")
            
        if scores['liquidity'] < 4:
            parts.append("Poor liquidity")
            
        if scores['momentum'] < 3:
            parts.append("Weak momentum")
            
        if scores['stability'] < 4:
            parts.append("High volatility")
        
        parts.append("Does not meet investment criteria")
        
        return ". ".join(parts) + "."

    def process_card_recommendations(self, card_ids: list[int] = None) -> list[Dict[str, Any]]:
        """Process cards through conservative decision engine."""
        
        if card_ids:
            cards = self.db_session.query(Card).filter(Card.id.in_(card_ids)).all()
        else:
            cards = self.db_session.query(Card).all()
        
        recommendations = []
        
        for card in cards:
            try:
                # Get latest features
                latest_features = self.db_session.query(CardFeature).filter_by(
                    card_id=card.id
                ).order_by(CardFeature.feature_date.desc()).first()
                
                if not latest_features:
                    continue
                
                # Get base ML prediction (if model is trained)
                try:
                    feature_data = self._prepare_feature_data(latest_features)
                    X = pd.DataFrame([feature_data])
                    base_predictions = self.base_model.predict(X)
                    base_pred = base_predictions.iloc[0].to_dict()
                except Exception:
                    # Fallback to mock prediction if model not trained
                    base_pred = {
                        'predicted_return_3m': 5.0,
                        'confidence': 0.75,
                        'recommendation': 'WATCH'
                    }
                
                # Apply conservative decision making
                decision, rationale, scores = self.make_conservative_decision(
                    card, base_pred, latest_features
                )
                
                recommendation = {
                    'card_id': card.id,
                    'card_name': card.name_normalized,
                    'recommendation': decision,
                    'predicted_return_3m': base_pred['predicted_return_3m'],
                    'confidence': base_pred['confidence'],
                    'risk_level': self._determine_risk_level(decision, scores),
                    'rationale': rationale,
                    'price_target_low': self._calculate_price_target(latest_features, base_pred['predicted_return_3m'], -0.05) if decision == 'BUY' else None,
                    'price_target_high': self._calculate_price_target(latest_features, base_pred['predicted_return_3m'], 0.05) if decision == 'BUY' else None,
                    'prediction_date': datetime.utcnow().isoformat(),
                    'scores': scores
                }
                
                recommendations.append(recommendation)
                
            except Exception as e:
                logger.error("Conservative processing failed", card_id=card.id, error=str(e))
        
        # Sort by recommendation priority and confidence
        priority_order = {'BUY': 0, 'WATCH': 1, 'AVOID': 2}
        recommendations.sort(key=lambda x: (priority_order.get(x['recommendation'], 3), -x['confidence']))
        
        return recommendations

    def _prepare_feature_data(self, features: CardFeature) -> Dict[str, Any]:
        """Prepare feature data for ML model."""
        return {
            'price_momentum_30d': features.price_momentum_30d or 0,
            'price_momentum_90d': features.price_momentum_90d or 0,
            'price_momentum_180d': features.price_momentum_180d or 0,
            'active_listings_count': features.active_listings_count or 0,
            'listing_turnover_30d': features.listing_turnover_30d or 0,
            'ask_sold_spread_pct': features.ask_sold_spread_pct or 0,
            'price_volatility_30d': features.price_volatility_30d or 0,
            'price_volatility_90d': features.price_volatility_90d or 0,
            'psa_pop_growth_30d': features.psa_pop_growth_30d or 0,
            'time_since_release_days': features.time_since_release_days or 0,
            'set_type': features.set_type or 'unknown'
        }

    def _determine_risk_level(self, decision: str, scores: Dict[str, float]) -> str:
        """Determine risk level based on decision and scores."""
        if decision == 'AVOID':
            return 'HIGH'
        elif decision == 'BUY':
            if scores['stability'] >= 8 and scores['liquidity'] >= 8:
                return 'LOW'
            else:
                return 'MEDIUM'
        else:  # WATCH
            if scores['stability'] >= 6:
                return 'MEDIUM'
            else:
                return 'HIGH'

    def _calculate_price_target(self, features: CardFeature, predicted_return: float, adjustment: float) -> float:
        """Calculate conservative price target."""
        if not features.sold_median_30d:
            return None
            
        current_price = features.sold_median_30d
        conservative_return = predicted_return * 0.8  # 20% haircut for conservatism
        target_return = conservative_return + (adjustment * 100)
        
        return current_price * (1 + target_return / 100)