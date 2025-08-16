"""TCGdx API MCP server."""

from typing import Any

import httpx
import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class TCGCard(BaseModel):
    """TCG card model from TCGdx."""
    id: str
    name: str
    supertype: str
    subtypes: list[str]
    level: str | None
    hp: int | None
    types: list[str]
    rarity: str
    set_id: str
    set_name: str
    number: str
    artist: str | None
    image_url: str | None
    tcgplayer_id: int | None


class TCGSet(BaseModel):
    """TCG set model."""
    id: str
    name: str
    series: str
    total: int
    release_date: str
    symbol_url: str | None
    logo_url: str | None


class TCGdxClient:
    """TCGdx API client (free, no auth required)."""

    def __init__(self) -> None:
        self.base_url = "https://api.tcgdx.net/v2/en"
        self.headers = {
            "Content-Type": "application/json",
        }

    async def search_cards(
        self,
        name: str | None = None,
        set_id: str | None = None,
        number: str | None = None,
    ) -> list[TCGCard]:
        """Search for cards."""
        url = f"{self.base_url}/cards"
        params = {}

        if name:
            params["q"] = f"name:{name}"
        if set_id:
            params["q"] = params.get("q", "") + f" set.id:{set_id}"
        if number:
            params["q"] = params.get("q", "") + f" number:{number}"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    url,
                    headers=self.headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                cards = []
                for card_data in data.get("data", []):
                    try:
                        card = self._parse_card(card_data)
                        cards.append(card)
                    except Exception as e:
                        logger.warning("Failed to parse card", card_id=card_data.get("id"), error=str(e))

                logger.info("TCGdx card search completed", name=name, count=len(cards))
                return cards

            except httpx.HTTPError as e:
                logger.error("TCGdx API request failed", error=str(e))
                raise

    async def get_sets(self) -> list[TCGSet]:
        """Get all Pokemon sets."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/sets",
                    headers=self.headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                sets = []
                for set_data in data.get("data", []):
                    try:
                        set_obj = self._parse_set(set_data)
                        sets.append(set_obj)
                    except Exception as e:
                        logger.warning("Failed to parse set", set_id=set_data.get("id"), error=str(e))

                logger.info("TCGdx sets retrieved", count=len(sets))
                return sets

            except httpx.HTTPError as e:
                logger.error("TCGdx API request failed", error=str(e))
                raise

    def _parse_card(self, card_data: dict[str, Any]) -> TCGCard:
        """Parse card data from TCGdx."""
        return TCGCard(
            id=card_data["id"],
            name=card_data["name"],
            supertype=card_data["supertype"],
            subtypes=card_data.get("subtypes", []),
            level=card_data.get("level"),
            hp=card_data.get("hp"),
            types=card_data.get("types", []),
            rarity=card_data.get("rarity", "Unknown"),
            set_id=card_data["set"]["id"],
            set_name=card_data["set"]["name"],
            number=card_data["number"],
            artist=card_data.get("artist"),
            image_url=card_data.get("images", {}).get("large"),
            tcgplayer_id=card_data.get("tcgplayer", {}).get("id"),
        )

    def _parse_set(self, set_data: dict[str, Any]) -> TCGSet:
        """Parse set data from TCGdx."""
        return TCGSet(
            id=set_data["id"],
            name=set_data["name"],
            series=set_data["series"],
            total=set_data["total"],
            release_date=set_data["releaseDate"],
            symbol_url=set_data.get("images", {}).get("symbol"),
            logo_url=set_data.get("images", {}).get("logo"),
        )


# MCP Tool Functions
async def search_pokemon_cards_tcgdx(
    name: str | None = None,
    set_id: str | None = None,
    number: str | None = None,
) -> list[dict[str, Any]]:
    """Search for Pokemon cards using TCGdx API."""
    client = TCGdxClient()

    try:
        cards = await client.search_cards(name=name, set_id=set_id, number=number)
        return [card.model_dump() for card in cards]
    except Exception as e:
        logger.error("TCGdx search failed", error=str(e))
        return []


async def get_pokemon_sets() -> list[dict[str, Any]]:
    """Get all Pokemon sets from TCGdx."""
    client = TCGdxClient()

    try:
        sets = await client.get_sets()
        return [set_obj.model_dump() for set_obj in sets]
    except Exception as e:
        logger.error("TCGdx sets retrieval failed", error=str(e))
        return []


async def normalize_card_sku(
    card_name: str,
    set_name: str | None = None,
    number: str | None = None,
) -> dict[str, Any] | None:
    """Normalize card SKU using TCGdx data."""
    cards = await search_pokemon_cards_tcgdx(name=card_name, set_id=set_name, number=number)

    if not cards:
        return None

    # Return the first match with normalized SKU format
    card = cards[0]
    return {
        "canonical_sku": f"{card['set_id']}_{card['number']}_{card['name'].replace(' ', '_')}_{card['rarity']}",
        "set_code": card['set_id'],
        "card_number": card['number'],
        "name_normalized": card['name'],
        "rarity": card['rarity'],
        "supertype": card['supertype'],
        "subtypes": card['subtypes'],
        "release_date": card.get('release_date'),
    }
