"""API setup and configuration endpoints for all data sources."""

import os
import asyncio
from typing import Dict, Any, List
from datetime import datetime
import httpx
import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from tcg_research.core.pokemon_filter import PokemonCardFilter
from tcg_research.mcp.enhanced_ebay_browse import EnhancedEbayBrowseClient

logger = structlog.get_logger()
router = APIRouter()

class APIStatus(BaseModel):
    """API connection status model."""
    name: str
    connected: bool
    error: str | None = None
    last_tested: datetime | None = None

class FilteredSearchResult(BaseModel):
    """Filtered search result model."""
    query: str
    total_raw_results: int
    total_filtered_results: int
    filter_efficiency: float
    quality_distribution: Dict[str, int]
    top_results: List[Dict[str, Any]]

@router.get("/api-status/all")
async def get_all_api_status():
    """Get status of all API connections."""
    
    apis = {
        "ebay": {
            "name": "eBay Browse API",
            "required_vars": ["EBAY_APP_ID", "EBAY_CERT_ID"],
            "test_endpoint": "/api/test-apis/ebay"
        },
        "pricecharting": {
            "name": "PriceCharting API", 
            "required_vars": ["PRICECHARTING_API_KEY"],
            "test_endpoint": "/api/test-apis/pricecharting"
        },
        "psa": {
            "name": "PSA API",
            "required_vars": ["PSA_ACCESS_TOKEN"],
            "test_endpoint": "/api/psa/status"
        },
        "database": {
            "name": "PostgreSQL Database",
            "required_vars": ["DATABASE_URL"],
            "test_endpoint": "/api/test-apis/database"
        }
    }
    
    status_results = {}
    
    for api_key, api_info in apis.items():
        # Check if required environment variables are set
        vars_set = all(os.getenv(var) for var in api_info["required_vars"])
        
        status_results[api_key] = {
            "name": api_info["name"],
            "required_variables": api_info["required_vars"],
            "variables_set": vars_set,
            "ready_for_testing": vars_set,
            "test_endpoint": api_info["test_endpoint"],
            "setup_instructions": f"Add {', '.join(api_info['required_vars'])} to Railway environment variables"
        }
    
    return {
        "timestamp": datetime.utcnow(),
        "apis": status_results,
        "overall_readiness": {
            "total_apis": len(apis),
            "ready_apis": sum(1 for api in status_results.values() if api["ready_for_testing"]),
            "missing_apis": [name for name, api in status_results.items() if not api["ready_for_testing"]]
        }
    }

@router.get("/api-setup/pricecharting-guide")
async def pricecharting_setup_guide():
    """Detailed setup guide for PriceCharting API."""
    return {
        "api_name": "PriceCharting API",
        "purpose": "Historical price data and market trends for Pokemon cards",
        "setup_steps": [
            "1. Go to https://www.pricecharting.com/",
            "2. Create an account or sign in",
            "3. Navigate to your account dashboard",
            "4. Look for 'API Access' or 'Developer Tools' section",
            "5. Request API access (may require business justification)",
            "6. Wait for approval (usually 1-3 business days)",
            "7. Once approved, you'll receive an API key",
            "8. Add PRICECHARTING_API_KEY to Railway environment variables"
        ],
        "api_documentation": "https://www.pricecharting.com/api-documentation",
        "authentication": "Bearer token in Authorization header",
        "rate_limits": "Check documentation for current limits",
        "cost": "Check pricing page for current rates",
        "alternative": "System has mock historical data for development",
        "environment_variable": "PRICECHARTING_API_KEY",
        "current_status": {
            "api_key_set": bool(os.getenv("PRICECHARTING_API_KEY")),
            "ready_to_test": bool(os.getenv("PRICECHARTING_API_KEY"))
        }
    }

@router.get("/api-setup/psa-guide") 
async def psa_setup_guide():
    """Detailed setup guide for PSA API."""
    return {
        "api_name": "PSA Public API",
        "purpose": "Population data for graded Pokemon cards (PSA grades)",
        "setup_steps": [
            "1. Go to https://www.psacard.com/publicapi",
            "2. Create a PSA account if you don't have one",
            "3. Click on 'Apply for API Access'",
            "4. Fill out the application form with business use case",
            "5. Describe your Pokemon card investment analysis system",
            "6. Wait for approval (can take 3-7 business days)",
            "7. Once approved, you'll receive API credentials",
            "8. Add PSA_API_KEY to Railway environment variables"
        ],
        "api_documentation": "https://www.psacard.com/publicapi/documentation",
        "authentication": "Bearer token in Authorization header", 
        "rate_limits": "Conservative limits, check documentation",
        "cost": "Free for approved use cases",
        "business_justification": "Market analysis and investment research for Pokemon cards",
        "alternative": "System has mock population data for development",
        "environment_variable": "PSA_API_KEY",
        "current_status": {
            "api_key_set": bool(os.getenv("PSA_API_KEY")),
            "ready_to_test": bool(os.getenv("PSA_API_KEY"))
        }
    }

@router.get("/api-setup/database-guide")
async def database_setup_guide():
    """Setup guide for PostgreSQL database."""
    return {
        "database": "PostgreSQL with TimescaleDB",
        "purpose": "Store card data, features, and ML predictions",
        "railway_setup": [
            "1. In Railway dashboard, click 'New' → 'Database' → 'Add PostgreSQL'", 
            "2. Railway will automatically create the database",
            "3. DATABASE_URL will be auto-injected into your app",
            "4. No manual configuration needed!"
        ],
        "local_development": [
            "1. Run: docker-compose up -d postgres",
            "2. Run: alembic upgrade head (to create tables)",
            "3. Run: python scripts/init_db.py (to initialize)"
        ],
        "tables_created": [
            "cards - Pokemon card entities",
            "sets - Pokemon set information", 
            "ebay_listings - Live eBay data",
            "price_history - Historical prices",
            "psa_populations - Grading data",
            "card_features - ML features",
            "model_predictions - AI predictions"
        ],
        "current_status": {
            "database_url_set": bool(os.getenv("DATABASE_URL")),
            "ready_to_use": bool(os.getenv("DATABASE_URL"))
        }
    }

