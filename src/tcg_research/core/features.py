"""Feature engineering pipeline for ML models."""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import structlog
from sqlalchemy import and_
from sqlalchemy.orm import Session

from tcg_research.models.database import (
    Card,
    CardFeature,
    EbayListing,
    PriceHistory,
    PSAPopulation,
    Set,
)

logger = structlog.get_logger()


class FeatureEngineer:
    """Feature engineering for TCG market prediction."""

    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session

    def generate_features_for_date(self, target_date: datetime, lookback_days: int = 180) -> int:
        """Generate features for all cards as of a specific date."""
        logger.info("Generating features", target_date=target_date.date(), lookback_days=lookback_days)

        # Get all active cards
        cards = self.db_session.query(Card).all()
        features_created = 0

        for card in cards:
            try:
                features = self._calculate_card_features(card, target_date, lookback_days)
                if features:
                    self._save_features(card.id, target_date, features)
                    features_created += 1
            except Exception as e:
                logger.error("Feature generation failed", card_id=card.id, error=str(e))

        self.db_session.commit()
        logger.info("Feature generation completed", features_created=features_created)
        return features_created

    def _calculate_card_features(
        self,
        card: Card,
        as_of_date: datetime,
        lookback_days: int,
    ) -> dict | None:
        """Calculate all features for a single card."""
        start_date = as_of_date - timedelta(days=lookback_days)

        # Get price history
        price_data = self._get_price_history(card.id, start_date, as_of_date)
        if len(price_data) < 5:  # Need minimum data points
            return None

        # Get eBay listing data
        listing_data = self._get_listing_data(card.id, start_date, as_of_date)

        # Get PSA data
        psa_data = self._get_psa_data(card.id, as_of_date)

        # Calculate feature groups
        features = {}
        features.update(self._price_momentum_features(price_data))
        features.update(self._liquidity_features(listing_data))
        features.update(self._spread_features(price_data, listing_data))
        features.update(self._volatility_features(price_data))
        features.update(self._psa_features(psa_data, price_data))
        features.update(self._market_features(card, as_of_date))
        features.update(self._target_features(card.id, as_of_date))

        return features

    def _get_price_history(self, card_id: int, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get price history for feature calculation."""
        query = self.db_session.query(PriceHistory).filter(
            and_(
                PriceHistory.card_id == card_id,
                PriceHistory.date >= start_date,
                PriceHistory.date <= end_date,
            ),
        ).order_by(PriceHistory.date)

        data = []
        for record in query:
            # Use graded price if available, otherwise use loose price
            price = record.graded_price or record.loose_price or record.new_price
            if price and price > 0:
                data.append({
                    'date': record.date,
                    'price': price,
                    'volume': record.volume or 0,
                })

        return pd.DataFrame(data)

    def _get_listing_data(self, card_id: int, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Get eBay listing data."""
        query = self.db_session.query(EbayListing).filter(
            and_(
                EbayListing.card_id == card_id,
                EbayListing.created_at >= start_date,
                EbayListing.created_at <= end_date,
                EbayListing.price.isnot(None),
                EbayListing.price > 0,
            ),
        ).order_by(EbayListing.created_at)

        data = []
        for record in query:
            data.append({
                'date': record.created_at,
                'price': record.price,
                'listing_type': record.listing_type,
                'is_active': record.is_active,
            })

        return pd.DataFrame(data)

    def _get_psa_data(self, card_id: int, as_of_date: datetime) -> pd.DataFrame:
        """Get PSA population data."""
        query = self.db_session.query(PSAPopulation).filter(
            and_(
                PSAPopulation.card_id == card_id,
                PSAPopulation.last_updated <= as_of_date,
            ),
        ).order_by(PSAPopulation.grade)

        data = []
        for record in query:
            data.append({
                'grade': record.grade,
                'population': record.population,
                'population_higher': record.population_higher,
                'last_updated': record.last_updated,
            })

        return pd.DataFrame(data)

    def _price_momentum_features(self, price_data: pd.DataFrame) -> dict:
        """Calculate price momentum features."""
        if price_data.empty:
            return {
                'price_momentum_30d': None,
                'price_momentum_90d': None,
                'price_momentum_180d': None,
            }

        price_data = price_data.set_index('date').sort_index()
        prices = price_data['price']

        # Calculate momentum over different periods
        momentum_30d = self._calculate_momentum(prices, 30)
        momentum_90d = self._calculate_momentum(prices, 90)
        momentum_180d = self._calculate_momentum(prices, 180)

        return {
            'price_momentum_30d': momentum_30d,
            'price_momentum_90d': momentum_90d,
            'price_momentum_180d': momentum_180d,
        }

    def _calculate_momentum(self, prices: pd.Series, days: int) -> float | None:
        """Calculate price momentum over specified days."""
        if len(prices) < 2:
            return None

        cutoff_date = prices.index[-1] - pd.Timedelta(days=days)
        recent_prices = prices[prices.index >= cutoff_date]

        if len(recent_prices) < 2:
            return None

        start_price = recent_prices.iloc[0]
        end_price = recent_prices.iloc[-1]

        if start_price == 0:
            return None

        return (end_price - start_price) / start_price * 100

    def _liquidity_features(self, listing_data: pd.DataFrame) -> dict:
        """Calculate liquidity features."""
        if listing_data.empty:
            return {
                'active_listings_count': 0,
                'listing_turnover_30d': 0.0,
                'avg_days_on_market': None,
            }

        # Current active listings
        active_count = len(listing_data[listing_data['is_active'] == True])

        # Listing turnover (new listings per day over 30 days)
        listing_data['date'] = pd.to_datetime(listing_data['date'])
        last_30_days = listing_data['date'].max() - pd.Timedelta(days=30)
        recent_listings = listing_data[listing_data['date'] >= last_30_days]
        turnover_30d = len(recent_listings) / 30.0

        # Average days on market (placeholder - would need end dates)
        avg_days_on_market = None  # TODO: Calculate when we have listing end dates

        return {
            'active_listings_count': active_count,
            'listing_turnover_30d': turnover_30d,
            'avg_days_on_market': avg_days_on_market,
        }

    def _spread_features(self, price_data: pd.DataFrame, listing_data: pd.DataFrame) -> dict:
        """Calculate bid-ask spread features."""
        ask_median = None
        sold_median_30d = None
        ask_sold_spread_pct = None

        # Current ask median from active listings
        if not listing_data.empty:
            active_listings = listing_data[listing_data['is_active'] == True]
            if not active_listings.empty:
                ask_median = active_listings['price'].median()

        # Sold median from price history (last 30 days)
        if not price_data.empty:
            last_30_days = price_data['date'].max() - pd.Timedelta(days=30)
            recent_sales = price_data[price_data['date'] >= last_30_days]
            if not recent_sales.empty:
                sold_median_30d = recent_sales['price'].median()

        # Calculate spread
        if ask_median and sold_median_30d and sold_median_30d > 0:
            ask_sold_spread_pct = (ask_median - sold_median_30d) / sold_median_30d * 100

        return {
            'ask_median': ask_median,
            'sold_median_30d': sold_median_30d,
            'ask_sold_spread_pct': ask_sold_spread_pct,
        }

    def _volatility_features(self, price_data: pd.DataFrame) -> dict:
        """Calculate price volatility features."""
        if price_data.empty or len(price_data) < 3:
            return {
                'price_volatility_30d': None,
                'price_volatility_90d': None,
            }

        price_data = price_data.set_index('date').sort_index()
        prices = price_data['price']

        # Calculate returns
        returns = prices.pct_change().dropna()

        vol_30d = self._calculate_volatility(returns, 30)
        vol_90d = self._calculate_volatility(returns, 90)

        return {
            'price_volatility_30d': vol_30d,
            'price_volatility_90d': vol_90d,
        }

    def _calculate_volatility(self, returns: pd.Series, days: int) -> float | None:
        """Calculate volatility over specified days."""
        if len(returns) < 2:
            return None

        cutoff_date = returns.index[-1] - pd.Timedelta(days=days)
        recent_returns = returns[returns.index >= cutoff_date]

        if len(recent_returns) < 2:
            return None

        return recent_returns.std() * np.sqrt(252)  # Annualized volatility

    def _psa_features(self, psa_data: pd.DataFrame, price_data: pd.DataFrame) -> dict:
        """Calculate PSA-related features."""
        psa_pop_growth_30d = None
        psa_pop_pressure = None

        if not psa_data.empty:
            # PSA 10 population growth (placeholder - would need historical pop data)
            psa_10_data = psa_data[psa_data['grade'] == 10]
            if not psa_10_data.empty:
                # TODO: Calculate actual population growth
                psa_pop_growth_30d = 0.0  # Placeholder

        # PSA population pressure vs price movement
        if psa_pop_growth_30d is not None and not price_data.empty:
            price_change_30d = self._calculate_momentum(
                price_data.set_index('date')['price'], 30,
            )
            if price_change_30d and price_change_30d != 0:
                psa_pop_pressure = psa_pop_growth_30d / abs(price_change_30d)

        return {
            'psa_pop_growth_30d': psa_pop_growth_30d,
            'psa_pop_pressure': psa_pop_pressure,
        }

    def _market_features(self, card: Card, as_of_date: datetime) -> dict:
        """Calculate market-level features."""
        # Time since release
        time_since_release_days = None
        set_type = "unknown"

        # Get set information
        set_info = self.db_session.query(Set).filter_by(set_code=card.set_code).first()
        if set_info and set_info.release_date:
            time_since_release_days = (as_of_date - set_info.release_date).days

            # Classify set type based on name patterns
            set_name_lower = set_info.name.lower()
            if any(x in set_name_lower for x in ['base', 'expansion', 'scarlet', 'violet']):
                set_type = "main"
            elif any(x in set_name_lower for x in ['special', 'holiday', 'collection']):
                set_type = "special"
            elif 'promo' in set_name_lower:
                set_type = "promo"
            else:
                set_type = "main"  # Default assumption

        return {
            'time_since_release_days': time_since_release_days,
            'set_type': set_type,
        }

    def _target_features(self, card_id: int, as_of_date: datetime) -> dict:
        """Calculate target variables for training."""
        # Get future price data for targets
        future_1m = as_of_date + timedelta(days=30)
        future_3m = as_of_date + timedelta(days=90)
        future_6m = as_of_date + timedelta(days=180)

        current_price = self._get_price_at_date(card_id, as_of_date)
        price_1m = self._get_price_at_date(card_id, future_1m)
        price_3m = self._get_price_at_date(card_id, future_3m)
        price_6m = self._get_price_at_date(card_id, future_6m)

        return_1m = None
        return_3m = None
        return_6m = None

        if current_price and current_price > 0:
            if price_1m:
                return_1m = (price_1m - current_price) / current_price * 100
            if price_3m:
                return_3m = (price_3m - current_price) / current_price * 100
            if price_6m:
                return_6m = (price_6m - current_price) / current_price * 100

        return {
            'return_1m': return_1m,
            'return_3m': return_3m,
            'return_6m': return_6m,
        }

    def _get_price_at_date(self, card_id: int, target_date: datetime) -> float | None:
        """Get price closest to target date."""
        # Find price record closest to target date
        query = self.db_session.query(PriceHistory).filter(
            PriceHistory.card_id == card_id,
            PriceHistory.date <= target_date,
        ).order_by(PriceHistory.date.desc()).limit(1)

        record = query.first()
        if record:
            return record.graded_price or record.loose_price or record.new_price

        return None

    def _save_features(self, card_id: int, feature_date: datetime, features: dict) -> None:
        """Save calculated features to database."""
        # Check if features already exist for this date
        existing = self.db_session.query(CardFeature).filter_by(
            card_id=card_id,
            feature_date=feature_date.date(),
        ).first()

        if existing:
            # Update existing features
            for key, value in features.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
        else:
            # Create new feature record
            feature_record = CardFeature(
                card_id=card_id,
                feature_date=feature_date,
                **features,
            )
            self.db_session.add(feature_record)

    def get_training_data(
        self,
        min_date: datetime | None = None,
        max_date: datetime | None = None,
    ) -> pd.DataFrame:
        """Get feature data for model training."""
        query = self.db_session.query(CardFeature)

        if min_date:
            query = query.filter(CardFeature.feature_date >= min_date)
        if max_date:
            query = query.filter(CardFeature.feature_date <= max_date)

        # Only include records with valid targets
        query = query.filter(CardFeature.return_3m.isnot(None))

        records = []
        for feature in query:
            record = {
                'card_id': feature.card_id,
                'feature_date': feature.feature_date,

                # Features
                'price_momentum_30d': feature.price_momentum_30d,
                'price_momentum_90d': feature.price_momentum_90d,
                'price_momentum_180d': feature.price_momentum_180d,
                'active_listings_count': feature.active_listings_count,
                'listing_turnover_30d': feature.listing_turnover_30d,
                'ask_sold_spread_pct': feature.ask_sold_spread_pct,
                'price_volatility_30d': feature.price_volatility_30d,
                'price_volatility_90d': feature.price_volatility_90d,
                'psa_pop_growth_30d': feature.psa_pop_growth_30d,
                'time_since_release_days': feature.time_since_release_days,
                'set_type': feature.set_type,

                # Targets
                'return_1m': feature.return_1m,
                'return_3m': feature.return_3m,
                'return_6m': feature.return_6m,
            }
            records.append(record)

        df = pd.DataFrame(records)
        logger.info("Training data retrieved", rows=len(df))

        return df

    def backfill_features(self, start_date: datetime, end_date: datetime) -> int:
        """Backfill features for historical dates."""
        logger.info("Backfilling features", start_date=start_date.date(), end_date=end_date.date())

        current_date = start_date
        total_created = 0

        while current_date <= end_date:
            daily_created = self.generate_features_for_date(current_date)
            total_created += daily_created

            logger.info("Daily features backfilled", date=current_date.date(), count=daily_created)
            current_date += timedelta(days=1)

        logger.info("Feature backfill completed", total_created=total_created)
        return total_created
