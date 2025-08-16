"""Simple eBay API setup guide and test endpoint."""

import os
import base64
from typing import Dict, Any
import httpx
import structlog
from fastapi import APIRouter, HTTPException

logger = structlog.get_logger()
router = APIRouter()


class EbayAuth:
    """Simple eBay OAuth client for Browse API."""
    
    def __init__(self, app_id: str, cert_id: str):
        self.app_id = app_id
        self.cert_id = cert_id
        self.token_url = "https://api.ebay.com/identity/v1/oauth2/token"
        self.browse_url = "https://api.ebay.com/buy/browse/v1"
        
    async def get_access_token(self) -> str:
        """Get OAuth access token using client credentials flow."""
        
        # Create base64 encoded credentials
        credentials = f"{self.app_id}:{self.cert_id}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        data = {
            "grant_type": "client_credentials",
            "scope": "https://api.ebay.com/oauth/api_scope"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(self.token_url, headers=headers, data=data)
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, 
                    detail=f"eBay OAuth failed: {response.text}"
                )
            
            token_data = response.json()
            return token_data["access_token"]
    
    async def search_pokemon_cards(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Search for Pokemon cards on eBay."""
        
        try:
            token = await self.get_access_token()
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"
            }
            
            # Pokemon cards are typically in category 2536 (CCG Individual Cards)
            params = {
                "q": f"pokemon {query}",
                "category_ids": "2536",
                "filter": "buyingOptions:{FIXED_PRICE},itemLocationCountry:US",
                "limit": limit,
                "sort": "price"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.browse_url}/item_summary/search",
                    headers=headers,
                    params=params
                )
                
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"eBay search failed: {response.text}"
                    )
                
                return response.json()
                
        except Exception as e:
            logger.error("eBay search failed", error=str(e))
            raise HTTPException(status_code=500, detail=f"eBay API error: {str(e)}")


@router.get("/ebay/setup-guide")
async def ebay_setup_guide():
    """Get instructions for setting up eBay API."""
    
    app_id_set = bool(os.getenv("EBAY_APP_ID"))
    cert_id_set = bool(os.getenv("EBAY_CERT_ID"))
    
    return {
        "step_1": "Go to https://developer.ebay.com/",
        "step_2": "Create developer account and sign in",
        "step_3": "Go to 'My Account' → 'Keys & IDs'",
        "step_4": "Create new Keyset (choose Production for live data)",
        "step_5": "Copy your App ID and Cert ID",
        "step_6": "Add these to Railway environment variables",
        "railway_variables": {
            "EBAY_APP_ID": "Your App ID from eBay",
            "EBAY_CERT_ID": "Your Cert ID from eBay"
        },
        "current_status": {
            "EBAY_APP_ID_set": app_id_set,
            "EBAY_CERT_ID_set": cert_id_set,
            "ready_to_test": app_id_set and cert_id_set
        },
        "test_endpoint": "/ebay/test-search?query=charizard",
        "note": "You DON'T need the webhook endpoint for card price data - that's only for marketplace apps"
    }


@router.get("/ebay/test-search")
async def test_ebay_search(query: str = "charizard"):
    """Test eBay API with a simple search."""
    
    app_id = os.getenv("EBAY_APP_ID")
    cert_id = os.getenv("EBAY_CERT_ID")
    
    if not app_id or not cert_id:
        raise HTTPException(
            status_code=400,
            detail="eBay credentials not set. Add EBAY_APP_ID and EBAY_CERT_ID to Railway environment variables"
        )
    
    ebay_client = EbayAuth(app_id, cert_id)
    
    try:
        results = await ebay_client.search_pokemon_cards(query, limit=5)
        
        # Format for easy reading
        items = []
        if "itemSummaries" in results:
            for item in results["itemSummaries"]:
                items.append({
                    "title": item.get("title", ""),
                    "price": item.get("price", {}).get("value", "N/A"),
                    "currency": item.get("price", {}).get("currency", ""),
                    "condition": item.get("condition", ""),
                    "url": item.get("itemWebUrl", "")
                })
        
        return {
            "success": True,
            "query": query,
            "total_found": results.get("total", 0),
            "items": items,
            "message": "eBay API is working! You can now get live Pokemon card data."
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "Check your eBay credentials and try again"
        }