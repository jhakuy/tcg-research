"""
Enhanced entity resolution with integrated Pokemon card filtering.

This module extends the base entity resolver with sophisticated filtering
capabilities to handle eBay listing data quality and validation.
"""

import re
from typing import Dict, List, Optional, Tuple
import structlog
from pydantic import BaseModel

from tcg_research.core.entity_resolver import EntityResolver, CardEntity
from tcg_research.core.pokemon_filter import PokemonCardFilter, FilterResult, ListingQuality, CardType

logger = structlog.get_logger()


class EnhancedCardEntity(CardEntity):
    """Enhanced card entity with filtering metadata."""
    filter_quality: ListingQuality
    card_type: CardType
    filter_confidence: float
    source_title: str
    validation_reasons: List[str]
    
    # Additional metadata from filtering
    detected_condition: Optional[str] = None
    price_estimate: Optional[float] = None
    market_tier: Optional[str] = None  # premium, mid, budget


class FilteredEntityResolver:
    """Enhanced entity resolver with integrated Pokemon card filtering."""
    
    def __init__(self):
        self.base_resolver = EntityResolver()
        self.pokemon_filter = PokemonCardFilter()
        self.confidence_threshold = 85
        self.quality_threshold = ListingQuality.ACCEPTABLE
        
        # Market tier classifications
        self.market_tiers = {
            'premium': ['secret rare', 'rainbow rare', 'gold rare', 'alt art', 'full art'],
            'mid': ['rare', 'ultra rare', 'holo rare'],
            'budget': ['common', 'uncommon', 'regular rare']
        }

    def resolve_ebay_listing(
        self,
        title: str,
        description: str = "",
        price: Optional[float] = None,
        condition: Optional[str] = None,
        seller_info: Optional[Dict] = None
    ) -> Optional[EnhancedCardEntity]:
        """
        Resolve an eBay listing to an enhanced card entity.
        
        Args:
            title: eBay listing title
            description: eBay listing description
            price: Listed price
            condition: Listed condition
            seller_info: Seller information (feedback, etc.)
            
        Returns:
            EnhancedCardEntity if valid, None if filtered out
        """
        
        # Step 1: Apply Pokemon card filtering
        filter_result = self.pokemon_filter.filter_listing(title, description, price)
        
        # Early exit if listing is junk or below quality threshold
        if not filter_result.is_valid or filter_result.quality == ListingQuality.JUNK:
            logger.debug(
                "eBay listing filtered out",
                title=title[:50],
                quality=filter_result.quality.value,
                reasons=filter_result.reasons
            )
            return None
            
        # Only process single cards and high-quality sealed products
        if filter_result.card_type not in [CardType.SINGLE_CARD, CardType.SEALED_PRODUCT]:
            logger.debug(
                "Non-card listing filtered out", 
                title=title[:50],
                card_type=filter_result.card_type.value
            )
            return None
            
        # Step 2: Extract card information using filtered data
        card_info = self._extract_card_info_from_filter(filter_result, title, description)
        
        # Step 3: Use base entity resolver for normalization
        base_entity = self.base_resolver.resolve_card(
            name=card_info['name'],
            set_info=card_info['set_info'],
            number=card_info['number'],
            rarity=card_info['rarity'],
            finish=card_info['finish'],
            grade=filter_result.detected_grade,
            source="ebay_enhanced"
        )
        
        if not base_entity:
            logger.warning(
                "Base entity resolution failed",
                title=title[:50],
                extracted_info=card_info
            )
            return None
            
        # Step 4: Enhance with filtering metadata and market analysis
        enhanced_entity = self._create_enhanced_entity(
            base_entity, filter_result, title, price, card_info
        )
        
        # Step 5: Final validation
        if not self._validate_enhanced_entity(enhanced_entity):
            return None
            
        logger.info(
            "Enhanced entity resolved",
            sku=enhanced_entity.canonical_sku,
            quality=enhanced_entity.filter_quality.value,
            confidence=enhanced_entity.confidence,
            filter_confidence=enhanced_entity.filter_confidence
        )
        
        return enhanced_entity

    def _extract_card_info_from_filter(
        self, 
        filter_result: FilterResult, 
        title: str, 
        description: str
    ) -> Dict[str, str]:
        """Extract card information using filter results as a guide."""
        
        # Start with filter-detected information
        card_info = {
            'name': '',
            'set_info': filter_result.detected_set or '',
            'number': filter_result.detected_number or '',
            'rarity': '',
            'finish': 'Regular'
        }
        
        # Extract Pokemon name from title
        name = self._extract_pokemon_name(filter_result.normalized_title)
        card_info['name'] = name
        
        # Extract rarity information
        rarity = self._extract_rarity_from_text(title + " " + description)
        card_info['rarity'] = rarity or ''
        
        # Extract finish/variant information
        finish = self._extract_finish_from_text(title + " " + description)
        card_info['finish'] = finish or 'Regular'
        
        return card_info

    def _extract_pokemon_name(self, title: str) -> str:
        """Extract Pokemon name from normalized title."""
        
        # Common Pokemon name patterns
        pokemon_patterns = [
            # Basic pattern: Pokemon name at start
            r'^([A-Za-z][A-Za-z\s]+?)(?:\s+(?:ex|EX|GX|V|VMAX|VSTAR|&)|\s+\d|\s*$)',
            
            # Pattern with card type: "Charizard ex"
            r'\b([A-Za-z][A-Za-z\s]+?)\s+(?:ex|EX|GX|V|VMAX|VSTAR)\b',
            
            # Pattern with set: "Pokemon name - Set"
            r'^([A-Za-z][A-Za-z\s]+?)\s*[-–]\s*',
            
            # Fallback: first capitalized words
            r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)'
        ]
        
        for pattern in pokemon_patterns:
            match = re.search(pattern, title.strip())
            if match:
                name = match.group(1).strip()
                # Clean up common artifacts
                name = re.sub(r'\s+', ' ', name)
                name = re.sub(r'\b(?:Pokemon|Card|TCG)\b', '', name, flags=re.IGNORECASE)
                if len(name) >= 3:  # Minimum reasonable Pokemon name length
                    return name.strip()
                    
        # If no pattern matches, try to extract the first meaningful word
        words = title.split()
        if words:
            first_word = words[0]
            if len(first_word) >= 3 and first_word.isalpha():
                return first_word
                
        return "Unknown"

    def _extract_rarity_from_text(self, text: str) -> Optional[str]:
        """Extract rarity information from text."""
        
        rarity_patterns = {
            'Secret Rare': [r'\bsecret\s+rare\b', r'\bSR\b', r'\bsecret\b'],
            'Rainbow Rare': [r'\brainbow\s+rare\b', r'\brainbow\b'],
            'Gold Rare': [r'\bgold\s+rare\b', r'\bgold\b'],
            'Alt Art': [r'\balternate\s+art\b', r'\balt\s+art\b', r'\balternative\b'],
            'Full Art': [r'\bfull\s+art\b'],
            'Ultra Rare': [r'\bultra\s+rare\b', r'\bUR\b'],
            'Rare': [r'\bholo\s+rare\b', r'\brare\s+holo\b', r'\brare\b'],
            'Uncommon': [r'\buncommon\b'],
            'Common': [r'\bcommon\b'],
            'Promo': [r'\bpromo\b', r'\bpromotional\b'],
        }
        
        text_lower = text.lower()
        
        # Check patterns in order of specificity (most specific first)
        for rarity, patterns in rarity_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return rarity
                    
        return None

    def _extract_finish_from_text(self, text: str) -> Optional[str]:
        """Extract finish/variant information from text."""
        
        finish_patterns = {
            'Reverse Holo': [r'\breverse\s+holo\b', r'\brev\s+holo\b'],
            'Holo': [r'\bholographic\b', r'\bholo\b'],
            'Full Art': [r'\bfull\s+art\b'],
            'Alt Art': [r'\balternate\s+art\b', r'\balt\s+art\b'],
            'Rainbow': [r'\brainbow\b'],
            'Gold': [r'\bgold\b'],
            'Textured': [r'\btextured\b'],
        }
        
        text_lower = text.lower()
        
        for finish, patterns in finish_patterns.items():
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    return finish
                    
        return None

    def _create_enhanced_entity(
        self,
        base_entity: CardEntity,
        filter_result: FilterResult,
        title: str,
        price: Optional[float],
        card_info: Dict[str, str]
    ) -> EnhancedCardEntity:
        """Create enhanced entity from base entity and filter results."""
        
        # Determine market tier
        market_tier = self._classify_market_tier(base_entity.rarity, card_info.get('finish', ''))
        
        # Estimate price reasonableness
        price_estimate = self._estimate_price_reasonableness(
            base_entity.rarity, market_tier, price
        )
        
        return EnhancedCardEntity(
            # Base entity fields
            canonical_sku=base_entity.canonical_sku,
            set_code=base_entity.set_code,
            card_number=base_entity.card_number,
            name_normalized=base_entity.name_normalized,
            rarity=base_entity.rarity,
            finish=base_entity.finish,
            grade=base_entity.grade,
            language=base_entity.language,
            confidence=base_entity.confidence,
            
            # Enhanced fields
            filter_quality=filter_result.quality,
            card_type=filter_result.card_type,
            filter_confidence=filter_result.confidence_score,
            source_title=title,
            validation_reasons=filter_result.reasons,
            detected_condition=filter_result.detected_condition,
            price_estimate=price_estimate,
            market_tier=market_tier
        )

    def _classify_market_tier(self, rarity: str, finish: str) -> str:
        """Classify card into market tier based on rarity and finish."""
        
        rarity_lower = rarity.lower()
        finish_lower = finish.lower()
        
        # Check premium tier first
        for tier, rarities in self.market_tiers.items():
            if any(r in rarity_lower or r in finish_lower for r in rarities):
                return tier
                
        return 'budget'  # Default

    def _estimate_price_reasonableness(
        self, 
        rarity: str, 
        market_tier: str, 
        price: Optional[float]
    ) -> Optional[float]:
        """Estimate if price is reasonable for the card type."""
        
        if price is None:
            return None
            
        # Rough price ranges by tier (these would ideally come from historical data)
        tier_ranges = {
            'premium': (50, 2000),
            'mid': (10, 200),
            'budget': (0.5, 50)
        }
        
        min_price, max_price = tier_ranges.get(market_tier, (0, 10000))
        
        if min_price <= price <= max_price:
            return 1.0  # Reasonable
        elif price < min_price:
            return 0.3  # Suspiciously low
        else:
            return 0.6  # Potentially overpriced
            
    def _validate_enhanced_entity(self, entity: EnhancedCardEntity) -> bool:
        """Final validation of enhanced entity."""
        
        # Check minimum confidence thresholds
        if entity.confidence < self.confidence_threshold:
            logger.warning(
                "Entity confidence below threshold",
                sku=entity.canonical_sku,
                confidence=entity.confidence,
                threshold=self.confidence_threshold
            )
            return False
            
        # Check filter quality
        if entity.filter_quality == ListingQuality.JUNK:
            return False
            
        # Check for required fields
        if not entity.name_normalized or entity.name_normalized == "Unknown":
            logger.warning("Entity missing valid Pokemon name", sku=entity.canonical_sku)
            return False
            
        return True

    def batch_resolve_listings(self, listings: List[Dict]) -> List[EnhancedCardEntity]:
        """Resolve multiple eBay listings in batch."""
        
        resolved_entities = []
        
        for listing in listings:
            try:
                entity = self.resolve_ebay_listing(
                    title=listing.get('title', ''),
                    description=listing.get('description', ''),
                    price=listing.get('price'),
                    condition=listing.get('condition'),
                    seller_info=listing.get('seller_info')
                )
                
                if entity:
                    resolved_entities.append(entity)
                    
            except Exception as e:
                logger.error(
                    "Failed to resolve listing",
                    title=listing.get('title', '')[:50],
                    error=str(e)
                )
                
        # Log batch statistics
        logger.info(
            "Batch entity resolution completed",
            total_listings=len(listings),
            resolved_entities=len(resolved_entities),
            success_rate=len(resolved_entities) / len(listings) if listings else 0
        )
        
        return resolved_entities

    def get_resolution_stats(self, entities: List[EnhancedCardEntity]) -> Dict:
        """Get comprehensive statistics about resolution results."""
        
        if not entities:
            return {}
            
        stats = {
            'total_resolved': len(entities),
            'average_confidence': sum(e.confidence for e in entities) / len(entities),
            'average_filter_confidence': sum(e.filter_confidence for e in entities) / len(entities),
            'quality_distribution': {},
            'market_tier_distribution': {},
            'set_distribution': {},
            'rarity_distribution': {}
        }
        
        # Quality distribution
        for quality in ListingQuality:
            stats['quality_distribution'][quality.value] = sum(
                1 for e in entities if e.filter_quality == quality
            )
            
        # Market tier distribution
        tier_counts = {}
        for entity in entities:
            tier = entity.market_tier or 'unknown'
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        stats['market_tier_distribution'] = tier_counts
        
        # Set distribution
        set_counts = {}
        for entity in entities:
            set_code = entity.set_code
            set_counts[set_code] = set_counts.get(set_code, 0) + 1
        stats['set_distribution'] = set_counts
        
        # Rarity distribution
        rarity_counts = {}
        for entity in entities:
            rarity = entity.rarity
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
        stats['rarity_distribution'] = rarity_counts
        
        return stats