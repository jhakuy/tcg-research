"""Entity resolution for matching cards across data sources."""

import re

import structlog
from fuzzywuzzy import process
from pydantic import BaseModel

logger = structlog.get_logger()


class CardEntity(BaseModel):
    """Canonical card entity."""
    canonical_sku: str
    set_code: str
    card_number: str
    name_normalized: str
    rarity: str
    finish: str = "Regular"
    grade: int | None = None
    language: str = "EN"
    confidence: float


class EntityResolver:
    """Resolves card entities across data sources."""

    # Common rarity mappings
    RARITY_MAPPINGS = {
        "common": "Common",
        "uncommon": "Uncommon",
        "rare": "Rare",
        "ultra rare": "Ultra Rare",
        "secret rare": "Secret Rare",
        "rainbow rare": "Rainbow Rare",
        "gold rare": "Gold Rare",
        "full art": "Full Art",
        "alternate art": "Alt Art",
        "promo": "Promo",
        "special": "Special",
    }

    # Finish type mappings
    FINISH_MAPPINGS = {
        "regular": "Regular",
        "reverse holo": "Reverse Holo",
        "holo": "Holo",
        "full art": "Full Art",
        "alt art": "Alt Art",
        "rainbow": "Rainbow",
        "gold": "Gold",
        "textured": "Textured",
    }

    def __init__(self) -> None:
        self.confidence_threshold = 85  # Minimum match confidence

    def resolve_card(
        self,
        name: str,
        set_info: str | None = None,
        number: str | None = None,
        rarity: str | None = None,
        finish: str | None = None,
        grade: int | None = None,
        source: str = "unknown",
    ) -> CardEntity | None:
        """Resolve a card to canonical entity."""

        # Filter for English cards only
        if not self._is_english_card(name, set_info):
            logger.debug("Non-English card filtered out", name=name, set_info=set_info)
            return None

        # Normalize inputs
        name_norm = self._normalize_name(name)
        set_code = self._extract_set_code(set_info) if set_info else None
        number_norm = self._normalize_number(number) if number else None
        rarity_norm = self._normalize_rarity(rarity) if rarity else None
        finish_norm = self._normalize_finish(finish) if finish else "Regular"

        # Validate required fields
        if not name_norm or not set_code or not number_norm:
            logger.warning(
                "Missing required fields for entity resolution",
                name=name_norm,
                set_code=set_code,
                number=number_norm,
                source=source,
            )
            return None

        # Calculate confidence score
        confidence = self._calculate_confidence(name, set_info, number, rarity)

        if confidence < self.confidence_threshold:
            logger.warning(
                "Low confidence entity match",
                confidence=confidence,
                threshold=self.confidence_threshold,
                name=name,
                source=source,
            )
            return None

        # Generate canonical SKU
        sku_parts = [
            set_code,
            number_norm,
            name_norm.replace(" ", "_"),
            rarity_norm or "Unknown",
        ]

        if finish_norm != "Regular":
            sku_parts.append(finish_norm.replace(" ", "_"))

        if grade:
            sku_parts.append(f"PSA{grade}")

        canonical_sku = "_".join(sku_parts)

        entity = CardEntity(
            canonical_sku=canonical_sku,
            set_code=set_code,
            card_number=number_norm,
            name_normalized=name_norm,
            rarity=rarity_norm or "Unknown",
            finish=finish_norm,
            grade=grade,
            language="EN",
            confidence=confidence,
        )

        logger.info("Entity resolved", sku=canonical_sku, confidence=confidence, source=source)
        return entity

    def _is_english_card(self, name: str, set_info: str | None) -> bool:
        """Check if card is English language."""
        # Filter out Japanese characters
        japanese_pattern = r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]'
        if re.search(japanese_pattern, name):
            return False

        if set_info and re.search(japanese_pattern, set_info):
            return False

        # Filter out known non-English indicators
        non_english_indicators = [
            "japanese", "jp", "日本語", "korean", "kr", "chinese", "cn",
            "français", "deutsch", "español", "italiano", "português",
        ]

        text_to_check = f"{name} {set_info or ''}".lower()
        for indicator in non_english_indicators:
            if indicator in text_to_check:
                return False

        return True

    def _normalize_name(self, name: str) -> str:
        """Normalize card name."""
        # Remove extra whitespace and special characters
        normalized = re.sub(r'\s+', ' ', name.strip())

        # Remove common prefixes/suffixes that cause confusion
        normalized = re.sub(r'\s*\(.*?\)\s*', '', normalized)  # Remove parentheses
        normalized = re.sub(r'\s*-\s*.*$', '', normalized)     # Remove dash suffixes

        # Standardize Pokemon name formatting
        normalized = re.sub(r'\bex\b', 'ex', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bEX\b', 'ex', normalized)
        normalized = re.sub(r'\bGX\b', 'GX', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bV\b', 'V', normalized)
        normalized = re.sub(r'\bVMAX\b', 'VMAX', normalized, flags=re.IGNORECASE)
        normalized = re.sub(r'\bVSTAR\b', 'VSTAR', normalized, flags=re.IGNORECASE)

        return normalized.strip()

    def _extract_set_code(self, set_info: str) -> str | None:
        """Extract set code from set information."""
        if not set_info:
            return None

        # Common set code patterns
        patterns = [
            r'\b([A-Z]{2,4}\d{1,3}[a-z]?)\b',  # SV4, PAL, etc.
            r'\b(Base Set|Jungle|Fossil|Team Rocket)\b',  # Classic sets
            r'\b([A-Z]{2,3})\b',  # Short codes like XY, SM
        ]

        for pattern in patterns:
            match = re.search(pattern, set_info, re.IGNORECASE)
            if match:
                return match.group(1).upper()

        # Fallback: first word if it looks like a code
        words = set_info.split()
        if words and len(words[0]) <= 6 and any(c.isdigit() for c in words[0]):
            return words[0].upper()

        return None

    def _normalize_number(self, number: str) -> str | None:
        """Normalize card number."""
        if not number:
            return None

        # Extract number from string (handle formats like "025/165", "25", "H25")
        match = re.search(r'([A-Z]?\d+)', number.upper())
        if match:
            return match.group(1)

        return None

    def _normalize_rarity(self, rarity: str) -> str | None:
        """Normalize rarity string."""
        if not rarity:
            return None

        rarity_lower = rarity.lower().strip()

        # Direct mapping
        for key, value in self.RARITY_MAPPINGS.items():
            if key in rarity_lower:
                return value

        # Fuzzy matching for close matches
        matches = process.extract(rarity_lower, list(self.RARITY_MAPPINGS.keys()), limit=1)
        if matches and matches[0][1] > 80:
            return self.RARITY_MAPPINGS[matches[0][0]]

        return rarity.title()  # Fallback to title case

    def _normalize_finish(self, finish: str) -> str:
        """Normalize finish type."""
        if not finish:
            return "Regular"

        finish_lower = finish.lower().strip()

        # Direct mapping
        for key, value in self.FINISH_MAPPINGS.items():
            if key in finish_lower:
                return value

        # Fuzzy matching
        matches = process.extract(finish_lower, list(self.FINISH_MAPPINGS.keys()), limit=1)
        if matches and matches[0][1] > 80:
            return self.FINISH_MAPPINGS[matches[0][0]]

        return finish.title()  # Fallback

    def _calculate_confidence(
        self,
        name: str,
        set_info: str | None,
        number: str | None,
        rarity: str | None,
    ) -> float:
        """Calculate confidence score for entity resolution."""
        confidence = 100.0

        # Penalize missing information
        if not set_info:
            confidence -= 20
        if not number:
            confidence -= 15
        if not rarity:
            confidence -= 10

        # Penalize ambiguous names
        if len(name.split()) < 2:
            confidence -= 10

        # Penalize suspicious patterns
        suspicious_patterns = [
            r'\?',           # Question marks
            r'unknown',      # Unknown fields
            r'error',        # Error indicators
            r'n/a',          # N/A values
        ]

        text_to_check = f"{name} {set_info or ''} {number or ''} {rarity or ''}".lower()
        for pattern in suspicious_patterns:
            if re.search(pattern, text_to_check):
                confidence -= 15

        return max(0.0, confidence)

    def batch_resolve(self, cards: list[dict]) -> list[CardEntity | None]:
        """Resolve multiple cards in batch."""
        entities = []

        for card_data in cards:
            entity = self.resolve_card(
                name=card_data.get("name", ""),
                set_info=card_data.get("set"),
                number=card_data.get("number"),
                rarity=card_data.get("rarity"),
                finish=card_data.get("finish"),
                grade=card_data.get("grade"),
                source=card_data.get("source", "batch"),
            )
            entities.append(entity)

        resolved_count = sum(1 for e in entities if e is not None)
        logger.info("Batch entity resolution completed", total=len(cards), resolved=resolved_count)

        return entities

    def find_duplicates(self, entities: list[CardEntity]) -> list[list[CardEntity]]:
        """Find duplicate entities that should be merged."""
        duplicates = []
        seen = set()

        for entity in entities:
            if entity.canonical_sku in seen:
                continue

            matches = [e for e in entities if e.canonical_sku == entity.canonical_sku]
            if len(matches) > 1:
                duplicates.append(matches)
                seen.add(entity.canonical_sku)

        return duplicates
