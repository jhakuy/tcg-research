"""Data ingestion pipeline for TCG market data."""

import asyncio
from datetime import datetime, timedelta
from typing import Any

import structlog
from sqlalchemy.orm import Session

from tcg_research.mcp.ebay_browse import EbayBrowseClient, search_pokemon_cards
from tcg_research.mcp.enhanced_ebay_browse import EnhancedEbayBrowseClient, search_enhanced_pokemon_cards
from tcg_research.mcp.pricecharting import PriceChartingClient, search_pokemon_prices
from tcg_research.mcp.psa_api import PSAAPIClient, get_psa_population
from tcg_research.mcp.tcgdx import search_pokemon_cards_tcgdx
from tcg_research.models.database import Card, EbayListing, PriceHistory, PSAPopulation
from tcg_research.core.entity_resolver import EntityResolver
from tcg_research.core.enhanced_entity_resolver import FilteredEntityResolver

logger = structlog.get_logger()


class DataIngestionPipeline:
    """Main data ingestion pipeline."""

    def __init__(
        self,
        db_session: Session,
        ebay_client: EbayBrowseClient | None = None,
        enhanced_ebay_client: EnhancedEbayBrowseClient | None = None,
        pricecharting_client: PriceChartingClient | None = None,
        psa_client: PSAAPIClient | None = None,
        use_enhanced_filtering: bool = True,
    ) -> None:
        self.db_session = db_session
        self.ebay_client = ebay_client
        self.enhanced_ebay_client = enhanced_ebay_client
        self.pricecharting_client = pricecharting_client
        self.psa_client = psa_client
        self.use_enhanced_filtering = use_enhanced_filtering
        
        # Use enhanced resolver if filtering is enabled
        if use_enhanced_filtering:
            self.entity_resolver = FilteredEntityResolver()
        else:
            self.entity_resolver = EntityResolver()

    async def run_daily_ingestion(self) -> dict[str, int]:
        """Run daily data ingestion."""
        logger.info("Starting daily ingestion pipeline")

        results = {
            "cards_updated": 0,
            "ebay_listings": 0,
            "price_updates": 0,
            "psa_updates": 0,
            "errors": 0,
        }

        try:
            # Get popular cards to track
            target_cards = await self._get_target_cards()
            logger.info("Target cards identified", count=len(target_cards))

            # Process each card
            for card_query in target_cards:
                try:
                    await self._process_card(card_query, results)
                except Exception as e:
                    logger.error("Card processing failed", card=card_query, error=str(e))
                    results["errors"] += 1

                # Rate limiting
                await asyncio.sleep(1)

            self.db_session.commit()
            logger.info("Daily ingestion completed", results=results)

        except Exception as e:
            logger.error("Daily ingestion failed", error=str(e))
            self.db_session.rollback()
            raise

        return results

    async def _get_target_cards(self) -> list[dict[str, str]]:
        """Get list of cards to track."""
        # For now, use a curated list of popular cards
        # TODO: Make this dynamic based on user interests and market activity

        popular_cards = [
            # Current meta cards
            {"query": "Charizard ex Paldea Evolved", "set": "PAL", "priority": "high"},
            {"query": "Miraidon ex Scarlet Violet", "set": "SVI", "priority": "high"},
            {"query": "Koraidon ex Scarlet Violet", "set": "SVI", "priority": "high"},

            # Classic valuable cards
            {"query": "Charizard Base Set", "set": "BASE", "priority": "medium"},
            {"query": "Pikachu VMAX Vivid Voltage", "set": "VIV", "priority": "medium"},

            # Recent sets
            {"query": "Paradox Rift", "set": "PAR", "priority": "low"},
            {"query": "Obsidian Flames", "set": "OBF", "priority": "low"},
        ]

        return popular_cards

    async def _process_card(self, card_query: dict[str, str], results: dict[str, int]) -> None:
        """Process a single card through the ingestion pipeline."""
        query = card_query["query"]

        logger.debug("Processing card", query=query)

        # Step 1: Get TCGdx data for normalization
        tcgdx_data = await self._get_tcgdx_data(query)
        if not tcgdx_data:
            logger.warning("No TCGdx data found", query=query)
            return

        # Step 2: Resolve to canonical entity
        entity = self.entity_resolver.resolve_card(
            name=tcgdx_data["name"],
            set_info=tcgdx_data.get("set_name"),
            number=tcgdx_data.get("number"),
            rarity=tcgdx_data.get("rarity"),
            source="tcgdx",
        )

        if not entity:
            logger.warning("Entity resolution failed", query=query)
            return

        # Step 3: Get or create card record
        card = await self._get_or_create_card(entity, tcgdx_data)

        # Step 4: Ingest from different sources
        await asyncio.gather(
            self._ingest_ebay_data(card, query, results),
            self._ingest_pricecharting_data(card, query, results),
            self._ingest_psa_data(card, results),
            return_exceptions=True,
        )

        results["cards_updated"] += 1

    async def _get_tcgdx_data(self, query: str) -> dict[str, Any] | None:
        """Get card data from TCGdx."""
        try:
            cards = await search_pokemon_cards_tcgdx(name=query)
            if cards:
                return cards[0]  # Take first match
        except Exception as e:
            logger.error("TCGdx lookup failed", query=query, error=str(e))

        return None

    async def _get_or_create_card(self, entity, tcgdx_data: dict[str, Any]) -> Card:
        """Get existing card or create new one."""
        card = self.db_session.query(Card).filter_by(
            canonical_sku=entity.canonical_sku,
        ).first()

        if not card:
            card = Card(
                canonical_sku=entity.canonical_sku,
                set_code=entity.set_code,
                card_number=entity.card_number,
                name_normalized=entity.name_normalized,
                rarity=entity.rarity,
                finish=entity.finish,
                grade=entity.grade,
                language=entity.language,

                # TCGdx metadata
                supertype=tcgdx_data.get("supertype"),
                subtypes=str(tcgdx_data.get("subtypes", [])),
                hp=tcgdx_data.get("hp"),
                types=str(tcgdx_data.get("types", [])),
                artist=tcgdx_data.get("artist"),
                image_url=tcgdx_data.get("image_url"),
                tcgplayer_id=tcgdx_data.get("tcgplayer_id"),
            )
            self.db_session.add(card)
            self.db_session.flush()
            logger.info("Created new card", sku=entity.canonical_sku)

        return card

    async def _ingest_ebay_data(self, card: Card, query: str, results: dict[str, int]) -> None:
        """Ingest eBay listing data with enhanced filtering."""
        try:
            if self.use_enhanced_filtering and self.enhanced_ebay_client:
                # Use enhanced eBay client with filtering
                filtered_listings = await self.enhanced_ebay_client.search_pokemon_cards(
                    query=query,
                    max_results=20,
                    include_entity_resolution=False  # We already have the card entity
                )
                
                high_quality_count = 0
                for filtered_item in filtered_listings:
                    # Only process high-quality listings
                    if (filtered_item.filter_quality.value in ['excellent', 'good'] and
                        filtered_item.card_type.value == 'single_card'):
                        
                        # Check if listing already exists
                        existing = self.db_session.query(EbayListing).filter_by(
                            item_id=filtered_item.item_id,
                            card_id=card.id,
                        ).first()

                        if existing:
                            # Update existing listing
                            existing.price = filtered_item.price
                            existing.is_active = True
                            existing.last_seen = datetime.utcnow()
                        else:
                            # Create new listing with filter metadata
                            listing = EbayListing(
                                card_id=card.id,
                                item_id=filtered_item.item_id,
                                title=filtered_item.title,
                                price=filtered_item.price,
                                currency=filtered_item.currency,
                                condition=filtered_item.condition,
                                listing_type=filtered_item.listing_type,
                                seller_username=filtered_item.seller_username,
                                view_item_url=filtered_item.view_item_url,
                                image_url=filtered_item.image_url,
                            )
                            self.db_session.add(listing)
                            results["ebay_listings"] += 1
                            high_quality_count += 1
                            
                        # Limit high-quality listings per card
                        if high_quality_count >= 10:
                            break
                            
                logger.info(
                    "Enhanced eBay ingestion completed",
                    card_sku=card.canonical_sku,
                    total_found=len(filtered_listings),
                    high_quality_stored=high_quality_count
                )
                
            else:
                # Fallback to basic ingestion
                listings_data = await search_pokemon_cards(query)

                for listing_data in listings_data[:10]:  # Limit to 10 listings per card
                    # Check if listing already exists
                    existing = self.db_session.query(EbayListing).filter_by(
                        item_id=listing_data["item_id"],
                        card_id=card.id,
                    ).first()

                    if existing:
                        # Update existing listing
                        existing.price = listing_data.get("price")
                        existing.is_active = True
                        existing.last_seen = datetime.utcnow()
                    else:
                        # Create new listing
                        listing = EbayListing(
                            card_id=card.id,
                            item_id=listing_data["item_id"],
                            title=listing_data["title"],
                            price=listing_data.get("price"),
                            currency=listing_data.get("currency", "USD"),
                            condition=listing_data.get("condition"),
                            listing_type=listing_data.get("listing_type"),
                            seller_username=listing_data.get("seller"),
                            view_item_url=listing_data.get("url"),
                        )
                        self.db_session.add(listing)
                        results["ebay_listings"] += 1

        except Exception as e:
            logger.error("eBay ingestion failed", card_sku=card.canonical_sku, error=str(e))

    async def _ingest_pricecharting_data(self, card: Card, query: str, results: dict[str, int]) -> None:
        """Ingest PriceCharting historical data."""
        try:
            # Use mock function for now
            price_data = await search_pokemon_prices(query)

            if price_data:
                data = price_data[0]

                # Check if we already have recent price data
                recent_price = self.db_session.query(PriceHistory).filter_by(
                    card_id=card.id,
                    source="pricecharting",
                ).order_by(PriceHistory.date.desc()).first()

                # Only add if we don't have today's data
                today = datetime.utcnow().date()
                if not recent_price or recent_price.date.date() < today:
                    price_history = PriceHistory(
                        card_id=card.id,
                        date=datetime.fromisoformat(data["date"]),
                        loose_price=data.get("loose_price"),
                        graded_price=data.get("graded_price"),
                        source="pricecharting",
                        product_id=data.get("id"),
                    )
                    self.db_session.add(price_history)
                    results["price_updates"] += 1

        except Exception as e:
            logger.error("PriceCharting ingestion failed", card_sku=card.canonical_sku, error=str(e))

    async def _ingest_psa_data(self, card: Card, results: dict[str, int]) -> None:
        """Ingest PSA population data."""
        try:
            # Use mock function for now
            psa_data = await get_psa_population(card.name_normalized)

            for grade_data in psa_data:
                grade = grade_data["grade"]

                # Check if population exists
                existing_pop = self.db_session.query(PSAPopulation).filter_by(
                    card_id=card.id,
                    grade=grade,
                ).first()

                if existing_pop:
                    # Update population
                    existing_pop.population = grade_data["population"]
                    existing_pop.population_higher = grade_data["population_higher"]
                    existing_pop.last_updated = datetime.fromisoformat(grade_data["last_updated"])
                else:
                    # Create new population record
                    psa_pop = PSAPopulation(
                        card_id=card.id,
                        grade=grade,
                        population=grade_data["population"],
                        population_higher=grade_data["population_higher"],
                        last_updated=datetime.fromisoformat(grade_data["last_updated"]),
                    )
                    self.db_session.add(psa_pop)

                results["psa_updates"] += 1

        except Exception as e:
            logger.error("PSA ingestion failed", card_sku=card.canonical_sku, error=str(e))

    async def cleanup_stale_listings(self, days_old: int = 7) -> int:
        """Mark old eBay listings as inactive."""
        cutoff_date = datetime.utcnow() - timedelta(days=days_old)

        updated = self.db_session.query(EbayListing).filter(
            EbayListing.last_seen < cutoff_date,
            EbayListing.is_active.is_(True),
        ).update({"is_active": False})

        self.db_session.commit()
        logger.info("Cleaned up stale listings", count=updated)

        return updated


