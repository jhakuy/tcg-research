"""FastAPI application for TCG research system."""

import os
from datetime import datetime

import structlog
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

try:
    from ..core.features import FeatureEngineer
    from ..core.ingestion import DataIngestionPipeline, SpecificCardIngester
    from ..core.model import TCGMarketModel
    from ..models.database import Card, ModelPrediction, create_database_engine
except ImportError:
    # Fallback for deployment issues
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    
    from tcg_research.core.features import FeatureEngineer
    from tcg_research.core.ingestion import DataIngestionPipeline, SpecificCardIngester
    from tcg_research.core.model import TCGMarketModel
    from tcg_research.models.database import Card, ModelPrediction, create_database_engine

# Configure logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO level
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Create FastAPI app
app = FastAPI(
    title="TCG Research API",
    description="TCG market analysis and prediction system",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database setup with fallback
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://tcg_user:tcg_password@localhost:5432/tcg_research")

try:
    engine = create_database_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    logger.info("Database connection established", url=DATABASE_URL.split('@')[-1])  # Don't log credentials
except Exception as e:
    logger.error("Database connection failed", error=str(e))
    # Create a dummy session for development
    SessionLocal = None


def get_db():
    """Get database session."""
    if SessionLocal is None:
        raise HTTPException(status_code=503, detail="Database not available")
    
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Pydantic models
class CardResponse(BaseModel):
    id: int
    canonical_sku: str
    set_code: str
    card_number: str
    name_normalized: str
    rarity: str
    finish: str
    language: str

    class Config:
        from_attributes = True


class PredictionResponse(BaseModel):
    card_id: int
    card_name: str
    recommendation: str
    predicted_return_3m: float
    confidence: float
    risk_level: str
    rationale: str
    price_target_low: float | None
    price_target_high: float | None
    prediction_date: datetime

    class Config:
        from_attributes = True


class IngestionRequest(BaseModel):
    card_name: str
    set_name: str | None = None


class IngestionResponse(BaseModel):
    success: bool
    message: str
    card_id: int | None = None


# API Routes
@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "TCG Research API", "version": "0.1.0"}


@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    try:
        # Test database connection
        card_count = db.query(Card).count()
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow(),
            "cards_in_db": card_count,
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Service unavailable")


@app.get("/cards", response_model=list[CardResponse])
async def get_cards(
    limit: int = 100,
    offset: int = 0,
    set_code: str | None = None,
    db: Session = Depends(get_db),
):
    """Get cards from database."""
    query = db.query(Card)

    if set_code:
        query = query.filter(Card.set_code == set_code.upper())

    cards = query.offset(offset).limit(limit).all()
    return cards


@app.get("/cards/{card_id}", response_model=CardResponse)
async def get_card(card_id: int, db: Session = Depends(get_db)):
    """Get specific card by ID."""
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@app.post("/cards/ingest", response_model=IngestionResponse)
async def ingest_card(request: IngestionRequest, db: Session = Depends(get_db)):
    """Ingest a specific card by name."""
    try:
        ingester = SpecificCardIngester(db)
        card = await ingester.ingest_card_by_name(request.card_name, request.set_name)

        if card:
            return IngestionResponse(
                success=True,
                message=f"Card '{request.card_name}' ingested successfully",
                card_id=card.id,
            )
        return IngestionResponse(
            success=False,
            message=f"Card '{request.card_name}' not found or failed to ingest",
        )

    except Exception as e:
        logger.error("Card ingestion failed", error=str(e))
        raise HTTPException(status_code=500, detail="Ingestion failed")


@app.get("/predictions", response_model=list[PredictionResponse])
async def get_predictions(
    limit: int = 50,
    recommendation: str | None = None,
    min_confidence: float | None = None,
    db: Session = Depends(get_db),
):
    """Get model predictions."""
    query = db.query(ModelPrediction, Card).join(Card, ModelPrediction.card_id == Card.id)

    if recommendation:
        query = query.filter(ModelPrediction.recommendation == recommendation.upper())

    if min_confidence:
        query = query.filter(ModelPrediction.confidence >= min_confidence)

    # Get latest predictions
    query = query.order_by(ModelPrediction.prediction_date.desc())
    results = query.limit(limit).all()

    predictions = []
    for pred, card in results:
        predictions.append(PredictionResponse(
            card_id=card.id,
            card_name=card.name_normalized,
            recommendation=pred.recommendation,
            predicted_return_3m=pred.predicted_return_3m,
            confidence=pred.confidence,
            risk_level=pred.risk_level,
            rationale=pred.rationale or "",
            price_target_low=pred.price_target_low,
            price_target_high=pred.price_target_high,
            prediction_date=pred.prediction_date,
        ))

    return predictions


