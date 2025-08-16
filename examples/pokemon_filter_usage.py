"""
Example usage of the Pokemon card filtering and validation system.

This script demonstrates how to use the enhanced filtering system
to process eBay listings and extract high-quality Pokemon card data.
"""

import asyncio
from typing import List, Dict, Any

from tcg_research.core.pokemon_filter import PokemonCardFilter, ListingQuality, CardType
from tcg_research.core.enhanced_entity_resolver import FilteredEntityResolver
from tcg_research.mcp.enhanced_ebay_browse import search_enhanced_pokemon_cards


async def demo_basic_filtering():
    """Demonstrate basic Pokemon card filtering."""
    print("=== Basic Pokemon Card Filtering Demo ===\n")
    
    # Initialize filter
    pokemon_filter = PokemonCardFilter()
    
    # Sample eBay listing titles (mix of good and bad)
    sample_listings = [
        # Valid cards
        {
            "title": "Charizard VMAX 074/172 Brilliant Stars Secret Rare PSA 10 Mint",
            "price": 299.99,
            "description": "Beautiful PSA 10 graded card. Fast shipping with tracking."
        },
        {
            "title": "Pikachu ex 057/191 Paldea Evolved Full Art Near Mint",
            "price": 45.00,
            "description": "Near mint condition, stored in sleeve."
        },
        {
            "title": "Umbreon VMAX Alt Art 215/203 Evolving Skies Mint",
            "price": 180.00,
            "description": "Mint condition alternate art card."
        },
        
        # Junk/filtered listings
        {
            "title": "Pokemon TCG Online Code - Digital Download",
            "price": 0.99,
            "description": "Unused TCGO code for online play."
        },
        {
            "title": "Pokemon Card Sleeves Ultra Pro 65ct Deck Protectors",
            "price": 8.99,
            "description": "High quality card sleeves for protection."
        },
        {
            "title": "Choose Your Pokemon Card Complete Your Set Random",
            "price": 25.00,
            "description": "Pick any card from our inventory to complete your set."
        },
        {
            "title": "Pokemon Charizard Proxy Custom Fan Art Card",
            "price": 15.00,
            "description": "Custom made proxy card with alternate artwork."
        },
        
        # Edge cases
        {
            "title": "Pokemon Card ??? Condition Unknown As Is",
            "price": 5.00,
            "description": "Found in storage, not sure of condition. Sold as is."
        },
        {
            "title": "Rare Pokemon Card Misprinted Error Charizard",
            "price": 500.00,
            "description": "Extremely rare misprint error card."
        }
    ]
    
    print(f"Processing {len(sample_listings)} sample listings...\n")
    
    # Filter each listing
    for i, listing in enumerate(sample_listings, 1):
        print(f"Listing {i}: {listing['title'][:60]}...")
        
        result = pokemon_filter.filter_listing(
            title=listing["title"],
            description=listing["description"],
            price=listing["price"]
        )
        
        print(f"  Valid: {result.is_valid}")
        print(f"  Quality: {result.quality.value}")
        print(f"  Type: {result.card_type.value}")
        print(f"  Confidence: {result.confidence_score:.2f}")
        
        if result.detected_set:
            print(f"  Set: {result.detected_set}")
        if result.detected_number:
            print(f"  Number: {result.detected_number}")
        if result.detected_condition:
            print(f"  Condition: {result.detected_condition}")
        if result.detected_grade:
            print(f"  Grade: PSA {result.detected_grade}")
            
        if result.reasons:
            print(f"  Issues: {', '.join(result.reasons[:2])}")
            
        print()
    
    # Generate batch statistics
    results = pokemon_filter.batch_filter(sample_listings)
    stats = pokemon_filter.get_filter_stats(results)
    
    print("=== Filtering Statistics ===")
    print(f"Total processed: {stats['total_processed']}")
    print(f"Valid listings: {stats['valid_listings']}")
    print(f"Invalid listings: {stats['invalid_listings']}")
    print(f"Average confidence: {stats['average_confidence']:.2f}")
    print(f"Set detection rate: {stats['set_detection_rate']:.1%}")
    print(f"Grade detection rate: {stats['grade_detection_rate']:.1%}")
    
    print("\nQuality Distribution:")
    for quality, count in stats['quality_distribution'].items():
        print(f"  {quality}: {count}")
        
    print("\nCard Type Distribution:")
    for card_type, count in stats['card_type_distribution'].items():
        print(f"  {card_type}: {count}")


