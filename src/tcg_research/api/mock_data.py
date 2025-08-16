"""Mock data for testing the TCG analysis system."""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import random

# ULTRA CONSERVATIVE Mock card data - Very strict BUY criteria
MOCK_CARDS = [
    {
        "id": 1,
        "name": "Charizard VMAX (Champion's Path)",
        "set_code": "CP",
        "rarity": "Secret Rare",
        "current_price": 350.00,
        "recommendation": "BUY",  # Only exceptional opportunity
        "predicted_return_3m": 28.5,  # Must be 20%+ for BUY
        "confidence": 0.94,  # Must be 90%+ confidence
        "risk_level": "MEDIUM",
        "rationale": "STRONG BUY: 28.5% predicted return with 94% confidence. Exceptional price momentum. Excellent liquidity. High price stability. All conservative criteria met."
    },
    {
        "id": 2, 
        "name": "Pikachu VMAX (Vivid Voltage)",
        "set_code": "VIV",
        "rarity": "Rainbow Rare",
        "current_price": 125.00,
        "recommendation": "WATCH",  # Good but not exceptional
        "predicted_return_3m": 12.2,  # Under 20% threshold
        "confidence": 0.82,  # Under 90% confidence
        "risk_level": "MEDIUM",
        "rationale": "WATCH: 12.2% predicted return with 82% confidence. Return below 20% BUY threshold. Confidence below 90% BUY threshold. Monitor for improvement."
    },
    {
        "id": 3,
        "name": "Umbreon VMAX (Evolving Skies)",
        "set_code": "EVS", 
        "rarity": "Alternate Art",
        "current_price": 280.00,
        "recommendation": "BUY",  # Meets strict criteria
        "predicted_return_3m": 31.8,  # High return
        "confidence": 0.93,  # High confidence
        "risk_level": "MEDIUM",
        "rationale": "STRONG BUY: 31.8% predicted return with 93% confidence. Strong price momentum. Good liquidity. Stable pricing. All conservative criteria met."
    },
    {
        "id": 4,
        "name": "Rayquaza VMAX (Evolving Skies)",
        "set_code": "EVS",
        "rarity": "Rainbow Rare", 
        "current_price": 95.00,
        "recommendation": "AVOID",
        "predicted_return_3m": -12.7,
        "confidence": 0.79,
        "risk_level": "HIGH",
        "rationale": "AVOID: -12.7% predicted return with 79% confidence. Negative return expected. Low prediction confidence. Does not meet investment criteria."
    },
    {
        "id": 5,
        "name": "Mew VMAX (Fusion Strike)",
        "set_code": "FST",
        "rarity": "Secret Rare",
        "current_price": 45.00,
        "recommendation": "WATCH", # Conservative downgrade - insufficient confidence
        "predicted_return_3m": 16.2,  # Good return but under 20%
        "confidence": 0.84,  # Under 90% confidence
        "risk_level": "MEDIUM",
        "rationale": "WATCH: 16.2% predicted return with 84% confidence. Return below 20% BUY threshold. Confidence below 90% BUY threshold. Monitor for improvement."
    },
    {
        "id": 6,
        "name": "Leafeon VMAX (Evolving Skies)",
        "set_code": "EVS",
        "rarity": "Alternate Art",
        "current_price": 180.00,
        "recommendation": "WATCH",
        "predicted_return_3m": 8.1,
        "confidence": 0.71,
        "risk_level": "MEDIUM", 
        "rationale": "WATCH: 8.1% predicted return with 71% confidence. Return below 20% BUY threshold. Confidence below 90% BUY threshold. Monitor for improvement."
    },
    {
        "id": 7,
        "name": "Gengar VMAX (Fusion Strike)",
        "set_code": "FST",
        "rarity": "Rainbow Rare",
        "current_price": 65.00,
        "recommendation": "WATCH", # Conservative downgrade
        "predicted_return_3m": 14.4,  # Under 20% threshold
        "confidence": 0.76,  # Under 90% confidence
        "risk_level": "MEDIUM",
        "rationale": "WATCH: 14.4% predicted return with 76% confidence. Return below 20% BUY threshold. Confidence below 90% BUY threshold. Monitor for improvement."
    },
    {
        "id": 8,
        "name": "Lugia VSTAR (Silver Tempest)",
        "set_code": "SIT",
        "rarity": "Secret Rare",
        "current_price": 85.00,
        "recommendation": "AVOID",
        "predicted_return_3m": 3.2,
        "confidence": 0.68,
        "risk_level": "HIGH",
        "rationale": "AVOID: 3.2% predicted return with 68% confidence. Low return potential. Low prediction confidence. Weak momentum. Does not meet investment criteria."
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