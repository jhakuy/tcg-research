# Pokemon Card Data Filtering and Validation System

## Overview

A comprehensive filtering and validation system for Pokemon card data from eBay that addresses the critical issue of junk listings, irrelevant results, and data quality problems in TCG market analysis.

## Problem Solved

The original system suffered from poor data quality due to eBay searches returning:
- Pokemon TCG Online codes (digital, not physical cards)
- "Choose your card" bulk/random listings
- Non-card accessories (sleeves, boxes, playmats)
- Fake/proxy/custom cards
- Multiple variants mixed together
- Low-quality listings with poor descriptions

## Solution Architecture

### 1. Core Filtering Engine (`pokemon_filter.py`)

**PokemonCardFilter Class**
- **Immediate Exclusions**: Patterns that automatically exclude listings (codes, accessories, fakes)
- **Quality Scoring**: Multi-factor algorithm that scores listing quality (0.0-1.0)
- **Card Type Detection**: Classifies listings into categories (single_card, sealed_product, etc.)
- **Information Extraction**: Detects sets, card numbers, conditions, grades
- **Confidence Calculation**: Provides confidence scores for all decisions

**Key Features:**
- 50+ exclusion patterns for junk detection
- Modern Pokemon set recognition (2019-2024)
- PSA/BGS/CGC grade detection
- Condition mapping (Mint, NM, LP, MP, HP, Damaged)
- Price reasonableness checks
- Batch processing capabilities

### 2. Enhanced Entity Resolution (`enhanced_entity_resolver.py`)

**FilteredEntityResolver Class**
- Integrates Pokemon filtering with entity resolution
- Market tier classification (premium, mid, budget)
- Enhanced confidence thresholds
- Pokemon name extraction and normalization
- Set code and card number validation

**EnhancedCardEntity Model**
- Extends base CardEntity with filtering metadata
- Includes quality scores, card types, validation reasons
- Market tier and price estimates
- Source title preservation for debugging

### 3. Enhanced eBay Integration (`enhanced_ebay_browse.py`)

**EnhancedEbayBrowseClient Class**
- Integrates filtering directly with eBay API calls
- Quality-based result filtering and sorting
- Specific card search capabilities
- Market data aggregation
- Concurrent batch processing

## Filter Categories and Rules

### Immediate Exclusions (Junk Filtering)

**Digital/Online Codes**
```python
r'\b(?:tcg\s*online|ptcgo|tcgo|digital\s*code|code\s*card|online\s*code)\b'
r'\b(?:unused\s*code|redeem\s*code|download\s*code)\b'
```

**Non-Card Items**
```python
r'\b(?:sleeves?|deck\s*box|binder|playmat|dice|coin|token)\b'
r'\b(?:case|storage|organizer|folder|album)\b'
r'\b(?:figure|plush|toy|statue|model)\b'
```

**Bulk/Random Lots**
```python
r'\b(?:random\s*(?:card|lot)|mystery\s*(?:box|pack)|grab\s*bag)\b'
r'\b(?:choose\s*your|pick\s*your|you\s*choose|complete\s*your\s*set)\b'
```

**Fake/Custom Cards**
```python
r'\b(?:fake|proxy|custom|fan\s*made|reproduction|reprint)\b'
r'\b(?:not\s*official|unofficial|knock\s*off)\b'
```

### Quality Scoring Factors

**Positive Indicators (+0.1 each)**
- Professional photos mentioned
- Detailed condition descriptions
- Fast/tracked shipping
- Authenticity statements

**Negative Indicators (-0.15 each)**
- "As is" / "No returns" language
- Condition issues mentioned
- Excessive punctuation/hype language
- Unclear descriptions

**Price Reasonableness**
- Suspiciously low prices (<$1): -0.2
- Suspiciously high prices (>$10k): -0.3
- Detailed listings (>100 chars): +0.1

### Set Detection

Supports 40+ Pokemon sets with multiple recognition patterns:

**Modern Sets (2019-2024)**
- Scarlet & Violet series (PAL, OBF, MEW, PAR, SVI)
- Sword & Shield series (CRZ, SIT, LOR, PGO, ASR, BRS, FST, etc.)

**Classic Sets**
- WOTC era (Base Set, Jungle, Fossil, Team Rocket)
- Neo series (Genesis, Discovery, Revelation, Destiny)

## Usage Examples

### Basic Filtering
```python
from tcg_research.core.pokemon_filter import PokemonCardFilter

filter_system = PokemonCardFilter()

# Filter a single listing
result = filter_system.filter_listing(
    title="Charizard VMAX 074/172 Brilliant Stars Secret Rare PSA 10",
    description="Gem mint condition, fast shipping",
    price=299.99
)

print(f"Valid: {result.is_valid}")
print(f"Quality: {result.quality.value}")
print(f"Card Type: {result.card_type.value}")
print(f"Confidence: {result.confidence_score}")
print(f"Detected Set: {result.detected_set}")
```

### Enhanced Entity Resolution
```python
from tcg_research.core.enhanced_entity_resolver import FilteredEntityResolver

resolver = FilteredEntityResolver()

# Resolve eBay listing to canonical entity
entity = resolver.resolve_ebay_listing(
    title="Charizard VMAX Brilliant Stars Secret Rare Mint",
    price=250.0,
    condition="Mint"
)

if entity:
    print(f"SKU: {entity.canonical_sku}")
    print(f"Pokemon: {entity.name_normalized}")
    print(f"Market Tier: {entity.market_tier}")
    print(f"Filter Quality: {entity.filter_quality.value}")
```