@router.get("/filtered-search/test")
async def test_filtered_pokemon_search(
    query: str = "charizard vmax",
    limit: int = 10
) -> FilteredSearchResult:
    """Test the sophisticated Pokemon card filtering system."""
    
    app_id = os.getenv("EBAY_APP_ID")
    cert_id = os.getenv("EBAY_CERT_ID")
    
    if not app_id or not cert_id:
        raise HTTPException(
            status_code=400,
            detail="eBay credentials not set. Add EBAY_APP_ID and EBAY_CERT_ID to environment variables"
        )
    
    try:
        # Use enhanced eBay client with filtering
        ebay_client = EnhancedEbayBrowseClient(app_id, cert_id)
        filter_system = PokemonCardFilter()
        
        # Get filtered results
        results = await ebay_client.search_pokemon_cards_filtered(
            query=query,
            limit=limit,
            quality_threshold="acceptable"
        )
        
        # Calculate filter efficiency
        total_raw = results.get("total_raw_results", 0)
        total_filtered = results.get("total_filtered_results", 0)
        efficiency = (1 - total_filtered / max(total_raw, 1)) * 100 if total_raw > 0 else 0
        
        return FilteredSearchResult(
            query=query,
            total_raw_results=total_raw,
            total_filtered_results=total_filtered,
            filter_efficiency=round(efficiency, 2),
            quality_distribution=results.get("quality_distribution", {}),
            top_results=results.get("filtered_items", [])[:limit]
        )
        
    except Exception as e:
        logger.error("Filtered search failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

@router.get("/filtering/demonstration")
async def demonstrate_filtering():
    """Demonstrate the filtering system with various example listings."""
    
    # Example listings that show filtering capabilities
    test_listings = [
        {
            "title": "2022 Pokemon Brilliant Stars Charizard VSTAR 018/172 Rainbow Rare PSA 10",
            "price": "299.99",
            "condition": "Graded",
            "expected_result": "KEEP - High quality single card with PSA grade"
        },
        {
            "title": "POKEMON TCG ONLINE CODE CARDS - Unused - **EMAIL CODES**", 
            "price": "0.99",
            "condition": "Used",
            "expected_result": "FILTER OUT - Digital codes"
        },
        {
            "title": "2021 Pokemon Battle Styles Choose Your Card/Complete Your Set! Reverse Holo Rare",
            "price": "0.99", 
            "condition": "Ungraded",
            "expected_result": "FILTER OUT - Choose your card bulk listing"
        },
        {
            "title": "Custom Pokemon Charizard Proxy Card - Fan Made",
            "price": "5.99",
            "condition": "Custom",
            "expected_result": "FILTER OUT - Custom/proxy card"
        },
        {
            "title": "Pokemon Charizard Base Set Shadowless 4/102 Holo Rare Light Play",
            "price": "850.00",
            "condition": "Light Play", 
            "expected_result": "KEEP - Valuable vintage card"
        },
        {
            "title": "Pokemon Card Sleeves Deck Box Playmat Bundle Charizard Theme",
            "price": "29.99",
            "condition": "New",
            "expected_result": "FILTER OUT - Accessories, not cards"
        }
    ]
    
    filter_system = PokemonCardFilter()
    results = []
    
    for listing in test_listings:
        try:
            # Apply filtering logic
            is_pokemon_card = filter_system.is_pokemon_card(listing["title"])
            quality_score = filter_system.calculate_quality_score(listing["title"], float(listing["price"]))
            card_info = filter_system.extract_card_info(listing["title"])
            
            filter_result = {
                "listing": listing,
                "filter_decision": "KEEP" if is_pokemon_card and quality_score >= 0.5 else "FILTER OUT",
                "is_pokemon_card": is_pokemon_card,
                "quality_score": round(quality_score, 3),
                "extracted_info": card_info,
                "matches_expected": None  # Will be calculated
            }
            
            # Check if result matches expectation
            expected_decision = "KEEP" if "KEEP" in listing["expected_result"] else "FILTER OUT"
            filter_result["matches_expected"] = filter_result["filter_decision"] == expected_decision
            
            results.append(filter_result)
            
        except Exception as e:
            results.append({
                "listing": listing,
                "error": str(e),
                "filter_decision": "ERROR"
            })
    
    # Calculate accuracy
    correct_predictions = sum(1 for r in results if r.get("matches_expected") == True)
    total_predictions = len([r for r in results if "matches_expected" in r])
    accuracy = (correct_predictions / max(total_predictions, 1)) * 100
    
    return {
        "demonstration": "Pokemon Card Filtering System",
        "test_cases": len(test_listings),
        "accuracy": f"{accuracy:.1f}%",
        "correct_predictions": correct_predictions,
        "total_predictions": total_predictions,
        "results": results,
        "summary": {
            "digital_codes_filtered": sum(1 for r in results if "digital" in str(r.get("extracted_info", {}))),
            "bulk_lots_filtered": sum(1 for r in results if r.get("extracted_info", {}).get("card_type") == "bulk_lot"),
            "accessories_filtered": sum(1 for r in results if r.get("extracted_info", {}).get("card_type") == "accessory"),
            "quality_cards_kept": sum(1 for r in results if r.get("filter_decision") == "KEEP")
        }
    }