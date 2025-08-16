#!/usr/bin/env python3
"""Setup script for TCG research system."""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tcg_research.models.database import Base, create_tables
from tcg_research.core.features import FeatureEngineer
from tcg_research.core.ingestion import DataIngestionPipeline
from tcg_research.core.model import TCGMarketModel


def create_database():
    """Create database and tables."""
    database_url = os.getenv("DATABASE_URL", "postgresql://tcg_user:tcg_password@localhost:5432/tcg_research")
    
    print(f"Creating database with URL: {database_url}")
    
    engine = create_engine(database_url)
    
    # Create tables
    create_tables(engine)
    print("Database tables created successfully")
    
    return engine


async def initial_data_ingestion(engine):
    """Run initial data ingestion."""
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print("Starting initial data ingestion...")
        
        pipeline = DataIngestionPipeline(db)
        results = await pipeline.run_daily_ingestion()
        
        print(f"Initial ingestion completed: {results}")
        
    except Exception as e:
        print(f"Initial ingestion failed: {e}")
        db.rollback()
    finally:
        db.close()


def generate_features(engine):
    """Generate initial features."""
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print("Generating features...")
        
        feature_engineer = FeatureEngineer(db)
        
        # Generate features for last 30 days
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=30)
        
        total_features = feature_engineer.backfill_features(start_date, end_date)
        
        print(f"Generated {total_features} feature records")
        
    except Exception as e:
        print(f"Feature generation failed: {e}")
        db.rollback()
    finally:
        db.close()


def train_initial_model(engine):
    """Train initial model."""
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        print("Training initial model...")
        
        model = TCGMarketModel(db)
        
        # Use last 90 days for training
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=90)
        
        X, y_return, y_class = model.prepare_training_data(start_date, end_date)
        
        if len(X) < 10:
            print("Insufficient data for model training")
            return
        
        metrics = model.train_models(X, y_return, y_class)
        
        # Save model
        version = datetime.utcnow().strftime("%Y%m%d")
        model.save_models(version)
        
        print(f"Model trained and saved (version: {version})")
        print(f"Training metrics: {metrics}")
        
    except Exception as e:
        print(f"Model training failed: {e}")
        db.rollback()
    finally:
        db.close()


async def main():
    """Main setup function."""
    print("Starting TCG Research System Setup")
    print("=" * 50)
    
    # Create database
    engine = create_database()
    
    # Initial data ingestion
    await initial_data_ingestion(engine)
    
    # Generate features
    generate_features(engine)
    
    # Train initial model
    train_initial_model(engine)
    
    print("\nSetup completed successfully!")
    print("\nNext steps:")
    print("1. Set up your API keys in .env file:")
    print("   - EBAY_APP_ID")
    print("   - PRICECHARTING_API_KEY") 
    print("   - PSA_API_KEY")
    print("2. Run the API server: python -m tcg_research.api.main")
    print("3. Try the /tcg/scan endpoint for recommendations")


if __name__ == "__main__":
    asyncio.run(main())