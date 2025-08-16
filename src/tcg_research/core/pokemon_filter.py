"""
Sophisticated Pokemon card data filtering and validation system for eBay listings.

This module provides comprehensive filtering to remove junk listings, categorize
card variants, and implement quality scoring for Pokemon card data from eBay.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set
import structlog

logger = structlog.get_logger()


class ListingQuality(Enum):
    """Quality levels for eBay listings."""
    EXCELLENT = "excellent"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"
    JUNK = "junk"


class CardType(Enum):
    """Types of Pokemon cards."""
    SINGLE_CARD = "single_card"
    SEALED_PRODUCT = "sealed_product"
    BULK_LOT = "bulk_lot"
    ACCESSORY = "accessory"
    DIGITAL_CODE = "digital_code"
    CUSTOM_PROXY = "custom_proxy"
    UNKNOWN = "unknown"


@dataclass
class FilterResult:
    """Result of filtering operation."""
    is_valid: bool
    quality: ListingQuality
    card_type: CardType
    confidence_score: float
    reasons: List[str]
    normalized_title: str
    detected_set: Optional[str] = None
    detected_number: Optional[str] = None
    detected_condition: Optional[str] = None
    detected_grade: Optional[int] = None


class PokemonCardFilter:
    """Comprehensive filtering system for Pokemon card eBay listings."""

    def __init__(self):
        self.min_quality_threshold = ListingQuality.ACCEPTABLE
        self.min_confidence_score = 0.7
        
        # Initialize filter patterns and rules
        self._init_junk_patterns()
        self._init_set_patterns()
        self._init_condition_patterns()
        self._init_quality_indicators()

    def _init_junk_patterns(self):
        """Initialize patterns for detecting junk/irrelevant listings."""
        
        # Immediate exclusion patterns - these are never valid Pokemon cards
        self.immediate_exclusions = [
            # Digital/Online codes
            r'\b(?:tcg\s*online|ptcgo|tcgo|digital\s*code|code\s*card|online\s*code)\b',
            r'\b(?:unused\s*code|redeem\s*code|download\s*code)\b',
            
            # Non-card items
            r'\b(?:sleeves?|deck\s*box|binder|playmat|dice|coin|token)\b',
            r'\b(?:case|storage|organizer|folder|album)\b',
            r'\b(?:figure|plush|toy|statue|model)\b',
            
            # Bulk/random lots (unless specifically valuable)
            r'\b(?:random\s*(?:card|lot)|mystery\s*(?:box|pack)|grab\s*bag)\b',
            r'\b(?:choose\s*your|pick\s*your|you\s*choose|complete\s*your\s*set)\b',
            r'\b(?:lot\s*of\s*\d+|bulk\s*lot|\d+\s*card\s*lot)\b',
            
            # Fake/custom/proxy cards
            r'\b(?:fake|proxy|custom|fan\s*made|reproduction|reprint)\b',
            r'\b(?:not\s*official|unofficial|knock\s*off)\b',
            
            # Damaged/incomplete
            r'\b(?:damaged\s*beyond|water\s*damage|fire\s*damage)\b',
            r'\b(?:pieces|parts|torn|ripped\s*up)\b',
            
            # Listing issues
            r'\b(?:read\s*description|see\s*pictures|as\s*is|no\s*returns)\b',
            r'\b(?:broken|cracked|scratched\s*up)\b',
        ]
        
        # Suspicious patterns that reduce quality but don't exclude
        self.suspicious_patterns = [
            r'\b(?:minor\s*damage|slight\s*wear|edge\s*wear)\b',
            r'\b(?:\?\?+|\*\*+|!!!+)\b',  # Excessive punctuation
            r'\b(?:rare\s*find|super\s*rare|ultra\s*rare)\b',  # Hype language
            r'\b(?:look\s*at\s*pics|check\s*photos)\b',
            r'\b(?:estate\s*sale|found\s*in)\b',
        ]

    def _init_set_patterns(self):
        """Initialize patterns for detecting Pokemon sets."""
        
        # Modern set codes and names (2019-2024)
        self.modern_sets = {
            # Scarlet & Violet Series
            'PAL': ['Paldea Evolved', 'PAL'],
            'OBF': ['Obsidian Flames', 'OBF'],
            'MEW': ['151', 'MEW', 'Pokemon 151'],
            'PAR': ['Paradox Rift', 'PAR'],
            'SVI': ['Scarlet Violet Base', 'SVI', 'Scarlet & Violet'],
            
            # Sword & Shield Series  
            'CRZ': ['Crown Zenith', 'CRZ'],
            'SIT': ['Silver Tempest', 'SIT'],
            'LOR': ['Lost Origin', 'LOR'],
            'PGO': ['Pokemon GO', 'PGO'],
            'ASR': ['Astral Radiance', 'ASR'],
            'BRS': ['Brilliant Stars', 'BRS'],
            'FST': ['Fusion Strike', 'FST'],
            'CEL': ['Celebrations', 'CEL'],
            'EVS': ['Evolving Skies', 'EVS'],
            'CRE': ['Chilling Reign', 'CRE'],
            'BST': ['Battle Styles', 'BST'],
            'SHF': ['Shining Fates', 'SHF'],
            'VIV': ['Vivid Voltage', 'VIV'],
            'CPA': ['Champions Path', 'CPA', 'CP'],
            'DAA': ['Darkness Ablaze', 'DAA'],
            'RCL': ['Rebel Clash', 'RCL'],
            'SSH': ['Sword Shield Base', 'SSH', 'Sword & Shield'],
            
            # Classic sets (high value)
            'BASE': ['Base Set', 'Base', 'WOTC'],
            'JUN': ['Jungle', 'JUN'],
            'FOS': ['Fossil', 'FOS'],
            'B2': ['Base Set 2', 'Base 2'],
            'TR': ['Team Rocket', 'TR'],
            'GYM1': ['Gym Heroes', 'GYM1'],
            'GYM2': ['Gym Challenge', 'GYM2'],
            'NEO1': ['Neo Genesis', 'NEO1'],
            'NEO2': ['Neo Discovery', 'NEO2'],
            'NEO3': ['Neo Revelation', 'NEO3'],
            'NEO4': ['Neo Destiny', 'NEO4'],
        }
        
        # Pattern to match set information in titles
        self.set_pattern = re.compile(
            r'\b(?:' + '|'.join([
                item for sublist in self.modern_sets.values() 
                for item in sublist
            ]) + r')\b',
            re.IGNORECASE
        )

    def _init_condition_patterns(self):
        """Initialize condition detection patterns."""
        
        self.condition_map = {
            'mint': ['mint', 'mt', 'gem mint', 'perfect'],
            'near_mint': ['near mint', 'nm', 'near-mint', 'excellent'],
            'lightly_played': ['lightly played', 'lp', 'light play', 'very good'],
            'moderately_played': ['moderately played', 'mp', 'played', 'good'],
            'heavily_played': ['heavily played', 'hp', 'poor'],
            'damaged': ['damaged', 'dmg', 'fair'],
        }
        
        # Grading company patterns
        self.grading_patterns = {
            'psa': r'\b(?:psa\s*(?:10|9|8|7|6|5|4|3|2|1))\b',
            'bgs': r'\b(?:bgs|beckett)\s*(?:10|9\.5|9|8\.5|8|7\.5|7|6\.5|6)\b',
            'cgc': r'\b(?:cgc)\s*(?:10|9\.5|9|8\.5|8|7\.5|7|6\.5|6)\b',
        }

    def _init_quality_indicators(self):
        """Initialize quality indicators for scoring."""
        
        # Positive quality indicators
        self.quality_positive = {
            'professional_photos': [
                r'\bprofessional\s*photo', r'\bhigh\s*res', r'\bclear\s*image',
                r'\bmultiple\s*angle', r'\bfront\s*and\s*back'
            ],
            'detailed_condition': [
                r'\bcentering', r'\bcorners?', r'\bedges?', r'\bsurface',
                r'\bno\s*creases?', r'\bno\s*bends?', r'\bno\s*scratches?'
            ],
            'seller_quality': [
                r'\btop\s*rated', r'\bfast\s*shipping', r'\bfree\s*shipping',
                r'\btracked\s*shipping', r'\binsured'
            ],
            'authenticity': [
                r'\bofficial', r'\boriginal', r'\bauthentic', r'\bgenuine',
                r'\bnot\s*proxy', r'\bnot\s*fake'
            ],
        }
        
        # Negative quality indicators  
        self.quality_negative = {
            'poor_description': [
                r'\bas\s*is', r'\bno\s*returns?', r'\bsold\s*as\s*seen',
                r'\bread\s*description', r'\bcheck\s*photo'
            ],
            'condition_issues': [
                r'\bscuffs?', r'\bscratches?', r'\bdents?', r'\bbends?',
                r'\bwear', r'\bused', r'\bdamage'
            ],
            'unclear_listing': [
                r'\b\?\?+', r'\bmight\s*be', r'\bnot\s*sure',
                r'\bthink\s*it\s*is', r'\bbelieve\s*it'
            ],
        }

    def filter_listing(self, title: str, description: str = "", 
                      price: Optional[float] = None) -> FilterResult:
        """
        Filter and analyze a single eBay listing.
        
        Args:
            title: Listing title
            description: Listing description (optional)
            price: Listing price (optional)
            
        Returns:
            FilterResult with analysis and recommendation
        """
        
        # Combine title and description for analysis
        full_text = f"{title} {description}".lower()
        reasons = []
        
        # Step 1: Check for immediate exclusions
        is_junk, junk_reasons = self._check_immediate_exclusions(full_text)
        if is_junk:
            return FilterResult(
                is_valid=False,
                quality=ListingQuality.JUNK,
                card_type=CardType.UNKNOWN,
                confidence_score=0.0,
                reasons=junk_reasons,
                normalized_title=self._normalize_title(title)
            )
        
        # Step 2: Determine card type
        card_type = self._detect_card_type(full_text)
        
        # Step 3: Extract card information
        detected_set = self._extract_set_info(title)
        detected_number = self._extract_card_number(title)
        detected_condition = self._extract_condition(full_text)
        detected_grade = self._extract_grade(full_text)
        
        # Step 4: Calculate quality score
        quality_score = self._calculate_quality_score(full_text, price)
        quality_level = self._score_to_quality(quality_score)
        
        # Step 5: Calculate overall confidence
        confidence = self._calculate_confidence(
            card_type, detected_set, detected_number, quality_score
        )
        
        # Step 6: Determine if listing is valid
        is_valid = (
            quality_level != ListingQuality.JUNK and
            confidence >= self.min_confidence_score and
            card_type != CardType.UNKNOWN
        )
        
        return FilterResult(
            is_valid=is_valid,
            quality=quality_level,
            card_type=card_type,
            confidence_score=confidence,
            reasons=reasons,
            normalized_title=self._normalize_title(title),
            detected_set=detected_set,
            detected_number=detected_number,
            detected_condition=detected_condition,
            detected_grade=detected_grade
        )

    def _check_immediate_exclusions(self, text: str) -> Tuple[bool, List[str]]:
        """Check for patterns that immediately exclude listings."""
        reasons = []
        
        for pattern in self.immediate_exclusions:
            if re.search(pattern, text, re.IGNORECASE):
                reasons.append(f"Matched exclusion pattern: {pattern}")
                
        return len(reasons) > 0, reasons

    def _detect_card_type(self, text: str) -> CardType:
        """Detect the type of Pokemon product."""
        
        # Digital codes
        if re.search(r'\b(?:code|tcg\s*online|digital)\b', text):
            return CardType.DIGITAL_CODE
            
        # Sealed products
        sealed_patterns = [
            r'\b(?:booster\s*(?:pack|box)|elite\s*trainer|theme\s*deck)\b',
            r'\b(?:tin|collection\s*box|starter\s*deck)\b',
            r'\b(?:sealed|unopened|factory\s*sealed)\b'
        ]
        if any(re.search(p, text) for p in sealed_patterns):
            return CardType.SEALED_PRODUCT
            
        # Bulk lots
        bulk_patterns = [
            r'\b(?:lot\s*of|\d+\s*cards?|bulk|random)\b',
            r'\b(?:mixed\s*lot|card\s*lot)\b'
        ]
        if any(re.search(p, text) for p in bulk_patterns):
            return CardType.BULK_LOT
            
        # Accessories
        accessory_patterns = [
            r'\b(?:sleeve|protector|binder|case|box)\b',
            r'\b(?:playmat|dice|coin|counter)\b'
        ]
        if any(re.search(p, text) for p in accessory_patterns):
            return CardType.ACCESSORY
            
        # Custom/proxy cards
        custom_patterns = [
            r'\b(?:custom|proxy|fan\s*made|ooak)\b',
            r'\b(?:altered|painted|custom\s*art)\b'
        ]
        if any(re.search(p, text) for p in custom_patterns):
            return CardType.CUSTOM_PROXY
            
        # Single card (default for Pokemon cards)
        single_patterns = [
            r'\b(?:pokemon\s*card|trading\s*card|single\s*card)\b',
            r'\b(?:holo|rare|common|uncommon)\b',
            r'\b(?:ex|gx|v|vmax|vstar)\b'
        ]
        if any(re.search(p, text) for p in single_patterns):
            return CardType.SINGLE_CARD
            
        return CardType.UNKNOWN

    def _extract_set_info(self, title: str) -> Optional[str]:
        """Extract set information from title."""
        match = self.set_pattern.search(title)
        if match:
            found_set = match.group().lower()
            # Map to canonical set code
            for code, names in self.modern_sets.items():
                if any(found_set in name.lower() for name in names):
                    return code
        return None

    def _extract_card_number(self, title: str) -> Optional[str]:
        """Extract card number from title."""
        # Common number patterns: #123, 123/200, 123/200, No. 123
        patterns = [
            r'#(\d+)',
            r'(\d+)/\d+',
            r'no\.?\s*(\d+)',
            r'\b(\d{1,3})\b'  # Simple number (use cautiously)
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_condition(self, text: str) -> Optional[str]:
        """Extract condition from text."""
        for condition, patterns in self.condition_map.items():
            for pattern in patterns:
                if re.search(r'\b' + re.escape(pattern) + r'\b', text, re.IGNORECASE):
                    return condition
        return None

    def _extract_grade(self, text: str) -> Optional[int]:
        """Extract grading information from text."""
        for company, pattern in self.grading_patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Extract the numeric grade
                grade_match = re.search(r'(\d+(?:\.\d+)?)', match.group())
                if grade_match:
                    return int(float(grade_match.group(1)))
        return None

    def _calculate_quality_score(self, text: str, price: Optional[float]) -> float:
        """Calculate quality score based on various indicators."""
        score = 0.5  # Base score
        
        # Positive indicators
        for category, patterns in self.quality_positive.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 0.1
                    
        # Negative indicators
        for category, patterns in self.quality_negative.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score -= 0.15
                    
        # Price reasonableness (if available)
        if price is not None:
            if price < 1.0:  # Suspiciously low
                score -= 0.2
            elif price > 10000:  # Suspiciously high
                score -= 0.3
                
        # Length and detail bonus
        if len(text) > 100:  # Detailed listing
            score += 0.1
            
        return max(0.0, min(1.0, score))

    def _score_to_quality(self, score: float) -> ListingQuality:
        """Convert numeric score to quality enum."""
        if score >= 0.8:
            return ListingQuality.EXCELLENT
        elif score >= 0.65:
            return ListingQuality.GOOD
        elif score >= 0.5:
            return ListingQuality.ACCEPTABLE
        elif score >= 0.3:
            return ListingQuality.POOR
        else:
            return ListingQuality.JUNK

    def _calculate_confidence(self, card_type: CardType, detected_set: Optional[str],
                            detected_number: Optional[str], quality_score: float) -> float:
        """Calculate overall confidence in the listing analysis."""
        confidence = 0.0
        
        # Card type confidence
        if card_type == CardType.SINGLE_CARD:
            confidence += 0.4
        elif card_type == CardType.SEALED_PRODUCT:
            confidence += 0.3
        elif card_type in [CardType.BULK_LOT, CardType.ACCESSORY]:
            confidence += 0.2
        else:
            confidence += 0.1
            
        # Set detection confidence
        if detected_set:
            confidence += 0.3
            
        # Card number confidence
        if detected_number:
            confidence += 0.2
            
        # Quality score contribution
        confidence += quality_score * 0.1
        
        return min(1.0, confidence)

    def _normalize_title(self, title: str) -> str:
        """Normalize title for consistent processing."""
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', title.strip())
        
        # Remove excessive punctuation
        normalized = re.sub(r'[!]{2,}', '!', normalized)
        normalized = re.sub(r'[\?]{2,}', '?', normalized)
        normalized = re.sub(r'[\*]{2,}', '*', normalized)
        
        # Standardize Pokemon name variations
        normalized = re.sub(r'\bpokemon\b', 'Pokemon', normalized, flags=re.IGNORECASE)
        
        return normalized

    def batch_filter(self, listings: List[Dict]) -> List[FilterResult]:
        """Filter multiple listings in batch."""
        results = []
        
        for listing in listings:
            result = self.filter_listing(
                title=listing.get('title', ''),
                description=listing.get('description', ''),
                price=listing.get('price')
            )
            results.append(result)
            
        # Log batch statistics
        valid_count = sum(1 for r in results if r.is_valid)
        quality_counts = {}
        for quality in ListingQuality:
            quality_counts[quality.value] = sum(
                1 for r in results if r.quality == quality
            )
            
        logger.info(
            "Batch filtering completed",
            total=len(listings),
            valid=valid_count,
            quality_distribution=quality_counts
        )
        
        return results

    def get_filter_stats(self, results: List[FilterResult]) -> Dict:
        """Get comprehensive statistics about filtering results."""
        if not results:
            return {}
            
        stats = {
            'total_processed': len(results),
            'valid_listings': sum(1 for r in results if r.is_valid),
            'invalid_listings': sum(1 for r in results if not r.is_valid),
            'quality_distribution': {},
            'card_type_distribution': {},
            'average_confidence': sum(r.confidence_score for r in results) / len(results),
            'set_detection_rate': sum(1 for r in results if r.detected_set) / len(results),
            'grade_detection_rate': sum(1 for r in results if r.detected_grade) / len(results),
        }
        
        # Quality distribution
        for quality in ListingQuality:
            stats['quality_distribution'][quality.value] = sum(
                1 for r in results if r.quality == quality
            )
            
        # Card type distribution
        for card_type in CardType:
            stats['card_type_distribution'][card_type.value] = sum(
                1 for r in results if r.card_type == card_type
            )
            
        return stats