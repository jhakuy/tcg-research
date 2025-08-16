"""PSA API MCP server."""

from typing import Any

import httpx
import structlog
from pydantic import BaseModel

logger = structlog.get_logger()


class PSAPopulationData(BaseModel):
    """PSA population data model."""
    cert_number: str | None
    card_name: str
    set_name: str
    year: int | None
    grade: int
    population: int
    population_higher: int
    last_updated: str


class PSAClient:
    """PSA API client."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key
        self.base_url = "https://api.psacard.com/publicapi/v1"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def search_population(
        self,
        card_name: str,
        set_name: str | None = None,
        year: int | None = None,
    ) -> list[PSAPopulationData]:
        """Search PSA population data."""
        params = {
            "CardName": card_name,
        }

        if set_name:
            params["SetName"] = set_name
        if year:
            params["Year"] = year

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/PopulationData",
                    headers=self.headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                populations = []
                for entry in data.get("PSAPopulationData", []):
                    populations.append(PSAPopulationData(
                        cert_number=entry.get("CertNumber"),
                        card_name=entry["CardName"],
                        set_name=entry["SetName"],
                        year=entry.get("Year"),
                        grade=entry["Grade"],
                        population=entry["Population"],
                        population_higher=entry["PopulationHigher"],
                        last_updated=entry["LastUpdated"],
                    ))

                logger.info("PSA population search completed", card_name=card_name, count=len(populations))
                return populations

            except httpx.HTTPError as e:
                logger.error("PSA API request failed", error=str(e))
                raise


# MCP Tool Functions
async def get_psa_population(
    card_name: str,
    set_name: str | None = None,
    year: int | None = None,
) -> list[dict[str, Any]]:
    """Get PSA population data for a card."""
    # TODO: This will need actual PSA API key
    logger.info("PSA population requested", card_name=card_name, set_name=set_name)

    return [
        {
            "card_name": card_name,
            "set_name": set_name or "Example Set",
            "grade": 10,
            "population": 1234,
            "population_higher": 0,
            "last_updated": "2024-01-15",
            "note": "MOCK DATA - Need PSA API key",
        },
        {
            "card_name": card_name,
            "set_name": set_name or "Example Set",
            "grade": 9,
            "population": 3456,
            "population_higher": 1234,
            "last_updated": "2024-01-15",
            "note": "MOCK DATA - Need PSA API key",
        },
    ]


async def get_psa_cert_lookup(cert_number: str) -> dict[str, Any]:
    """Look up PSA certificate details."""
    # TODO: This will need actual PSA API key
    logger.info("PSA cert lookup requested", cert_number=cert_number)

    return {
        "cert_number": cert_number,
        "card_name": "Example Card",
        "set_name": "Example Set",
        "grade": 10,
        "date_graded": "2024-01-01",
        "note": "MOCK DATA - Need PSA API key",
    }