### Enhanced eBay Search
```python
from tcg_research.mcp.enhanced_ebay_browse import EnhancedEbayBrowseClient

# Note: Requires eBay API credentials
client = EnhancedEbayBrowseClient(app_id="your_app_id", cert_id="your_cert_id")

# Search with filtering
results = await client.search_pokemon_cards(
    query="Charizard Brilliant Stars",
    condition="mint",
    price_min=50.0,
    price_max=500.0,
    max_results=20
)

# Only high-quality, relevant listings returned
for item in results:
    print(f"{item.title} - Quality: {item.filter_quality.value}")
```

## Quality Levels

### ListingQuality Enum
- **EXCELLENT** (≥0.8): Professional listings with detailed info
- **GOOD** (≥0.65): Good quality with most required info
- **ACCEPTABLE** (≥0.5): Adequate quality, some missing info
- **POOR** (≥0.3): Low quality but potentially valid
- **JUNK** (<0.3): Should be filtered out

### CardType Enum
- **SINGLE_CARD**: Individual Pokemon cards (target)
- **SEALED_PRODUCT**: Booster boxes, theme decks, etc.
- **BULK_LOT**: Random card lots (usually filtered)
- **ACCESSORY**: Sleeves, boxes, etc. (filtered)
- **DIGITAL_CODE**: Online codes (filtered)
- **CUSTOM_PROXY**: Fake/custom cards (filtered)

## Integration Points

### 1. Data Ingestion Pipeline
The enhanced filtering integrates with the existing ingestion pipeline in `ingestion.py`:

```python
# Enhanced ingestion with filtering
pipeline = DataIngestionPipeline(
    db_session=session,
    enhanced_ebay_client=enhanced_client,
    use_enhanced_filtering=True
)
```

### 2. API Endpoints
Can be integrated with existing API endpoints to provide filtered search results.

### 3. ML Feature Generation
Filtered data improves ML model quality by removing noise and ensuring consistent data.

## Performance Considerations

### Conservative Approach
- **Better to exclude questionable items than include junk**
- High confidence thresholds (85%+ for entity resolution)
- Multiple validation layers
- Extensive pattern matching for exclusions

### Efficiency Features
- Batch processing support
- Early exit for obvious junk listings
- Compiled regex patterns for performance
- Comprehensive statistics tracking

## Configuration Options

### Filter Thresholds
```python
filter_system = PokemonCardFilter()
filter_system.min_quality_threshold = ListingQuality.GOOD  # Stricter
filter_system.min_confidence_score = 0.8  # Higher confidence required
```

### Entity Resolution
```python
resolver = FilteredEntityResolver()
resolver.confidence_threshold = 90  # Stricter entity resolution
resolver.quality_threshold = ListingQuality.EXCELLENT  # Only best listings
```

## Testing

Comprehensive test suites provided:
- `test_pokemon_filter.py`: 25+ test cases for filtering logic
- `test_enhanced_entity_resolver.py`: Entity resolution integration tests
- Edge case handling and error recovery
- Performance and batch processing tests

## Example Usage Script

Run the demonstration script to see the system in action:

```bash
python examples/pokemon_filter_usage.py
```

This script demonstrates:
- Basic filtering of various listing types
- Entity resolution integration
- Quality scoring examples
- Batch processing capabilities
- Integration with eBay search (mock data)

## Statistics and Monitoring

The system provides comprehensive statistics:

```python
stats = filter_system.get_filter_stats(results)
# Returns:
# - Total processed
# - Valid vs invalid listings
# - Quality distribution
# - Card type distribution
# - Average confidence scores
# - Detection rates (sets, grades, etc.)
```

## Conservative Design Philosophy

The system follows a conservative "better safe than sorry" approach:

1. **Strict Exclusions**: Immediate filtering of obvious junk
2. **High Confidence Requirements**: Multiple validation layers
3. **Quality Thresholds**: Only process high-quality listings
4. **Detailed Logging**: Track all filtering decisions
5. **Graceful Degradation**: Fallback to basic systems if enhanced filtering fails

## Future Enhancements

1. **Machine Learning**: Train ML models on filtered data to improve quality detection
2. **Seller Reputation**: Integrate eBay seller feedback scores
3. **Image Analysis**: Use computer vision to validate card images
4. **Price Validation**: Dynamic price reasonableness based on market data
5. **User Feedback**: Learn from user corrections to improve filtering

## Dependencies

All required dependencies are already listed in `requirements.txt`:
- `structlog`: Logging
- `fuzzywuzzy`: String matching
- `pydantic`: Data models
- `httpx`: HTTP client
- `sqlalchemy`: Database ORM

## Summary

This comprehensive filtering system transforms the raw, noisy eBay search results into high-quality, structured Pokemon card data suitable for market analysis and ML model training. By implementing conservative filtering with multiple validation layers, the system ensures that only relevant, high-quality Pokemon card listings are processed, dramatically improving the reliability of market predictions and investment recommendations.