@app.get("/predictions/buy", response_model=list[PredictionResponse])
async def get_buy_recommendations(
    limit: int = 20,
    min_confidence: float = 0.7,
    db: Session = Depends(get_db),
):
    """Get top BUY recommendations."""
    return await get_predictions(
        limit=limit,
        recommendation="BUY",
        min_confidence=min_confidence,
        db=db,
    )


@app.post("/features/generate")
async def generate_features(
    date: str | None = None,
    db: Session = Depends(get_db),
):
    """Generate features for a specific date."""
    try:
        target_date = datetime.fromisoformat(date) if date else datetime.utcnow()

        feature_engineer = FeatureEngineer(db)
        count = feature_engineer.generate_features_for_date(target_date)

        return {
            "success": True,
            "message": f"Generated features for {count} cards",
            "date": target_date.date(),
        }

    except Exception as e:
        logger.error("Feature generation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Feature generation failed")


@app.post("/model/train")
async def train_model(
    start_date: str,
    end_date: str,
    db: Session = Depends(get_db),
):
    """Train the prediction model."""
    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = datetime.fromisoformat(end_date)

        model = TCGMarketModel(db)
        X, y_return, y_class = model.prepare_training_data(start_dt, end_dt)
        metrics = model.train_models(X, y_return, y_class)

        # Save trained model
        version = datetime.utcnow().strftime("%Y%m%d_%H%M")
        model.save_models(version)

        return {
            "success": True,
            "message": "Model trained successfully",
            "version": version,
            "metrics": metrics,
        }

    except Exception as e:
        logger.error("Model training failed", error=str(e))
        raise HTTPException(status_code=500, detail="Model training failed")


@app.post("/model/predict")
async def generate_predictions(
    model_version: str | None = None,
    db: Session = Depends(get_db),
):
    """Generate predictions for all cards."""
    try:
        model = TCGMarketModel(db)

        if model_version:
            model.load_models(model_version)
        else:
            # Use latest model (would need to implement model versioning)
            raise HTTPException(status_code=400, detail="Model version required")

        count = model.generate_predictions_for_cards()

        return {
            "success": True,
            "message": f"Generated predictions for {count} cards",
            "model_version": model_version,
        }

    except Exception as e:
        logger.error("Prediction generation failed", error=str(e))
        raise HTTPException(status_code=500, detail="Prediction generation failed")


@app.post("/ingestion/daily")
async def run_daily_ingestion(db: Session = Depends(get_db)):
    """Run daily data ingestion pipeline."""
    try:
        pipeline = DataIngestionPipeline(db)
        results = await pipeline.run_daily_ingestion()

        return {
            "success": True,
            "message": "Daily ingestion completed",
            "results": results,
        }

    except Exception as e:
        logger.error("Daily ingestion failed", error=str(e))
        raise HTTPException(status_code=500, detail="Daily ingestion failed")


# Command to run the TCG scan
@app.get("/tcg/scan")
async def tcg_scan(
    limit: int = 10,
    min_confidence: float = 0.8,
    db: Session = Depends(get_db),
):
    """Main TCG scan command - get top recommendations."""
    try:
        # Get top BUY recommendations
        buy_recs = await get_buy_recommendations(limit, min_confidence, db)

        # Format response for CLI output
        if not buy_recs:
            return {
                "message": "No high-confidence BUY recommendations found",
                "recommendations": [],
            }

        response = {
            "message": f"Found {len(buy_recs)} BUY recommendations",
            "timestamp": datetime.utcnow(),
            "recommendations": buy_recs,
        }

        return response

    except Exception as e:
        logger.error("TCG scan failed", error=str(e))
        raise HTTPException(status_code=500, detail="TCG scan failed")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
