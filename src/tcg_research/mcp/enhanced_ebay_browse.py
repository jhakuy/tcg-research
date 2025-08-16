"""
Enhanced eBay Browse API client with integrated Pokemon card filtering.

This module extends the base eBay client with sophisticated filtering
and validation for Pokemon card listings.
"""

from typing import Any, Dict, List, Optional
import asyncio
import httpx
import structlog
from pydantic import BaseModel

from tcg_research.mcp.ebay_browse import EbayBrowseClient, EbayItem
from tcg_research.core.enhanced_entity_resolver import FilteredEntityResolver, EnhancedCardEntity
from tcg_research.core.pokemon_filter import ListingQuality, CardType

logger = structlog.get_logger()


class FilteredEbayItem(EbayItem):
    """Enhanced eBay item with filtering metadata."""
    filter_quality: ListingQuality
    card_type: CardType
    filter_confidence: float
    validation_reasons: List[str]
    enhanced_entity: Optional[EnhancedCardEntity] = None


class EnhancedEbayBrowseClient:
    """Enhanced eBay Browse API client with Pokemon card filtering."""
    
    def __init__(self, app_id: str, cert_id: str):
        self.base_client = EbayBrowseClient(app_id, cert_id)
        self.entity_resolver = FilteredEntityResolver()
        
        # Configuration
        self.max_results_per_query = 100
        self.min_quality = ListingQuality.ACCEPTABLE
        self.enable_entity_resolution = True
        
        # Pokemon-specific category filters
        self.pokemon_categories = [
            "183454",  # Pokemon Individual Cards
            "31395",   # Pokemon Sealed Products  
        ]
        
        # Quality filters for eBay search
        self.quality_filters = {
            "conditionIds": "1000,1500,2000,2500,3000",  # New to Good condition
            "buyingOptions": "FIXED_PRICE,AUCTION",
            "itemLocationCountry": "US",
            "deliveryCountry": "US"
        }

    async def search_pokemon_cards(
        self,
        query: str,
        condition: Optional[str] = None,
        price_min: Optional[float] = None,
        price_max: Optional[float] = None,
        max_results: int = 50,
        include_entity_resolution: bool = True
    ) -> List[FilteredEbayItem]:
        """
        Search for Pokemon cards with enhanced filtering.
        
        Args:
            query: Search query (Pokemon name, set, etc.)
            condition: Item condition filter
            price_min: Minimum price filter
            price_max: Maximum price filter
            max_results: Maximum results to return
            include_entity_resolution: Whether to resolve entities
            
        Returns:
            List of filtered and enhanced eBay items
        """
        
        logger.info("Enhanced Pokemon card search", query=query, max_results=max_results)
        
        # Build eBay filters
        filters = self.quality_filters.copy()
        
        if condition:
            condition_map = {
                "new": "1000",
                "mint": "1000,1500", 
                "near_mint": "1500,2000",
                "excellent": "2000",
                "good": "2500,3000"
            }
            if condition.lower() in condition_map:
                filters["conditionIds"] = condition_map[condition.lower()]
                
        if price_min is not None:
            filters["priceCurrency"] = "USD"
            filters["price"] = f"[{price_min}.."
            if price_max is not None:
                filters["price"] = f"[{price_min}..{price_max}]"
        elif price_max is not None:
            filters["priceCurrency"] = "USD"
            filters["price"] = f"[..{price_max}]"
            
        # Search with base client
        try:
            raw_items = await self.base_client.search_items(
                query=f"Pokemon {query}",
                category_ids=self.pokemon_categories,
                filter_params=filters,
                limit=min(max_results * 3, 200)  # Get extra to filter
            )
        except Exception as e:
            logger.error("eBay search failed", query=query, error=str(e))
            return []
            
        # Apply Pokemon card filtering
        filtered_items = await self._filter_and_enhance_items(
            raw_items, include_entity_resolution
        )
        
        # Sort by quality and confidence
        filtered_items.sort(
            key=lambda x: (
                x.filter_quality.value,
                -x.filter_confidence,
                -x.enhanced_entity.confidence if x.enhanced_entity else 0
            )
        )
        
        # Limit results
        result_items = filtered_items[:max_results]
        
        logger.info(
            "Enhanced search completed",
            query=query,
            raw_count=len(raw_items),
            filtered_count=len(filtered_items),
            final_count=len(result_items)
        )
        
        return result_items

    async def _filter_and_enhance_items(
        self, 
        items: List[EbayItem],
        include_entity_resolution: bool
    ) -> List[FilteredEbayItem]:
        """Filter and enhance eBay items with Pokemon card filtering."""
        
        filtered_items = []
        
        for item in items:
            try:
                # Apply Pokemon card filtering
                filter_result = self.entity_resolver.pokemon_filter.filter_listing(
                    title=item.title,
                    description="",  # eBay API doesn't include description in search
                    price=item.price
                )
                
                # Skip items that don't meet quality threshold
                if (filter_result.quality == ListingQuality.JUNK or
                    not filter_result.is_valid or
                    filter_result.card_type not in [CardType.SINGLE_CARD, CardType.SEALED_PRODUCT]):
                    continue
                    
                # Create filtered item
                filtered_item = FilteredEbayItem(
                    **item.dict(),
                    filter_quality=filter_result.quality,
                    card_type=filter_result.card_type,
                    filter_confidence=filter_result.confidence_score,
                    validation_reasons=filter_result.reasons
                )
                
                # Optional entity resolution
                if include_entity_resolution and self.enable_entity_resolution:
                    try:
                        enhanced_entity = self.entity_resolver.resolve_ebay_listing(
                            title=item.title,
                            description="",
                            price=item.price,
                            condition=item.condition
                        )
                        filtered_item.enhanced_entity = enhanced_entity
                        
                    except Exception as e:
                        logger.warning(
                            "Entity resolution failed for item",
                            item_id=item.item_id,
                            title=item.title[:50],
                            error=str(e)
                        )
                        
                filtered_items.append(filtered_item)
                
            except Exception as e:
                logger.error(
                    "Failed to filter item",
                    item_id=item.item_id,
                    title=item.title[:50],
                    error=str(e)
                )
                
        return filtered_items

    async def search_specific_card(
        self,
        pokemon_name: str,
        set_code: Optional[str] = None,
        card_number: Optional[str] = None,
        rarity: Optional[str] = None,
        condition: Optional[str] = None,
        max_results: int = 20
    ) -> List[FilteredEbayItem]:
        """
        Search for a specific Pokemon card with precise filtering.
        
        Args:
            pokemon_name: Name of the Pokemon
            set_code: Set code (e.g., "PAL", "EVS")
            card_number: Card number
            rarity: Card rarity
            condition: Desired condition
            max_results: Maximum results
            
        Returns:
            List of highly relevant filtered items
        """
        
        # Build precise query
        query_parts = [pokemon_name]
        
        if set_code:
            query_parts.append(set_code)
        if card_number:
            query_parts.append(f"#{card_number}")
        if rarity:
            query_parts.append(rarity)
            
        query = " ".join(query_parts)
        
        # Search with higher quality thresholds
        old_min_quality = self.min_quality
        self.min_quality = ListingQuality.GOOD
        
        try:
            results = await self.search_pokemon_cards(
                query=query,
                condition=condition,
                max_results=max_results,
                include_entity_resolution=True
            )
            
            # Additional filtering for specific card search
            precise_results = []
            for item in results:
                if item.enhanced_entity:
                    # Check if entity matches search criteria
                    entity = item.enhanced_entity
                    
                    # Pokemon name match
                    if pokemon_name.lower() in entity.name_normalized.lower():
                        score = 1.0
                        
                        # Set match bonus
                        if set_code and entity.set_code == set_code.upper():
                            score += 0.5
                            
                        # Card number match bonus
                        if (card_number and entity.card_number and 
                            card_number in entity.card_number):
                            score += 0.3
                            
                        # Rarity match bonus
                        if rarity and rarity.lower() in entity.rarity.lower():
                            score += 0.2
                            
                        # Add match score to item for sorting
                        item.match_score = score
                        precise_results.append(item)
                        
            # Sort by match score and quality
            precise_results.sort(
                key=lambda x: (-getattr(x, 'match_score', 0), x.filter_quality.value)
            )
            
            return precise_results
            
        finally:
            self.min_quality = old_min_quality

    async def get_market_data(
        self,
        pokemon_name: str,
        set_code: Optional[str] = None,
        days_back: int = 30
    ) -> Dict[str, Any]:
        """
        Get market data for a Pokemon card including recent sales and listings.
        
        Args:
            pokemon_name: Pokemon name
            set_code: Optional set code
            days_back: Days of history to include
            
        Returns:
            Market data summary
        """
        
        # Search for recent listings
        active_listings = await self.search_specific_card(
            pokemon_name=pokemon_name,
            set_code=set_code,
            max_results=100
        )
        
        # TODO: Add sold listings search (requires different eBay endpoint)
        # For now, analyze active listings
        
        if not active_listings:
            return {
                "pokemon_name": pokemon_name,
                "set_code": set_code,
                "active_listings": 0,
                "error": "No listings found"
            }
            
        # Calculate market metrics
        prices = [item.price for item in active_listings if item.price]
        
        market_data = {
            "pokemon_name": pokemon_name,
            "set_code": set_code,
            "active_listings": len(active_listings),
            "price_data": {
                "min_price": min(prices) if prices else None,
                "max_price": max(prices) if prices else None,
                "avg_price": sum(prices) / len(prices) if prices else None,
                "median_price": sorted(prices)[len(prices)//2] if prices else None,
            },
            "quality_distribution": {},
            "condition_distribution": {},
            "seller_data": {
                "unique_sellers": len(set(item.seller_username for item in active_listings)),
                "avg_seller_feedback": None  # Would need seller details from eBay
            }
        }
        
        # Quality distribution
        for quality in ListingQuality:
            count = sum(1 for item in active_listings if item.filter_quality == quality)
            market_data["quality_distribution"][quality.value] = count
            
        # Condition distribution
        condition_counts = {}
        for item in active_listings:
            condition = item.condition or "Unknown"
            condition_counts[condition] = condition_counts.get(condition, 0) + 1
        market_data["condition_distribution"] = condition_counts
        
        return market_data

    async def batch_search_cards(
        self,
        card_searches: List[Dict[str, str]],
        max_concurrent: int = 5
    ) -> Dict[str, List[FilteredEbayItem]]:
        """
        Search for multiple cards concurrently.
        
        Args:
            card_searches: List of search parameters
            max_concurrent: Maximum concurrent requests
            
        Returns:
            Dictionary mapping search keys to results
        """
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def search_single(search_params: Dict[str, str]) -> Tuple[str, List[FilteredEbayItem]]:
            async with semaphore:
                key = f"{search_params.get('pokemon_name', '')}_{search_params.get('set_code', '')}"
                
                try:
                    results = await self.search_specific_card(**search_params)
                    return key, results
                except Exception as e:
                    logger.error("Batch search failed", search=search_params, error=str(e))
                    return key, []
                    
        # Execute searches concurrently
        tasks = [search_single(params) for params in card_searches]
        results = await asyncio.gather(*tasks)
        
        return dict(results)

    def get_search_stats(self, items: List[FilteredEbayItem]) -> Dict[str, Any]:
        """Get comprehensive statistics for search results."""
        
        if not items:
            return {"total_items": 0}
            
        stats = {
            "total_items": len(items),
            "with_entities": sum(1 for item in items if item.enhanced_entity),
            "quality_distribution": {},
            "card_type_distribution": {},
            "price_stats": {},
            "set_distribution": {},
            "condition_distribution": {}
        }
        
        # Quality distribution
        for quality in ListingQuality:
            stats["quality_distribution"][quality.value] = sum(
                1 for item in items if item.filter_quality == quality
            )
            
        # Card type distribution
        for card_type in CardType:
            stats["card_type_distribution"][card_type.value] = sum(
                1 for item in items if item.card_type == card_type
            )
            
        # Price statistics
        prices = [item.price for item in items if item.price]
        if prices:
            stats["price_stats"] = {
                "min": min(prices),
                "max": max(prices),
                "avg": sum(prices) / len(prices),
                "median": sorted(prices)[len(prices)//2]
            }
            
        # Set distribution (from entities)
        set_counts = {}
        for item in items:
            if item.enhanced_entity:
                set_code = item.enhanced_entity.set_code
                set_counts[set_code] = set_counts.get(set_code, 0) + 1
        stats["set_distribution"] = set_counts
        
        # Condition distribution
        condition_counts = {}
        for item in items:
            condition = item.condition or "Unknown"
            condition_counts[condition] = condition_counts.get(condition, 0) + 1
        stats["condition_distribution"] = condition_counts
        
        return stats


# Mock implementation for development
async def search_enhanced_pokemon_cards(
    query: str,
    condition: Optional[str] = None,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    max_results: int = 50
) -> List[Dict[str, Any]]:
    """
    Mock function for enhanced Pokemon card search.
    This would be replaced with actual eBay API calls in production.
    """
    
    logger.info("Enhanced eBay search requested (MOCK)", query=query)
    
    # Return mock data with filtering applied
    mock_results = [
        {
            "item_id": f"mock_{i}",
            "title": f"Pokemon {query} #{i:03d} - Mint Condition",
            "price": 25.99 + (i * 5),
            "currency": "USD",
            "condition": "Near Mint",
            "listing_type": "BuyItNow",
            "seller": f"seller_{i}",
            "url": f"https://ebay.com/mock_{i}",
            "filter_quality": "good",
            "card_type": "single_card",
            "filter_confidence": 0.85,
            "note": "MOCK DATA - Enhanced filtering applied"
        }
        for i in range(min(max_results, 10))
    ]
    
    return mock_results