class SpecificCardIngester:
    """Ingester for specific cards requested by users."""

    def __init__(self, db_session: Session) -> None:
        self.db_session = db_session
        self.entity_resolver = EntityResolver()

    async def ingest_card_by_name(self, card_name: str, set_name: str | None = None) -> Card | None:
        """Ingest a specific card by name."""
        logger.info("Ingesting specific card", name=card_name, set_name=set_name)

        # Get TCGdx data
        tcgdx_cards = await search_pokemon_cards_tcgdx(name=card_name)

        if not tcgdx_cards:
            logger.warning("Card not found in TCGdx", name=card_name)
            return None

        # Filter by set if specified
        if set_name:
            tcgdx_cards = [c for c in tcgdx_cards if set_name.lower() in c.get("set_name", "").lower()]

        if not tcgdx_cards:
            logger.warning("Card not found in specified set", name=card_name, set_name=set_name)
            return None

        tcgdx_data = tcgdx_cards[0]

        # Resolve entity
        entity = self.entity_resolver.resolve_card(
            name=tcgdx_data["name"],
            set_info=tcgdx_data.get("set_name"),
            number=tcgdx_data.get("number"),
            rarity=tcgdx_data.get("rarity"),
            source="user_request",
        )

        if not entity:
            logger.warning("Entity resolution failed", name=card_name)
            return None

        # Create or get card
        card = self.db_session.query(Card).filter_by(
            canonical_sku=entity.canonical_sku,
        ).first()

        if not card:
            card = Card(
                canonical_sku=entity.canonical_sku,
                set_code=entity.set_code,
                card_number=entity.card_number,
                name_normalized=entity.name_normalized,
                rarity=entity.rarity,
                finish=entity.finish,
                language=entity.language,

                supertype=tcgdx_data.get("supertype"),
                subtypes=str(tcgdx_data.get("subtypes", [])),
                hp=tcgdx_data.get("hp"),
                types=str(tcgdx_data.get("types", [])),
                artist=tcgdx_data.get("artist"),
                image_url=tcgdx_data.get("image_url"),
                tcgplayer_id=tcgdx_data.get("tcgplayer_id"),
            )
            self.db_session.add(card)
            self.db_session.commit()

            logger.info("Card ingested successfully", sku=entity.canonical_sku)
        else:
            logger.info("Card already exists", sku=entity.canonical_sku)

        return card
