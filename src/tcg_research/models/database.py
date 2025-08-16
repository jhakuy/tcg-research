"""Database models and schema definitions."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()


class Card(Base):
    """Card entity table."""
    
    __tablename__ = "cards"
    
    id = Column(Integer, primary_key=True)
    canonical_sku = Column(String(255), unique=True, nullable=False, index=True)
    set_code = Column(String(20), nullable=False, index=True)
    card_number = Column(String(20), nullable=False)
    name_normalized = Column(String(255), nullable=False, index=True)
    rarity = Column(String(50), nullable=False)
    finish = Column(String(50), default="Regular")
    grade = Column(Integer, nullable=True)
    language = Column(String(5), default="EN")
    
    # Metadata
    supertype = Column(String(50))
    subtypes = Column(String(255))  # JSON string of subtypes
    hp = Column(Integer)
    types = Column(String(255))     # JSON string of types
    artist = Column(String(255))
    image_url = Column(Text)
    tcgplayer_id = Column(Integer)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    ebay_listings = relationship("EbayListing", back_populates="card")
    price_history = relationship("PriceHistory", back_populates="card")
    psa_populations = relationship("PSAPopulation", back_populates="card")
    features = relationship("CardFeature", back_populates="card")


class Set(Base):
    """Set information table."""
    
    __tablename__ = "sets"
    
    id = Column(Integer, primary_key=True)
    set_code = Column(String(20), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    series = Column(String(100))
    total_cards = Column(Integer)
    release_date = Column(DateTime)
    symbol_url = Column(Text)
    logo_url = Column(Text)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EbayListing(Base):
    """eBay listing data."""
    
    __tablename__ = "ebay_listings"
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    
    # eBay data
    item_id = Column(String(50), nullable=False)
    title = Column(Text, nullable=False)
    price = Column(Float)
    currency = Column(String(5), default="USD")
    condition = Column(String(50))
    listing_type = Column(String(20))  # BuyItNow, Auction, etc.
    end_time = Column(DateTime)
    seller_username = Column(String(100))
    view_item_url = Column(Text)
    image_url = Column(Text)
    
    # Status tracking
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, default=datetime.utcnow)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    card = relationship("Card", back_populates="ebay_listings")
    
    __table_args__ = (
        UniqueConstraint("item_id", "card_id", name="uq_listing_card"),
    )


class PriceHistory(Base):
    """Price history from PriceCharting."""
    
    __tablename__ = "price_history"
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    
    # Price data
    date = Column(DateTime, nullable=False, index=True)
    loose_price = Column(Float)
    cib_price = Column(Float)      # Complete in Box
    new_price = Column(Float)
    graded_price = Column(Float)
    volume = Column(Integer)
    
    # Source tracking
    source = Column(String(50), default="pricecharting")
    product_id = Column(String(100))  # External product ID
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    card = relationship("Card", back_populates="price_history")
    
    __table_args__ = (
        UniqueConstraint("card_id", "date", "source", name="uq_price_date_source"),
    )


class PSAPopulation(Base):
    """PSA population data."""
    
    __tablename__ = "psa_populations"
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    
    # PSA data
    grade = Column(Integer, nullable=False)
    population = Column(Integer, nullable=False)
    population_higher = Column(Integer, nullable=False)
    last_updated = Column(DateTime, nullable=False)
    
    # Tracking
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    card = relationship("Card", back_populates="psa_populations")
    
    __table_args__ = (
        UniqueConstraint("card_id", "grade", name="uq_card_grade"),
    )


class CardFeature(Base):
    """Engineered features for ML models."""
    
    __tablename__ = "card_features"
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    
    # Time window
    feature_date = Column(DateTime, nullable=False, index=True)
    
    # Price momentum features
    price_momentum_30d = Column(Float)
    price_momentum_90d = Column(Float)
    price_momentum_180d = Column(Float)
    
    # Liquidity features
    active_listings_count = Column(Integer)
    listing_turnover_30d = Column(Float)
    avg_days_on_market = Column(Float)
    
    # Spread features
    ask_median = Column(Float)
    sold_median_30d = Column(Float)
    ask_sold_spread_pct = Column(Float)
    
    # Volatility features
    price_volatility_30d = Column(Float)
    price_volatility_90d = Column(Float)
    
    # PSA features (if applicable)
    psa_pop_growth_30d = Column(Float)
    psa_pop_pressure = Column(Float)  # pop_growth / price_change
    
    # Set/market features
    time_since_release_days = Column(Integer)
    set_type = Column(String(20))  # main, special, promo
    
    # Target variables (for training)
    return_1m = Column(Float)      # 1-month forward return
    return_3m = Column(Float)      # 3-month forward return
    return_6m = Column(Float)      # 6-month forward return
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    card = relationship("Card", back_populates="features")
    
    __table_args__ = (
        UniqueConstraint("card_id", "feature_date", name="uq_card_feature_date"),
    )


class ModelPrediction(Base):
    """Model predictions and recommendations."""
    
    __tablename__ = "model_predictions"
    
    id = Column(Integer, primary_key=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False)
    
    # Prediction metadata
    model_version = Column(String(50), nullable=False)
    prediction_date = Column(DateTime, nullable=False, index=True)
    
    # Predictions
    predicted_return_3m = Column(Float)
    confidence = Column(Float)
    recommendation = Column(String(10))  # BUY, WATCH, AVOID
    risk_level = Column(String(10))      # LOW, MEDIUM, HIGH
    
    # Supporting data
    key_features = Column(Text)          # JSON of important features
    rationale = Column(Text)
    price_target_low = Column(Float)
    price_target_high = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)


class MarketAlert(Base):
    """Market alerts and notifications."""
    
    __tablename__ = "market_alerts"
    
    id = Column(Integer, primary_key=True)
    
    # Alert details
    alert_type = Column(String(50), nullable=False)  # price_spike, volume_surge, etc.
    title = Column(String(255), nullable=False)
    description = Column(Text)
    severity = Column(String(10), default="INFO")    # INFO, WARNING, CRITICAL
    
    # Related entities
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=True)
    set_code = Column(String(20), nullable=True)
    
    # Trigger data
    trigger_value = Column(Float)
    threshold_value = Column(Float)
    
    # Status
    is_active = Column(Boolean, default=True)
    acknowledged_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)


# Database utility functions
def create_database_engine(database_url: str):
    """Create database engine with TimescaleDB optimizations."""
    engine = create_engine(
        database_url,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    return engine


def create_tables(engine):
    """Create all tables."""
    Base.metadata.create_all(engine)


def get_session_factory(engine):
    """Get session factory."""
    return sessionmaker(bind=engine)