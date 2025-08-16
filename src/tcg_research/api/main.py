"""FastAPI application for TCG research system."""

import os
from datetime import datetime

import structlog
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session, sessionmaker

from tcg_research.core.features import FeatureEngineer
from tcg_research.core.ingestion import DataIngestionPipeline, SpecificCardIngester
from tcg_research.core.model import TCGMarketModel
from tcg_research.core.conservative_model import ConservativeDecisionEngine
from tcg_research.models.database import Card, ModelPrediction, create_database_engine
from tcg_research.api.mock_data import generate_mock_recommendations, generate_mock_cards
from tcg_research.api.ebay_setup import router as ebay_router
from tcg_research.api.ebay_webhook import router as webhook_router
from tcg_research.api.api_setup import router as api_setup_router
from tcg_research.api.psa_endpoints import router as psa_router

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

# Include all API routers
app.include_router(ebay_router, prefix="/api", tags=["eBay Setup"])
app.include_router(webhook_router, tags=["eBay Webhooks"])
app.include_router(api_setup_router, tags=["API Setup & Filtering"])
app.include_router(psa_router, prefix="/api", tags=["PSA API"])

# Database setup with fallback
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://tcg_user:tcg_password@localhost:5432/tcg_research")

# Railway uses postgres:// but SQLAlchemy needs postgresql://
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

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
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow(),
        "version": "0.1.0",
        "service": "tcg-research-api"
    }

@app.get("/investment-criteria")
async def get_investment_criteria():
    """Get the ultra-conservative investment criteria used by the system."""
    return {
        "philosophy": "Ultra-conservative approach that only recommends BUY for exceptional opportunities",
        "buy_criteria": {
            "minimum_predicted_return": "20%+ over 3 months",
            "minimum_confidence": "90%+ model confidence",
            "maximum_risk_level": "MEDIUM (no HIGH risk BUYs)",
            "minimum_liquidity_score": "7/10 (good liquidity required)",
            "minimum_momentum_score": "6/10 (strong momentum required)",
            "minimum_stability_score": "6/10 (price stability required)"
        },
        "watch_criteria": {
            "minimum_predicted_return": "5%+ over 3 months",
            "minimum_confidence": "70%+ model confidence",
            "maximum_predicted_loss": "-15% (don't watch if >15% loss expected)"
        },
        "avoid_criteria": {
            "description": "Any card that doesn't meet WATCH criteria gets AVOID rating",
            "triggers": ["Negative returns", "Low confidence", "Poor liquidity", "High volatility"]
        },
        "data_quality": {
            "filtering_philosophy": "Ultra-conservative data filtering - better to exclude questionable items than include junk",
            "automatic_exclusions": [
                "Pokemon TCG Online codes",
                "Choose your card/bulk lots", 
                "Custom/proxy cards",
                "Non-card accessories",
                "Damaged items"
            ],
            "quality_requirements": [
                "Single card listings only",
                "Clear set identification",
                "Reasonable pricing",
                "Professional descriptions"
            ]
        },
        "rationale": "Better to miss opportunities than lose money. Only invest when all signals align.",
        "note": "This system prioritizes capital preservation over aggressive growth"
    }

@app.get("/system-dashboard")
async def get_system_dashboard():
    """Comprehensive system dashboard showing setup status and capabilities."""
    
    # Check API connections
    apis_status = {
        "ebay": {
            "connected": bool(os.getenv("EBAY_APP_ID") and os.getenv("EBAY_CERT_ID")),
            "purpose": "Live Pokemon card pricing and market data"
        },
        "pricecharting": {
            "connected": bool(os.getenv("PRICECHARTING_API_KEY")),
            "purpose": "Historical price trends and market analysis"
        },
        "psa": {
            "connected": bool(os.getenv("PSA_API_KEY")),
            "purpose": "Grading population data for collectible cards"
        },
        "database": {
            "connected": bool(os.getenv("DATABASE_URL")),
            "purpose": "Data storage and ML model persistence"
        }
    }
    
    # System capabilities
    connected_apis = sum(1 for api in apis_status.values() if api["connected"])
    total_apis = len(apis_status)
    
    return {
        "system_name": "Pokemon Card Investment Analysis System",
        "version": "1.0.0",
        "timestamp": datetime.utcnow(),
        "api_connections": apis_status,
        "connection_summary": {
            "connected_apis": connected_apis,
            "total_apis": total_apis,
            "connection_percentage": round((connected_apis / total_apis) * 100, 1),
            "operational_status": "Fully Operational" if connected_apis == total_apis else "Partially Operational" if connected_apis > 0 else "Mock Data Mode"
        },
        "features": {
            "ultra_conservative_algorithm": "✅ Active",
            "sophisticated_filtering": "✅ Active", 
            "multi_source_data": "✅ Available",
            "ml_predictions": "✅ Available",
            "web_dashboard": "✅ Available",
            "real_time_analysis": "✅ Available"
        },
        "data_quality": {
            "filtering_active": True,
            "quality_threshold": "Conservative (85%+ confidence)",
            "exclusion_rules": "50+ junk detection patterns",
            "entity_resolution": "Enhanced with market tier classification"
        },
        "investment_approach": {
            "philosophy": "Capital preservation over aggressive growth",
            "buy_threshold": "20%+ predicted return, 90%+ confidence",
            "risk_management": "Maximum MEDIUM risk for BUY decisions",
            "decision_boundary": "Ultra-conservative - better to miss than lose"
        },
        "setup_guides": {
            "api_status": "/api-status/all",
            "pricecharting_setup": "/api-setup/pricecharting-guide", 
            "psa_setup": "/api-setup/psa-guide",
            "database_setup": "/api-setup/database-guide"
        },
        "testing_endpoints": {
            "filtered_search": "/filtered-search/test?query=charizard",
            "filter_demonstration": "/filtering/demonstration",
            "conservative_scan": "/tcg/scan/conservative",
            "investment_criteria": "/investment-criteria"
        }
    }


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


