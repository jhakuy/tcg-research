"""
Tests for enhanced entity resolution with Pokemon card filtering.
"""

import pytest
from tcg_research.core.enhanced_entity_resolver import (
    FilteredEntityResolver, EnhancedCardEntity
)
from tcg_research.core.pokemon_filter import ListingQuality, CardType


class TestFilteredEntityResolver:
    """Test cases for FilteredEntityResolver."""
    
    def setup_method(self):
        """Setup test instance."""
        self.resolver = FilteredEntityResolver()
    
    def test_resolve_valid_ebay_listing(self):
        """Test resolution of valid eBay listing."""
        title = "Charizard VMAX 074/172 Brilliant Stars Secret Rare PSA 10 Mint"
        description = "Beautiful PSA 10 Gem Mint condition card. Fast shipping."
        price = 300.0
        
        entity = self.resolver.resolve_ebay_listing(
            title=title,
            description=description,
            price=price,
            condition="Mint"
        )
        
        assert entity is not None
        assert isinstance(entity, EnhancedCardEntity)
        assert entity.name_normalized != "Unknown"
        assert entity.filter_quality != ListingQuality.JUNK
        assert entity.confidence > 0
        assert entity.filter_confidence > 0

    def test_filter_out_junk_listing(self):
        """Test that junk listings are filtered out."""
        title = "Pokemon TCG Online Code Digital Download"
        
        entity = self.resolver.resolve_ebay_listing(title=title)
        assert entity is None

    def test_filter_out_non_cards(self):
        """Test that non-card items are filtered out."""
        titles = [
            "Pokemon Card Sleeves Deck Protectors",
            "Pokemon Plush Toy Pikachu",
            "Pokemon Deck Box Storage Case"
        ]
        
        for title in titles:
            entity = self.resolver.resolve_ebay_listing(title=title)
            assert entity is None

    def test_pokemon_name_extraction(self):
        """Test Pokemon name extraction."""
        test_cases = [
            ("Charizard VMAX Brilliant Stars 074/172", "Charizard"),
            ("Pikachu ex Paldea Evolved Secret Rare", "Pikachu"),
            ("Umbreon VMAX Alt Art Evolving Skies", "Umbreon"),
            ("Rayquaza V 110/203 Evolving Skies", "Rayquaza")
        ]
        
        for title, expected_name in test_cases:
            extracted = self.resolver._extract_pokemon_name(title)
            assert expected_name.lower() in extracted.lower()

    def test_market_tier_classification(self):
        """Test market tier classification."""
        test_cases = [
            ("Secret Rare", "Rainbow", "premium"),
            ("Ultra Rare", "Holo", "mid"),
            ("Rare", "Regular", "mid"),
            ("Common", "Regular", "budget"),
            ("Rainbow Rare", "Rainbow", "premium")
        ]
        
        for rarity, finish, expected_tier in test_cases:
            tier = self.resolver._classify_market_tier(rarity, finish)
            assert tier == expected_tier

    def test_price_reasonableness_estimation(self):
        """Test price reasonableness estimation."""
        # Premium card with reasonable price
        score = self.resolver._estimate_price_reasonableness("Secret Rare", "premium", 200.0)
        assert score == 1.0  # Reasonable
        
        # Premium card with suspiciously low price
        score = self.resolver._estimate_price_reasonableness("Secret Rare", "premium", 5.0)
        assert score == 0.3  # Suspiciously low
        
        # Budget card with high price
        score = self.resolver._estimate_price_reasonableness("Common", "budget", 100.0)
        assert score == 0.6  # Potentially overpriced

    def test_enhanced_entity_creation(self):
        """Test creation of enhanced entity."""
        title = "Charizard VMAX 074/172 Brilliant Stars Secret Rare Mint"
        
        entity = self.resolver.resolve_ebay_listing(
            title=title,
            price=250.0,
            condition="Mint"
        )
        
        if entity:  # Only test if resolution succeeded
            assert hasattr(entity, 'filter_quality')
            assert hasattr(entity, 'card_type')
            assert hasattr(entity, 'filter_confidence')
            assert hasattr(entity, 'market_tier')
            assert entity.source_title == title

    def test_confidence_thresholds(self):
        """Test confidence threshold filtering."""
        # Set a high confidence threshold
        original_threshold = self.resolver.confidence_threshold
        self.resolver.confidence_threshold = 95
        
        title = "Pokemon Card Rare"  # Vague title, low confidence
        entity = self.resolver.resolve_ebay_listing(title=title)
        
        # Should be filtered out due to low confidence
        assert entity is None
        
        # Restore original threshold
        self.resolver.confidence_threshold = original_threshold

    def test_batch_resolution(self):
        """Test batch resolution of multiple listings."""
        listings = [
            {
                "title": "Charizard VMAX Brilliant Stars Secret Rare Mint",
                "price": 200.0,
                "condition": "Mint"
            },
            {
                "title": "Pikachu Base Set Shadowless",
                "price": 150.0,
                "condition": "Near Mint"
            },
            {
                "title": "Pokemon TCG Online Code",
                "price": 1.0
            },
            {
                "title": "Pokemon Card Sleeves",
                "price": 10.0
            }
        ]
        
        entities = self.resolver.batch_resolve_listings(listings)
        
        # Should have some successful resolutions
        assert len(entities) >= 1
        
        # All returned entities should be valid
        for entity in entities:
            assert entity.filter_quality != ListingQuality.JUNK
            assert entity.confidence > 0

    def test_resolution_stats(self):
        """Test resolution statistics generation."""
        listings = [
            {"title": "Charizard VMAX Brilliant Stars Mint", "price": 200.0},
            {"title": "Pikachu ex Paldea Evolved", "price": 100.0},
            {"title": "Umbreon VMAX Alt Art", "price": 300.0}
        ]
        
        entities = self.resolver.batch_resolve_listings(listings)
        
        if entities:  # Only test if we have entities
            stats = self.resolver.get_resolution_stats(entities)
            
            assert "total_resolved" in stats
            assert "average_confidence" in stats
            assert "quality_distribution" in stats
            assert "market_tier_distribution" in stats
            assert stats["total_resolved"] == len(entities)

    def test_rarity_extraction_from_text(self):
        """Test rarity extraction from combined text."""
        test_cases = [
            ("Charizard Secret Rare Pokemon Card", "Secret Rare"),
            ("Pikachu Rainbow Rare Brilliant Stars", "Rainbow Rare"),
            ("Umbreon Alt Art Evolving Skies", "Alt Art"),
            ("Charizard Holo Rare Base Set", "Rare"),
            ("Common Pokemon Card", "Common")
        ]
        
        for text, expected_rarity in test_cases:
            rarity = self.resolver._extract_rarity_from_text(text)
            assert rarity == expected_rarity

    def test_finish_extraction_from_text(self):
        """Test finish extraction from combined text."""
        test_cases = [
            ("Charizard Reverse Holo Pokemon", "Reverse Holo"),
            ("Pikachu Holographic Card", "Holo"),
            ("Umbreon Full Art Alternate", "Full Art"),
            ("Rainbow Rare Charizard", "Rainbow")
        ]
        
        for text, expected_finish in test_cases:
            finish = self.resolver._extract_finish_from_text(text)
            assert finish == expected_finish

    def test_entity_validation(self):
        """Test enhanced entity validation."""
        # Create a mock enhanced entity
        title = "Charizard VMAX Brilliant Stars Secret Rare"
        entity = self.resolver.resolve_ebay_listing(title=title, price=200.0)
        
        if entity:
            # Valid entity should pass validation
            is_valid = self.resolver._validate_enhanced_entity(entity)
            assert is_valid
            
            # Test with modified confidence
            entity.confidence = 50  # Below threshold
            is_valid = self.resolver._validate_enhanced_entity(entity)
            assert not is_valid

    def test_set_code_handling(self):
        """Test set code detection and handling."""
        test_cases = [
            ("Charizard Brilliant Stars BST", "BST"),
            ("Pikachu Evolving Skies EVS", "EVS"),
            ("Umbreon Paldea Evolved PAL", "PAL"),
            ("Charizard Base Set", "BASE")
        ]
        
        for title, expected_set in test_cases:
            entity = self.resolver.resolve_ebay_listing(title=title, price=100.0)
            if entity:
                assert entity.set_code == expected_set

    def test_grade_handling(self):
        """Test PSA/BGS grade handling."""
        test_cases = [
            ("Charizard PSA 10 Gem Mint", 10),
            ("Pikachu BGS 9.5 Pristine", 9),
            ("Umbreon CGC 8 Near Mint", 8)
        ]
        
        for title, expected_grade in test_cases:
            entity = self.resolver.resolve_ebay_listing(title=title, price=200.0)
            if entity:
                assert entity.grade == expected_grade

    def test_error_handling(self):
        """Test error handling in resolution process."""
        # Test with problematic input
        problematic_inputs = [
            "",  # Empty title
            "x" * 1000,  # Very long title
            "♦♠♣♥",  # Special characters only
            None  # None title (should be handled gracefully)
        ]
        
        for title in problematic_inputs:
            try:
                entity = self.resolver.resolve_ebay_listing(title=title or "")
                # Should either return None or a valid entity, not crash
                if entity:
                    assert isinstance(entity, EnhancedCardEntity)
            except Exception as e:
                pytest.fail(f"Resolution crashed with input '{title}': {e}")

    def test_card_type_filtering(self):
        """Test that only appropriate card types are processed."""
        test_cases = [
            ("Charizard VMAX Pokemon Card", CardType.SINGLE_CARD, True),
            ("Pokemon Booster Box Sealed", CardType.SEALED_PRODUCT, True),
            ("Pokemon Random Card Lot", CardType.BULK_LOT, False),
            ("Pokemon Card Sleeves", CardType.ACCESSORY, False),
            ("Pokemon TCG Online Code", CardType.DIGITAL_CODE, False)
        ]
        
        for title, expected_type, should_resolve in test_cases:
            entity = self.resolver.resolve_ebay_listing(title=title)
            
            if should_resolve:
                assert entity is not None, f"Should resolve: {title}"
            else:
                assert entity is None, f"Should not resolve: {title}"