"""
Complete ML Pipeline for Pokemon Card Investment Analysis.

This module orchestrates the entire machine learning workflow:
1. Data Collection (eBay + PSA)
2. Feature Engineering  
3. Model Training
4. Prediction Generation
5. Conservative Decision Making

Usage:
    python -m tcg_research.workflows.ml_pipeline --mode collect
    python -m tcg_research.workflows.ml_pipeline --mode train
    python -m tcg_research.workflows.ml_pipeline --mode predict
    python -m tcg_research.workflows.ml_pipeline --mode full
"""

import asyncio
import argparse
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any
import structlog
from sqlalchemy.orm import Session

from tcg_research.models.database import create_database_engine, Card, CardFeature
from tcg_research.core.ingestion import DataIngestionPipeline
from tcg_research.core.features import FeatureEngineer
from tcg_research.core.model import TCGMarketModel
from tcg_research.core.conservative_model import ConservativeDecisionEngine
from tcg_research.mcp.enhanced_ebay_browse import EnhancedEbayBrowseClient

logger = structlog.get_logger()


class MLPipeline:
    """Complete machine learning pipeline for Pokemon card analysis."""
    
    def __init__(self):
        # Database setup
        self.engine = create_database_engine()
        self.session = Session(self.engine)
        
        # Core components
        self.ingestion_pipeline = DataIngestionPipeline(self.session)
        self.feature_engineer = FeatureEngineer(self.session)
        self.market_model = TCGMarketModel(self.session)
        self.conservative_engine = ConservativeDecisionEngine(self.session)
        
        # Data collection targets
        self.collection_targets = [
            # High-value modern cards
            {"pokemon": "Charizard", "set": "Brilliant Stars", "rarity": "Secret Rare"},
            {"pokemon": "Pikachu", "set": "Pokemon 151", "rarity": "Special Illustration"},
            {"pokemon": "Umbreon", "set": "Evolving Skies", "rarity": "Alt Art"},
            {"pokemon": "Rayquaza", "set": "Evolving Skies", "rarity": "Alt Art"},
            {"pokemon": "Mew", "set": "Pokemon 151", "rarity": "Special Illustration"},
            
            # Classic valuable cards
            {"pokemon": "Charizard", "set": "Base Set", "rarity": "Holo Rare"},
            {"pokemon": "Blastoise", "set": "Base Set", "rarity": "Holo Rare"},
            {"pokemon": "Venusaur", "set": "Base Set", "rarity": "Holo Rare"},
            
            # High-volume liquid cards
            {"pokemon": "Pikachu", "set": "Vivid Voltage", "rarity": "Amazing Rare"},
            {"pokemon": "Charizard", "set": "Champion's Path", "rarity": "Rainbow Rare"},
        ]

    async def collect_data(self, days_back: int = 30) -> Dict[str, Any]:
        """Collect fresh data from eBay and PSA APIs."""
        
        logger.info("Starting data collection", targets=len(self.collection_targets))
        
        # Setup eBay client
        ebay_app_id = os.getenv('EBAY_APP_ID')
        ebay_cert_id = os.getenv('EBAY_CERT_ID')
        
        if not ebay_app_id or not ebay_cert_id:
            logger.error("eBay credentials not found")
            return {"success": False, "error": "Missing eBay credentials"}
        
        results = {
            "cards_collected": 0,
            "listings_processed": 0,
            "psa_calls_used": 0,
            "errors": []
        }
        
        try:
            async with EnhancedEbayBrowseClient(ebay_app_id, ebay_cert_id) as ebay_client:
                
                for target in self.collection_targets:
                    try:
                        # Search for cards with enhanced filtering
                        query = f"{target['pokemon']} {target['set']} {target['rarity']}"
                        
                        logger.info("Collecting data for target", query=query)
                        
                        listings = await ebay_client.search_pokemon_cards(
                            query=query,
                            max_results=20,  # Reasonable number per target
                            include_entity_resolution=True
                        )
                        
                        results["listings_processed"] += len(listings)
                        
                        # Process listings and store in database
                        for listing in listings:
                            try:
                                # Store card data
                                card_data = {
                                    "name": listing.enhanced_entity.name_normalized if listing.enhanced_entity else target['pokemon'],
                                    "set_name": listing.enhanced_entity.set_code if listing.enhanced_entity else target['set'],
                                    "rarity": listing.enhanced_entity.rarity if listing.enhanced_entity else target['rarity'],
                                    "current_price": listing.price,
                                    "condition": listing.condition,
                                    "listing_date": datetime.now(),
                                    "source": "ebay_enhanced",
                                    "grade": listing.enhanced_entity.grade if listing.enhanced_entity else None
                                }
                                
                                # Use ingestion pipeline to store
                                await self.ingestion_pipeline.process_card_data(card_data)
                                results["cards_collected"] += 1
                                
                            except Exception as e:
                                logger.error("Failed to process listing", error=str(e))
                                results["errors"].append(str(e))
                        
                        # Small delay to be respectful to APIs
                        await asyncio.sleep(0.5)
                        
                    except Exception as e:
                        logger.error("Failed to collect target", target=target, error=str(e))
                        results["errors"].append(f"Target {target}: {str(e)}")
            
            logger.info("Data collection completed", results=results)
            return {"success": True, "results": results}
            
        except Exception as e:
            logger.error("Data collection failed", error=str(e))
            return {"success": False, "error": str(e)}

    async def generate_features(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Generate ML features for collected data."""
        
        logger.info("Starting feature generation", start_date=start_date, end_date=end_date)
        
        try:
            # Get cards in date range
            cards = self.session.query(Card).filter(
                Card.created_at.between(start_date, end_date)
            ).all()
            
            if not cards:
                logger.warning("No cards found in date range")
                return {"success": False, "error": "No cards found"}
            
            features_generated = 0
            
            for card in cards:
                try:
                    # Generate features for this card
                    features = await self.feature_engineer.generate_features_for_card(card)
                    if features:
                        features_generated += 1
                        
                except Exception as e:
                    logger.error("Feature generation failed for card", card_id=card.id, error=str(e))
            
            result = {
                "success": True,
                "cards_processed": len(cards),
                "features_generated": features_generated
            }
            
            logger.info("Feature generation completed", result=result)
            return result
            
        except Exception as e:
            logger.error("Feature generation failed", error=str(e))
            return {"success": False, "error": str(e)}

    async def train_models(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Train ML models on collected data."""
        
        logger.info("Starting model training", start_date=start_date, end_date=end_date)
        
        try:
            # Prepare training data
            X, y_return, y_class = self.market_model.prepare_training_data(start_date, end_date)
            
            if X.empty:
                logger.warning("No training data available")
                return {"success": False, "error": "No training data"}
            
            logger.info("Training data prepared", samples=len(X), features=len(X.columns))
            
            # Train models
            metrics = self.market_model.train_models(X, y_return, y_class)
            
            # Save trained models
            version = datetime.now().strftime("%Y%m%d_%H%M")
            self.market_model.save_models(version)
            
            result = {
                "success": True,
                "version": version,
                "metrics": metrics,
                "training_samples": len(X),
                "features": len(X.columns)
            }
            
            logger.info("Model training completed", result=result)
            return result
            
        except Exception as e:
            logger.error("Model training failed", error=str(e))
            return {"success": False, "error": str(e)}

    async def generate_predictions(self, model_version: str = None) -> Dict[str, Any]:
        """Generate predictions for all cards."""
        
        logger.info("Starting prediction generation", model_version=model_version)
        
        try:
            # Load model
            if model_version:
                self.market_model.load_models(model_version)
            else:
                # Use latest model
                latest_version = self.market_model.get_latest_model_version()
                if latest_version:
                    self.market_model.load_models(latest_version)
                else:
                    logger.error("No trained models found")
                    return {"success": False, "error": "No trained models available"}
            
            # Generate predictions
            predictions = self.market_model.generate_predictions()
            
            result = {
                "success": True,
                "predictions_generated": len(predictions),
                "model_version": model_version or latest_version
            }
            
            logger.info("Prediction generation completed", result=result)
            return result
            
        except Exception as e:
            logger.error("Prediction generation failed", error=str(e))
            return {"success": False, "error": str(e)}

    async def run_conservative_analysis(self, limit: int = 20) -> Dict[str, Any]:
        """Run conservative decision analysis with PSA data."""
        
        logger.info("Starting conservative analysis", limit=limit)
        
        try:
            # Get recent cards with predictions
            cards_with_predictions = self.session.query(Card).join(
                Card.predictions
            ).order_by(Card.created_at.desc()).limit(limit * 2).all()  # Get extra to filter
            
            if not cards_with_predictions:
                logger.warning("No cards with predictions found")
                return {"success": False, "error": "No cards with predictions"}
            
            recommendations = []
            psa_calls_used = 0
            
            for card in cards_with_predictions:
                try:
                    # Get latest prediction
                    latest_prediction = card.predictions[-1] if card.predictions else None
                    if not latest_prediction:
                        continue
                    
                    # Get features
                    latest_features = card.features[-1] if card.features else None
                    if not latest_features:
                        continue
                    
                    # Make conservative decision with PSA integration
                    prediction_data = {
                        "confidence": latest_prediction.confidence,
                        "predicted_return_3m": latest_prediction.predicted_return_3m
                    }
                    
                    decision, rationale, scores = await self.conservative_engine.make_conservative_decision(
                        card, prediction_data, latest_features
                    )
                    
                    if 'psa_confidence_bonus' in scores and scores['psa_confidence_bonus'] > 0:
                        psa_calls_used += 1
                    
                    recommendation = {
                        "card_name": card.name,
                        "set_name": card.set_name,
                        "decision": decision,
                        "rationale": rationale,
                        "predicted_return": scores['predicted_return'],
                        "confidence": scores['confidence'],
                        "scarcity_score": scores.get('scarcity_score', 0),
                        "gem_rate": scores.get('gem_rate', 0),
                        "current_price": card.current_price
                    }
                    
                    recommendations.append(recommendation)
                    
                    # Stop if we have enough BUY recommendations
                    buy_recs = [r for r in recommendations if r['decision'] == 'BUY']
                    if len(buy_recs) >= limit:
                        break
                        
                except Exception as e:
                    logger.error("Conservative analysis failed for card", card_id=card.id, error=str(e))
            
            # Sort by decision priority and confidence
            recommendations.sort(key=lambda x: (
                {'BUY': 3, 'WATCH': 2, 'AVOID': 1}[x['decision']],
                -x['confidence']
            ), reverse=True)
            
            result = {
                "success": True,
                "recommendations": recommendations[:limit],
                "psa_calls_used": psa_calls_used,
                "total_analyzed": len(recommendations)
            }
            
            logger.info("Conservative analysis completed", result={
                "recommendations": len(result["recommendations"]),
                "psa_calls": result["psa_calls_used"]
            })
            
            return result
            
        except Exception as e:
            logger.error("Conservative analysis failed", error=str(e))
            return {"success": False, "error": str(e)}

    async def run_full_pipeline(self) -> Dict[str, Any]:
        """Run complete ML pipeline from data collection to recommendations."""
        
        logger.info("Starting full ML pipeline")
        
        pipeline_results = {
            "start_time": datetime.now(),
            "data_collection": None,
            "feature_generation": None,
            "model_training": None,
            "prediction_generation": None,
            "conservative_analysis": None,
            "success": False
        }
        
        try:
            # Step 1: Collect fresh data
            logger.info("Pipeline Step 1: Data Collection")
            pipeline_results["data_collection"] = await self.collect_data(days_back=7)
            
            if not pipeline_results["data_collection"]["success"]:
                logger.error("Data collection failed, stopping pipeline")
                return pipeline_results
            
            # Step 2: Generate features
            logger.info("Pipeline Step 2: Feature Generation")
            end_date = datetime.now()
            start_date = end_date - timedelta(days=7)
            
            pipeline_results["feature_generation"] = await self.generate_features(start_date, end_date)
            
            if not pipeline_results["feature_generation"]["success"]:
                logger.error("Feature generation failed, stopping pipeline")
                return pipeline_results
            
            # Step 3: Train models
            logger.info("Pipeline Step 3: Model Training")
            train_end = datetime.now()
            train_start = train_end - timedelta(days=30)  # Use more data for training
            
            pipeline_results["model_training"] = await self.train_models(train_start, train_end)
            
            if not pipeline_results["model_training"]["success"]:
                logger.error("Model training failed, stopping pipeline")
                return pipeline_results
            
            # Step 4: Generate predictions
            logger.info("Pipeline Step 4: Prediction Generation")
            pipeline_results["prediction_generation"] = await self.generate_predictions()
            
            if not pipeline_results["prediction_generation"]["success"]:
                logger.error("Prediction generation failed, stopping pipeline")
                return pipeline_results
            
            # Step 5: Conservative analysis with PSA
            logger.info("Pipeline Step 5: Conservative Analysis")
            pipeline_results["conservative_analysis"] = await self.run_conservative_analysis(limit=10)
            
            if pipeline_results["conservative_analysis"]["success"]:
                pipeline_results["success"] = True
                logger.info("Full ML pipeline completed successfully")
            
            pipeline_results["end_time"] = datetime.now()
            pipeline_results["total_duration"] = (
                pipeline_results["end_time"] - pipeline_results["start_time"]
            ).total_seconds()
            
            return pipeline_results
            
        except Exception as e:
            logger.error("Full pipeline failed", error=str(e))
            pipeline_results["error"] = str(e)
            return pipeline_results
        
        finally:
            self.session.close()


async def main():
    """Main CLI interface for ML pipeline."""
    
    parser = argparse.ArgumentParser(description="Pokemon Card ML Pipeline")
    parser.add_argument(
        "--mode", 
        choices=["collect", "features", "train", "predict", "analyze", "full"],
        required=True,
        help="Pipeline mode to run"
    )
    parser.add_argument("--days", type=int, default=30, help="Days of data to process")
    parser.add_argument("--limit", type=int, default=10, help="Limit for recommendations")
    parser.add_argument("--model-version", type=str, help="Specific model version to use")
    
    args = parser.parse_args()
    
    # Configure logging
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.add_log_level,
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    logger.info("Starting Pokemon Card ML Pipeline", mode=args.mode)
    
    pipeline = MLPipeline()
    
    try:
        if args.mode == "collect":
            result = await pipeline.collect_data(days_back=args.days)
            
        elif args.mode == "features":
            end_date = datetime.now()
            start_date = end_date - timedelta(days=args.days)
            result = await pipeline.generate_features(start_date, end_date)
            
        elif args.mode == "train":
            end_date = datetime.now()
            start_date = end_date - timedelta(days=args.days)
            result = await pipeline.train_models(start_date, end_date)
            
        elif args.mode == "predict":
            result = await pipeline.generate_predictions(args.model_version)
            
        elif args.mode == "analyze":
            result = await pipeline.run_conservative_analysis(limit=args.limit)
            
        elif args.mode == "full":
            result = await pipeline.run_full_pipeline()
            
        else:
            logger.error("Invalid mode", mode=args.mode)
            return
        
        # Print results
        print(f"\n🎯 ML Pipeline Results ({args.mode.upper()})")
        print("=" * 50)
        
        if result["success"]:
            print("✅ SUCCESS")
            
            if args.mode == "analyze" and "recommendations" in result:
                print(f"\n📊 Investment Recommendations:")
                for i, rec in enumerate(result["recommendations"][:5], 1):
                    print(f"  {i}. {rec['decision']}: {rec['card_name']} ({rec['set_name']})")
                    print(f"     Return: {rec['predicted_return']:.1f}% | Confidence: {rec['confidence']:.0%}")
                    print(f"     Scarcity: {rec['scarcity_score']:.0f}/100 | {rec['rationale'][:80]}...")
                    print()
            
            if args.mode in ["full", "collect"] and "psa_calls_used" in str(result):
                psa_calls = result.get("conservative_analysis", {}).get("psa_calls_used", 0)
                if psa_calls > 0:
                    print(f"📡 PSA API calls used: {psa_calls}/100 daily limit")
            
        else:
            print("❌ FAILED")
            print(f"Error: {result.get('error', 'Unknown error')}")
        
        print("\n" + "=" * 50)
        
    except Exception as e:
        logger.error("Pipeline execution failed", error=str(e))
        print(f"❌ Pipeline failed: {e}")


if __name__ == "__main__":
    asyncio.run(main())