# Mock endpoints for testing without database
@app.get("/tcg/scan/mock")
async def tcg_scan_mock(limit: int = 10):
    """Mock TCG scan with sample data for testing."""
    try:
        mock_recs = generate_mock_recommendations()
        
        # Apply limit
        limited_recs = mock_recs[:limit]
        
        response = {
            "message": f"Found {len(limited_recs)} mock recommendations",
            "timestamp": datetime.utcnow(),
            "recommendations": limited_recs,
            "note": "This is mock data for testing purposes"
        }
        
        return response
        
    except Exception as e:
        logger.error("Mock TCG scan failed", error=str(e))
        raise HTTPException(status_code=500, detail="Mock scan failed")

@app.get("/cards/mock", response_model=list[CardResponse])
async def get_mock_cards(limit: int = 100, offset: int = 0):
    """Get mock cards for testing."""
    try:
        mock_cards = generate_mock_cards()
        
        # Apply pagination
        paginated = mock_cards[offset:offset + limit]
        
        return paginated
        
    except Exception as e:
        logger.error("Mock cards failed", error=str(e))
        raise HTTPException(status_code=500, detail="Mock cards failed")

# Ultra-conservative scan endpoint
@app.get("/tcg/scan/conservative")
async def tcg_scan_conservative(
    limit: int = 10,
    db: Session = Depends(get_db),
):
    """Ultra-conservative TCG scan with strict BUY criteria."""
    try:
        # If no database, return conservative mock data
        if SessionLocal is None:
            logger.info("No database available, returning conservative mock data")
            return await tcg_scan_mock(limit)
            
        # Use conservative decision engine
        conservative_engine = ConservativeDecisionEngine(db)
        recommendations = conservative_engine.process_card_recommendations()
        
        # Apply limit and filter for most relevant
        limited_recs = recommendations[:limit]
        
        response = {
            "message": f"Found {len(limited_recs)} ultra-conservative recommendations",
            "timestamp": datetime.utcnow(),
            "recommendations": limited_recs,
            "criteria": {
                "min_predicted_return_for_buy": "20%",
                "min_confidence_for_buy": "90%",
                "note": "Only exceptional opportunities get BUY rating"
            }
        }
        
        return response
        
    except Exception as e:
        logger.error("Conservative scan failed", error=str(e))
        return await tcg_scan_mock(limit)

# Command to run the TCG scan
@app.get("/tcg/scan")
async def tcg_scan(
    limit: int = 10,
    min_confidence: float = 0.8,
    conservative: bool = True,  # Default to conservative mode
    db: Session = Depends(get_db),
):
    """Main TCG scan command - get top recommendations."""
    try:
        # Use conservative mode by default
        if conservative:
            return await tcg_scan_conservative(limit, db)
            
        # If no database, return mock data
        if SessionLocal is None:
            logger.info("No database available, returning mock data")
            return await tcg_scan_mock(limit)
            
        # Get top BUY recommendations
        buy_recs = await get_buy_recommendations(limit, min_confidence, db)

        # Format response for CLI output
        if not buy_recs:
            # Fall back to mock data if no real data
            logger.info("No recommendations found, returning mock data")
            return await tcg_scan_mock(limit)

        response = {
            "message": f"Found {len(buy_recs)} BUY recommendations",
            "timestamp": datetime.utcnow(),
            "recommendations": buy_recs,
        }

        return response

    except Exception as e:
        logger.error("TCG scan failed, falling back to mock data", error=str(e))
        return await tcg_scan_mock(limit)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