async def demo_enhanced_entity_resolution():
    """Demonstrate enhanced entity resolution."""
    print("\n=== Enhanced Entity Resolution Demo ===\n")
    
    # Initialize enhanced resolver
    resolver = FilteredEntityResolver()
    
    # Sample high-quality listings
    quality_listings = [
        {
            "title": "Charizard VMAX 074/172 Brilliant Stars Secret Rare PSA 10",
            "description": "Perfect PSA 10 gem mint condition. Professionally graded.",
            "price": 299.99,
            "condition": "Mint"
        },
        {
            "title": "Pikachu VMAX 188/185 Vivid Voltage Rainbow Rare NM",
            "description": "Near mint rainbow rare. Stored in toploader.",
            "price": 120.00,
            "condition": "Near Mint"
        },
        {
            "title": "Umbreon VMAX Alt Art 215/203 Evolving Skies Mint",
            "description": "Beautiful alternate art card in mint condition.",
            "price": 175.00,
            "condition": "Mint"
        }
    ]
    
    print(f"Resolving {len(quality_listings)} high-quality listings...\n")
    
    resolved_entities = []
    
    for i, listing in enumerate(quality_listings, 1):
        print(f"Resolving listing {i}: {listing['title'][:50]}...")
        
        entity = resolver.resolve_ebay_listing(
            title=listing["title"],
            description=listing["description"],
            price=listing["price"],
            condition=listing["condition"]
        )
        
        if entity:
            resolved_entities.append(entity)
            print(f"  ✓ Resolved to: {entity.canonical_sku}")
            print(f"  Pokemon: {entity.name_normalized}")
            print(f"  Set: {entity.set_code}")
            print(f"  Rarity: {entity.rarity}")
            print(f"  Market Tier: {entity.market_tier}")
            print(f"  Confidence: {entity.confidence:.1f}")
            print(f"  Filter Quality: {entity.filter_quality.value}")
            print(f"  Filter Confidence: {entity.filter_confidence:.2f}")
            if entity.grade:
                print(f"  Grade: PSA {entity.grade}")
        else:
            print(f"  ✗ Failed to resolve")
            
        print()
    
    # Generate resolution statistics
    if resolved_entities:
        stats = resolver.get_resolution_stats(resolved_entities)
        
        print("=== Resolution Statistics ===")
        print(f"Successfully resolved: {stats['total_resolved']}")
        print(f"Average confidence: {stats['average_confidence']:.1f}")
        print(f"Average filter confidence: {stats['average_filter_confidence']:.2f}")
        
        print("\nMarket Tier Distribution:")
        for tier, count in stats['market_tier_distribution'].items():
            print(f"  {tier}: {count}")
            
        print("\nSet Distribution:")
        for set_code, count in stats['set_distribution'].items():
            print(f"  {set_code}: {count}")


async def demo_ebay_search_integration():
    """Demonstrate integration with eBay search."""
    print("\n=== eBay Search Integration Demo ===\n")
    
    # Note: This uses mock data since we don't have real eBay API credentials
    print("Searching for 'Charizard Brilliant Stars' with enhanced filtering...")
    
    results = await search_enhanced_pokemon_cards(
        query="Charizard Brilliant Stars",
        condition="mint",
        price_min=50.0,
        price_max=500.0,
        max_results=10
    )
    
    print(f"Found {len(results)} filtered results:\n")
    
    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   Price: ${result['price']}")
        print(f"   Quality: {result['filter_quality']}")
        print(f"   Type: {result['card_type']}")
        print(f"   Confidence: {result['filter_confidence']}")
        print()


