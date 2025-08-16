"""PriceCharting API MCP server."""

from datetime import datetime
from typing import Any

import httpx
import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class PriceData(BaseModel):
    """Price data model."""
    product_name: str
    loose_price: float | None
    cib_price: float | None  # Complete in Box
    new_price: float | None
    graded_price: float | None
    date: datetime
    volume: int | None


class PriceChartingClient:
    """PriceCharting API client."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://www.pricecharting.com/api"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def search_products(self, query: str, console: str = "pokemon") -> list[dict[str, Any]]:
        """Search for products."""
        params = {
            "t": "search",
            "q": query,
            "console": console,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/product",
                    headers=self.headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                logger.info("PriceCharting search completed", query=query, count=len(data.get("products", [])))
                return data.get("products", [])

            except httpx.HTTPError as e:
                logger.error("PriceCharting API request failed", error=str(e))
                raise

    async def get_price_history(self, product_id: str) -> list[PriceData]:
        """Get price history for a product."""
        params = {
            "t": "history",
            "id": product_id,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/product",
                    headers=self.headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                history = []
                for entry in data.get("history", []):
                    history.append(PriceData(
                        product_name=data.get("product_name", "Unknown"),
                        loose_price=entry.get("loose_price"),
                        cib_price=entry.get("cib_price"),
                        new_price=entry.get("new_price"),
                        graded_price=entry.get("graded_price"),
                        date=datetime.fromisoformat(entry["date"]),
                        volume=entry.get("volume"),
                    ))

                logger.info("Price history retrieved", product_id=product_id, count=len(history))
                return history

            except httpx.HTTPError as e:
                logger.error("PriceCharting API request failed", error=str(e))
                raise


# MCP Tool Functions
async def search_pokemon_prices(query: str) -> list[dict[str, Any]]:
    """Search for Pokemon card prices on PriceCharting."""
    # TODO: This will need actual PriceCharting API key
    logger.info("PriceCharting search requested", query=query)

    return [
        {
            "id": "example_123",
            "product_name": f"Mock price data for: {query}",
            "loose_price": 15.99,
            "graded_price": 89.99,
            "date": datetime.now().isoformat(),
            "note": "MOCK DATA - Need PriceCharting API key",
        },
    ]


async def get_price_history_data(product_id: str) -> list[dict[str, Any]]:
    """Get historical price data for a product."""
    # TODO: This will need actual PriceCharting API key
    logger.info("PriceCharting history requested", product_id=product_id)

    return [
        {
            "date": "2024-01-01",
            "loose_price": 12.99,
            "graded_price": 85.00,
            "volume": 45,
            "note": "MOCK DATA - Need PriceCharting API key",
        },
    ]
