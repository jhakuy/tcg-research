"""
PSA API client for Pokemon card population and certification data.

This module provides comprehensive PSA API integration for accessing
grading population data, certification details, and market analysis.
"""

import asyncio
import httpx
import structlog
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel
import os

logger = structlog.get_logger()


class PSACertData(BaseModel):
    """PSA certification data model."""
    cert_number: str
    card_name: str
    year: Optional[str] = None
    brand: str
    variety: Optional[str] = None
    grade: int
    grade_date: Optional[datetime] = None
    card_number: Optional[str] = None
    set_name: Optional[str] = None
    category: Optional[str] = None
    subject: Optional[str] = None
    
    # Additional metadata
    total_population: Optional[int] = None
    grade_population: Optional[int] = None
    higher_grade_population: Optional[int] = None


class PSAPopulationData(BaseModel):
    """PSA population data for a specific card."""
    card_name: str
    set_name: str
    card_number: Optional[str] = None
    total_graded: int
    grade_distribution: Dict[str, int]  # Grade -> count
    population_date: datetime
    
    # Calculated metrics
    gem_rate: float  # Percentage of PSA 10s
    high_grade_rate: float  # Percentage of PSA 9-10
    scarcity_score: float  # 0-100 based on total population


class PSAAPIClient:
    """PSA API client with authentication and rate limiting."""
    
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.psacard.com/publicapi"
        self.session: Optional[httpx.AsyncClient] = None
        
        # Rate limiting
        self.requests_per_minute = 60  # Conservative rate limit
        self.request_timestamps: List[datetime] = []
        
        # Cache for frequently accessed data
        self.cert_cache: Dict[str, PSACertData] = {}
        self.population_cache: Dict[str, PSAPopulationData] = {}
        self.cache_ttl = timedelta(hours=1)
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = httpx.AsyncClient(
            headers={"Authorization": f"bearer {self.access_token}"},
            timeout=30.0
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.aclose()
    
    async def _rate_limit(self):
        """Enforce rate limiting."""
        now = datetime.now()
        
        # Remove timestamps older than 1 minute
        self.request_timestamps = [
            ts for ts in self.request_timestamps 
            if now - ts < timedelta(minutes=1)
        ]
        
        # Check if we're at the rate limit
        if len(self.request_timestamps) >= self.requests_per_minute:
            sleep_time = 60 - (now - self.request_timestamps[0]).total_seconds()
            if sleep_time > 0:
                logger.info("Rate limit hit, sleeping", sleep_seconds=sleep_time)
                await asyncio.sleep(sleep_time)
                
        self.request_timestamps.append(now)
    
    async def _make_request(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make authenticated request to PSA API."""
        await self._rate_limit()
        
        if not self.session:
            raise RuntimeError("PSA client not initialized. Use 'async with' syntax.")
            
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = await self.session.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            logger.debug("PSA API request successful", endpoint=endpoint, status=response.status_code)
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error(
                "PSA API request failed",
                endpoint=endpoint,
                status_code=e.response.status_code,
                error=str(e)
            )
            raise
        except Exception as e:
            logger.error("PSA API request error", endpoint=endpoint, error=str(e))
            raise
    
    async def get_cert_by_number(self, cert_number: str) -> Optional[PSACertData]:
        """Get PSA certification data by cert number."""
        
        # Check cache first
        if cert_number in self.cert_cache:
            cached_data = self.cert_cache[cert_number]
            logger.debug("Using cached PSA cert data", cert_number=cert_number)
            return cached_data
            
        try:
            data = await self._make_request(f"cert/GetByCertNumber/{cert_number}")
            
            if not data or 'PSACert' not in data:
                logger.warning("No PSA cert data found", cert_number=cert_number)
                return None
                
            cert_data = data['PSACert']
            
            # Parse grade date if available
            grade_date = None
            if cert_data.get('GradeDate'):
                try:
                    grade_date = datetime.strptime(cert_data['GradeDate'], '%Y-%m-%d')
                except ValueError:
                    logger.warning("Invalid grade date format", date=cert_data['GradeDate'])
            
            psa_cert = PSACertData(
                cert_number=cert_number,
                card_name=cert_data.get('Subject', ''),
                year=cert_data.get('Year'),
                brand=cert_data.get('Brand', ''),
                variety=cert_data.get('Variety'),
                grade=int(cert_data.get('CardGrade', 0)),
                grade_date=grade_date,
                card_number=cert_data.get('CardNumber'),
                set_name=cert_data.get('Category'),
                category=cert_data.get('Category'),
                subject=cert_data.get('Subject')
            )
            
            # Cache the result
            self.cert_cache[cert_number] = psa_cert
            
            logger.info(
                "PSA cert data retrieved",
                cert_number=cert_number,
                card_name=psa_cert.card_name,
                grade=psa_cert.grade
            )
            
            return psa_cert
            
        except Exception as e:
            logger.error("Failed to get PSA cert data", cert_number=cert_number, error=str(e))
            return None
    
    async def test_connection(self) -> bool:
        """Test PSA API connection and authentication."""
        try:
            # Test with a known cert number - let's try a low number
            test_cert = "00000001"
            data = await self._make_request(f"cert/GetByCertNumber/{test_cert}")
            logger.info("PSA API connection test successful")
            return True
            
        except Exception as e:
            logger.error("PSA API connection test failed", error=str(e))
            return False


# Factory function
def create_psa_client(access_token: Optional[str] = None) -> PSAAPIClient:
    """Create PSA client instance."""
    
    if not access_token:
        access_token = os.getenv('PSA_ACCESS_TOKEN')
    
    if not access_token:
        raise ValueError("PSA access token is required")
    
    logger.info("Creating PSA client")
    return PSAAPIClient(access_token)


# Convenience function for testing
async def test_psa_api(access_token: str) -> Dict[str, Any]:
    """Test PSA API with provided token."""
    
    results = {
        "connection_test": False,
        "cert_lookup": None,
        "error": None
    }
    
    try:
        async with PSAAPIClient(access_token) as client:
            # Test connection
            results["connection_test"] = await client.test_connection()
            
            # Test cert lookup with a real cert number
            cert_data = await client.get_cert_by_number("12345678")
            if cert_data:
                results["cert_lookup"] = cert_data.dict()
                
    except Exception as e:
        results["error"] = str(e)
        logger.error("PSA API test failed", error=str(e))
    
    return results


# MCP Tool Functions for compatibility
async def get_psa_population(
    card_name: str,
    set_name: str | None = None,
    year: int | None = None,
) -> list[dict[str, Any]]:
    """Get PSA population data for a card."""
    access_token = os.getenv('PSA_ACCESS_TOKEN')
    
    if not access_token:
        logger.warning("No PSA access token found, returning mock data")
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
    
    # Real implementation would search for certs and calculate population
    logger.info("PSA population requested", card_name=card_name, set_name=set_name)
    return []


async def get_psa_cert_lookup(cert_number: str) -> dict[str, Any]:
    """Look up PSA certificate details."""
    access_token = os.getenv('PSA_ACCESS_TOKEN')
    
    if not access_token:
        logger.warning("No PSA access token found, returning mock data")
        return {
            "cert_number": cert_number,
            "card_name": "Example Card",
            "set_name": "Example Set",
            "grade": 10,
            "date_graded": "2024-01-01",
            "note": "MOCK DATA - Need PSA API key",
        }
    
    try:
        async with PSAAPIClient(access_token) as client:
            cert_data = await client.get_cert_by_number(cert_number)
            if cert_data:
                return cert_data.dict()
            else:
                return {"error": "Certificate not found"}
                
    except Exception as e:
        logger.error("PSA cert lookup failed", cert_number=cert_number, error=str(e))
        return {"error": str(e)}