async def demo_specific_card_search():
    """Demonstrate searching for specific cards."""
    print("\n=== Specific Card Search Demo ===\n")
    
    # Examples of specific card searches
    search_examples = [
        {
            "pokemon_name": "Charizard",
            "set_code": "BST", 
            "rarity": "Secret Rare",
            "description": "Charizard from Brilliant Stars secret rare"
        },
        {
            "pokemon_name": "Pikachu",
            "set_code": "VIV",
            "rarity": "Rainbow Rare", 
            "description": "Pikachu VMAX rainbow rare from Vivid Voltage"
        },
        {
            "pokemon_name": "Umbreon",
            "set_code": "EVS",
            "rarity": "Alt Art",
            "description": "Umbreon VMAX alternate art from Evolving Skies"
        }
    ]
    
    print("Demonstrating specific card search patterns...\n")
    
    # Initialize filter for demonstration
    pokemon_filter = PokemonCardFilter()
    
    for example in search_examples:
        print(f"Searching for: {example['description']}")
        
        # Simulate search query construction
        query_parts = [example["pokemon_name"]]
        if example.get("set_code"):
            query_parts.append(example["set_code"])
        if example.get("rarity"):
            query_parts.append(example["rarity"])
            
        search_query = " ".join(query_parts)
        print(f"Search query: '{search_query}'")
        
        # Simulate some results that would match
        mock_titles = [
            f"{example['pokemon_name']} VMAX {example.get('set_code', '')} {example.get('rarity', '')} Mint",
            f"{example['pokemon_name']} {example.get('rarity', '')} {example.get('set_code', '')} Near Mint",
            f"{example['pokemon_name']} {example.get('set_code', '')} Pokemon Card {example.get('rarity', '')}"
        ]
        
        print("Sample matching results:")
        for j, title in enumerate(mock_titles, 1):
            result = pokemon_filter.filter_listing(title, "", 100.0 + j * 50)
            print(f"  {j}. {title}")
            print(f"     Quality: {result.quality.value}, Confidence: {result.confidence_score:.2f}")
            
        print()


def demo_filtering_rules():
    """Demonstrate various filtering rules and edge cases."""
    print("\n=== Filtering Rules Demonstration ===\n")
    
    pokemon_filter = PokemonCardFilter()
    
    # Test different categories of listings
    test_categories = {
        "Valid Single Cards": [
            "Charizard ex 006/165 Paldea Evolved Secret Rare Mint",
            "Pikachu VMAX 188/185 Vivid Voltage Rainbow Rare",
            "Umbreon VMAX 215/203 Evolving Skies Alt Art"
        ],
        "TCG Online Codes (Should Filter)": [
            "Pokemon TCG Online Code - Brilliant Stars",
            "PTCGO Digital Code Unused",
            "Pokemon Online Booster Pack Code"
        ],
        "Accessories (Should Filter)": [
            "Pokemon Card Sleeves Ultra Pro 65ct",
            "Pokemon Deck Box Elite Trainer Storage",
            "Pokemon Playmat Official Tournament Mat"
        ],
        "Bulk Lots (Should Filter)": [
            "Pokemon Random Card Lot 100 Cards",
            "Choose Your Pokemon Cards Complete Set",
            "Pokemon Bulk Collection 500+ Cards"
        ],
        "Fake/Proxy Cards (Should Filter)": [
            "Pokemon Charizard Custom Proxy Card",
            "Pokemon Fake Card Not Official Reproduction",
            "Pokemon Fan Made Custom Art Card"
        ],
        "Graded Cards (Should Pass)": [
            "Charizard Base Set PSA 10 Gem Mint",
            "Pikachu BGS 9.5 Beckett Pristine",
            "Umbreon CGC 9 Mint+"
        ]
    }
    
    for category, titles in test_categories.items():
        print(f"=== {category} ===")
        
        for title in titles:
            result = pokemon_filter.filter_listing(title, "", 50.0)
            
            status = "✓ PASS" if result.is_valid else "✗ FILTERED"
            print(f"{status} {title}")
            print(f"      Quality: {result.quality.value}, Type: {result.card_type.value}")
            
            if result.reasons:
                print(f"      Reasons: {', '.join(result.reasons[:2])}")
                
        print()


async def main():
    """Run all demonstration examples."""
    print("Pokemon Card Filtering and Validation System Demo")
    print("=" * 55)
    
    # Run all demos
    await demo_basic_filtering()
    await demo_enhanced_entity_resolution()
    await demo_ebay_search_integration()
    await demo_specific_card_search()
    demo_filtering_rules()
    
    print("\n=== Demo Complete ===")
    print("The filtering system successfully:")
    print("• Filters out junk listings (codes, accessories, fakes)")
    print("• Identifies card types and quality levels")
    print("• Extracts Pokemon names, sets, and card details")
    print("• Provides confidence scores for all decisions")
    print("• Integrates with entity resolution for canonical data")
    print("• Supports batch processing and statistics")


if __name__ == "__main__":
    asyncio.run(main())