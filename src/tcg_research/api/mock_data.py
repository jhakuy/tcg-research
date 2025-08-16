"""Mock data for testing the TCG analysis system."""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

# Mock card data
MOCK_CARDS = [
    {
        "id": 1,
        "name": "Charizard VMAX (Champion's Path)",
        "set_code": "CP",
        "rarity": "Secret Rare",
        "current_price": 350.00,
        "recommendation": "BUY",
        "predicted_return_3m": 15.5,
        "confidence": 0.87,
        "risk_level": "MEDIUM",
        "rationale": "Strong demand from collectors, limited print run, popular Pokemon. Price has stabilized after initial drop."
    },
    {
        "id": 2, 
        "name": "Pikachu VMAX (Vivid Voltage)",
        "set_code": "VIV",
        "rarity": "Rainbow Rare",
        "current_price": 125.00,
        "recommendation": "WATCH",
        "predicted_return_3m": 5.2,
        "confidence": 0.72,
        "risk_level": "LOW",
        "rationale": "Steady popularity, good liquidity. Waiting for clearer trend direction before strong buy signal."
    },
    {
        "id": 3,
        "name": "Umbreon VMAX (Evolving Skies)",
        "set_code": "EVS", 
        "rarity": "Alternate Art",
        "current_price": 280.00,
        "recommendation": "BUY",
        "predicted_return_3m": 22.3,
        "confidence": 0.91,
        "risk_level": "MEDIUM",
        "rationale": "Extremely popular card with strong artwork. Recent dip provides good entry point. High PSA 10 population pressure."
    },
    {
        "id": 4,
        "name": "Rayquaza VMAX (Evolving Skies)",
        "set_code": "EVS",
        "rarity": "Rainbow Rare", 
        "current_price": 95.00,
        "recommendation": "AVOID",
        "predicted_return_3m": -8.7,
        "confidence": 0.79,
        "risk_level": "HIGH",
        "rationale": "Oversupplied market, declining interest. Better alternatives available in same price range."
    },
    {
        "id": 5,
        "name": "Mew VMAX (Fusion Strike)",
        "set_code": "FST",
        "rarity": "Secret Rare",
        "current_price": 45.00,
        "recommendation": "BUY", 
        "predicted_return_3m": 18.9,
        "confidence": 0.84,
        "risk_level": "LOW",
        "rationale": "Undervalued compared to similar cards. Strong tournament play history, good artwork appeal."
    },
    {
        "id": 6,
        "name": "Leafeon VMAX (Evolving Skies)",
        "set_code": "EVS",
        "rarity": "Alternate Art",
        "current_price": 180.00,
        "recommendation": "WATCH",
        "predicted_return_3m": 3.1,
        "confidence": 0.65,
        "risk_level": "MEDIUM", 
        "rationale": "Nice artwork but lower demand than other Eeveelutions. Market seems fairly priced currently."
    },
    {
        "id": 7,
        "name": "Gengar VMAX (Fusion Strike)",
        "set_code": "FST",
        "rarity": "Rainbow Rare",
        "current_price": 65.00,
        "recommendation": "BUY",
        "predicted_return_3m": 12.4,
        "confidence": 0.76,
        "risk_level": "LOW",
        "rationale": "Popular Pokemon with good competitive usage. Recent price consolidation suggests upward movement."
    }
]

def generate_mock_recommendations() -> List[Dict[str, Any]]:
    """Generate mock recommendations with realistic data."""
    recommendations = []
    
    for card in MOCK_CARDS:
        # Add some randomization to make it feel more realistic
        price_variance = random.uniform(0.95, 1.05)
        return_variance = random.uniform(0.9, 1.1)
        confidence_variance = random.uniform(0.95, 1.0)
        
        rec = {
            "card_id": card["id"],
            "card_name": card["name"],
            "recommendation": card["recommendation"],
            "predicted_return_3m": round(card["predicted_return_3m"] * return_variance, 1),
            "confidence": round(card["confidence"] * confidence_variance, 2),
            "risk_level": card["risk_level"],
            "rationale": card["rationale"],
            "price_target_low": round(card["current_price"] * price_variance * 0.95, 2) if card["recommendation"] == "BUY" else None,
            "price_target_high": round(card["current_price"] * price_variance * 1.15, 2) if card["recommendation"] == "BUY" else None,
            "prediction_date": (datetime.utcnow() - timedelta(hours=random.randint(1, 24))).isoformat()
        }
        recommendations.append(rec)
    
    # Sort by recommendation priority and confidence
    priority_order = {"BUY": 0, "WATCH": 1, "AVOID": 2}
    recommendations.sort(key=lambda x: (priority_order.get(x["recommendation"], 3), -x["confidence"]))
    
    return recommendations

def generate_mock_cards() -> List[Dict[str, Any]]:
    """Generate mock card data."""
    cards = []
    
    for card in MOCK_CARDS:
        mock_card = {
            "id": card["id"],
            "canonical_sku": f"{card['set_code']}-{card['id']:03d}",
            "set_code": card["set_code"],
            "card_number": f"{card['id']:03d}",
            "name_normalized": card["name"],
            "rarity": card["rarity"],
            "finish": "Holo",
            "language": "English"
        }
        cards.append(mock_card)
    
    return cards