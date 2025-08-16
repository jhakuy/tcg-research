"""
Tests for Pokemon card filtering and validation system.
"""

import pytest
from tcg_research.core.pokemon_filter import (
    PokemonCardFilter, ListingQuality, CardType, FilterResult
)


class TestPokemonCardFilter:
    """Test cases for PokemonCardFilter."""
    
    def setup_method(self):
        """Setup test instance."""
        self.filter = PokemonCardFilter()
    
    def test_filter_valid_single_card(self):
        """Test filtering of valid single card listings."""
        title = "Charizard VMAX Brilliant Stars 074/172 Secret Rare Pokemon Card Mint"
        result = self.filter.filter_listing(title, "", 150.0)
        
        assert result.is_valid
        assert result.card_type == CardType.SINGLE_CARD
        assert result.quality in [ListingQuality.GOOD, ListingQuality.EXCELLENT]
        assert result.detected_set is not None
        assert result.confidence_score > 0.7

    def test_filter_tcg_online_codes(self):
        """Test filtering out TCG Online codes."""
        titles = [
            "Pokemon TCG Online Code - Brilliant Stars Booster Pack",
            "PTCGO Digital Code Card Unused",
            "Pokemon Online Code Redeem Card"
        ]
        
        for title in titles:
            result = self.filter.filter_listing(title)
            assert not result.is_valid
            assert result.quality == ListingQuality.JUNK
            assert "exclusion pattern" in " ".join(result.reasons)

    def test_filter_non_card_items(self):
        """Test filtering out non-card items."""
        titles = [
            "Pokemon Card Sleeves Deck Protectors 65ct",
            "Pokemon Deck Box Storage Case",
            "Pokemon Playmat Official Tournament Mat",
            "Pokemon Plush Toy Pikachu 10 inch"
        ]
        
        for title in titles:
            result = self.filter.filter_listing(title)
            assert not result.is_valid or result.card_type == CardType.ACCESSORY

    def test_filter_bulk_lots(self):
        """Test filtering of bulk/random lots."""
        titles = [
            "Pokemon Random Card Lot 100 Cards Mixed",
            "Choose Your Pokemon Card Complete Your Set",
            "Pokemon Mystery Box 20 Cards Rare Included",
            "Pokemon Bulk Lot 500 Cards Assorted"
        ]
        
        for title in titles:
            result = self.filter.filter_listing(title)
            assert result.card_type == CardType.BULK_LOT

    def test_filter_fake_proxy_cards(self):
        """Test filtering out fake/proxy cards."""
        titles = [
            "Pokemon Charizard Custom Proxy Card Fan Made",
            "Pokemon Fake Card Reproduction Not Official",
            "Pokemon Charizard Proxy Custom Art",
            "Pokemon Card Reprint Not Original"
        ]
        
        for title in titles:
            result = self.filter.filter_listing(title)
            assert not result.is_valid
            assert result.quality == ListingQuality.JUNK

    def test_set_detection(self):
        """Test set code detection."""
        test_cases = [
            ("Charizard ex Paldea Evolved PAL", "PAL"),
            ("Pikachu VMAX Vivid Voltage VIV", "VIV"),
            ("Umbreon VMAX Evolving Skies", "EVS"),
            ("Charizard Base Set WOTC", "BASE"),
            ("Mew 151 Pokemon Card", "MEW")
        ]
        
        for title, expected_set in test_cases:
            result = self.filter.filter_listing(title)
            assert result.detected_set == expected_set

    def test_card_number_extraction(self):
        """Test card number extraction."""
        test_cases = [
            ("Charizard #006/165 Brilliant Stars", "006"),
            ("Pikachu 025/172 Pokemon Card", "025"),
            ("Umbreon No. 094 Evolving Skies", "094"),
            ("Charizard 150 Base Set", "150")
        ]
        
        for title, expected_number in test_cases:
            result = self.filter.filter_listing(title)
            assert result.detected_number == expected_number

    def test_condition_detection(self):
        """Test condition detection."""
        test_cases = [
            ("Charizard Mint Condition Pokemon Card", "mint"),
            ("Pikachu Near Mint NM Pokemon", "near_mint"),
            ("Umbreon Lightly Played LP Card", "lightly_played"),
            ("Charizard Heavily Played Pokemon", "heavily_played"),
            ("Damaged Pokemon Card As Is", "damaged")
        ]
        
        for title, expected_condition in test_cases:
            result = self.filter.filter_listing(title)
            assert result.detected_condition == expected_condition

    def test_grade_detection(self):
        """Test grading detection."""
        test_cases = [
            ("Charizard PSA 10 Gem Mint", 10),
            ("Pikachu BGS 9.5 Beckett", 9),  # Should round down
            ("Umbreon CGC 8.5 Graded", 8),   # Should round down
            ("Charizard PSA 7 Near Mint", 7)
        ]
        
        for title, expected_grade in test_cases:
            result = self.filter.filter_listing(title)
            assert result.detected_grade == expected_grade

    def test_quality_scoring(self):
        """Test quality scoring algorithm."""
        # Excellent quality listing
        excellent_title = ("Charizard VMAX Secret Rare 074/172 Brilliant Stars "
                          "PSA 10 Gem Mint Professional Photos Fast Shipping")
        result = self.filter.filter_listing(excellent_title, "", 300.0)
        assert result.quality in [ListingQuality.EXCELLENT, ListingQuality.GOOD]
        
        # Poor quality listing
        poor_title = ("Pokemon Card ??? As Is No Returns Read Description "
                     "Damaged Beyond Repair")
        result = self.filter.filter_listing(poor_title)
        assert result.quality in [ListingQuality.POOR, ListingQuality.JUNK]

    def test_price_reasonableness(self):
        """Test price reasonableness checks."""
        title = "Charizard VMAX Secret Rare Brilliant Stars"
        
        # Reasonable price
        result = self.filter.filter_listing(title, "", 150.0)
        assert result.confidence_score > 0.5
        
        # Suspiciously low price
        result = self.filter.filter_listing(title, "", 0.50)
        assert result.confidence_score < 0.8  # Should be penalized
        
        # Suspiciously high price
        result = self.filter.filter_listing(title, "", 50000.0)
        assert result.confidence_score < 0.8  # Should be penalized

    def test_sealed_product_detection(self):
        """Test sealed product detection."""
        titles = [
            "Pokemon Brilliant Stars Booster Box Sealed",
            "Pokemon Elite Trainer Box Evolving Skies Unopened",
            "Pokemon Theme Deck Factory Sealed",
            "Pokemon Tin Collection Box Sealed Product"
        ]
        
        for title in titles:
            result = self.filter.filter_listing(title)
            assert result.card_type == CardType.SEALED_PRODUCT

    def test_batch_filtering(self):
        """Test batch filtering functionality."""
        listings = [
            {"title": "Charizard VMAX Brilliant Stars Mint", "price": 150.0},
            {"title": "Pokemon TCG Online Code", "price": 1.0},
            {"title": "Pikachu Base Set Shadowless", "price": 200.0},
            {"title": "Random Pokemon Card Lot", "price": 50.0},
            {"title": "Pokemon Card Sleeves", "price": 10.0}
        ]
        
        results = self.filter.batch_filter(listings)
        assert len(results) == 5
        
        # Check that some were filtered out
        valid_results = [r for r in results if r.is_valid]
        assert len(valid_results) < len(results)

    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        # High confidence: single card with set and number
        title = "Charizard ex 006/165 Paldea Evolved Secret Rare Mint"
        result = self.filter.filter_listing(title, "", 200.0)
        high_confidence = result.confidence_score
        
        # Lower confidence: missing information
        title = "Pokemon Card Rare"
        result = self.filter.filter_listing(title)
        low_confidence = result.confidence_score
        
        assert high_confidence > low_confidence

    def test_filter_stats(self):
        """Test filter statistics generation."""
        listings = [
            {"title": "Charizard VMAX Brilliant Stars Mint", "price": 150.0},
            {"title": "Pikachu Base Set", "price": 100.0},
            {"title": "Pokemon TCG Online Code", "price": 1.0},
        ]
        
        results = self.filter.batch_filter(listings)
        stats = self.filter.get_filter_stats(results)
        
        assert "total_processed" in stats
        assert "valid_listings" in stats
        assert "quality_distribution" in stats
        assert "card_type_distribution" in stats
        assert stats["total_processed"] == 3

    def test_title_normalization(self):
        """Test title normalization."""
        messy_title = "Pokemon   Charizard!!!   ex    006/165   Paldea???  Evolved"
        normalized = self.filter._normalize_title(messy_title)
        
        assert "Pokemon Charizard! ex 006/165 Paldea? Evolved" == normalized
        assert "  " not in normalized  # No double spaces
        assert "!!!" not in normalized  # Excessive punctuation removed

    def test_suspicious_patterns(self):
        """Test detection of suspicious patterns."""
        suspicious_titles = [
            "Pokemon Card ??? Unknown Condition",
            "Charizard Error Card Misprinted",
            "Pokemon Card N/A Information",
            "Rare Find!!! Super Ultra Rare Pokemon!!!"
        ]
        
        for title in suspicious_titles:
            result = self.filter.filter_listing(title)
            # Should have reduced confidence or quality
            assert result.confidence_score < 0.8 or result.quality != ListingQuality.EXCELLENT

    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Empty title
        result = self.filter.filter_listing("")
        assert not result.is_valid
        
        # Very long title
        long_title = "Pokemon " + "Charizard " * 50 + "Card"
        result = self.filter.filter_listing(long_title)
        assert result is not None  # Should not crash
        
        # Special characters
        special_title = "Pokémon Charizard ♦ ★ ◆ Card"
        result = self.filter.filter_listing(special_title)
        assert result is not None  # Should not crash

    def test_rarity_extraction(self):
        """Test rarity extraction from text."""
        test_cases = [
            ("Charizard Secret Rare SR", "Secret Rare"),
            ("Pikachu Rainbow Rare", "Rainbow Rare"),
            ("Umbreon Full Art", "Full Art"),
            ("Charizard Alt Art", "Alt Art"),
            ("Pikachu Holo Rare", "Rare"),
            ("Common Pokemon Card", "Common")
        ]
        
        for text, expected_rarity in test_cases:
            rarity = self.filter._extract_rarity_from_text(text)
            assert rarity == expected_rarity

    def test_finish_extraction(self):
        """Test finish/variant extraction."""
        test_cases = [
            ("Charizard Reverse Holo", "Reverse Holo"),
            ("Pikachu Holographic Card", "Holo"),
            ("Umbreon Full Art", "Full Art"),
            ("Charizard Rainbow Rare", "Rainbow"),
            ("Pikachu Gold Card", "Gold")
        ]
        
        for text, expected_finish in test_cases:
            finish = self.filter._extract_finish_from_text(text)
            assert finish == expected_finish