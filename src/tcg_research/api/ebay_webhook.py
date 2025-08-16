"""eBay Marketplace Account Deletion webhook endpoint."""

import os
import hashlib
from fastapi import APIRouter, Request, Response, HTTPException
import structlog

logger = structlog.get_logger()
router = APIRouter()

# Your verification token from Railway
VERIFICATION_TOKEN = "1clgipOm5SHhQ0y22ttJmq_C065LGclOdmDCjRvdlEoMpCwo"
# Your exact endpoint URL (must match what you entered in eBay portal)
ENDPOINT_URL = "https://tcg-research-production.up.railway.app/webhooks/ebay/account-deletion"

@router.get("/webhooks/ebay/account-deletion")
async def ebay_verification_challenge(request: Request):
    """Handle eBay's verification challenge for account deletion webhook."""
    
    challenge_code = request.query_params.get("challenge_code")
    
    if not challenge_code:
        logger.error("No challenge_code in request", query_params=dict(request.query_params))
        return Response(status_code=400, content="Missing challenge_code parameter")
    
    # Calculate the challenge response
    # eBay expects: SHA-256 of (challengeCode + verificationToken + endpointURL)
    concatenated = challenge_code + VERIFICATION_TOKEN + ENDPOINT_URL
    challenge_response = hashlib.sha256(concatenated.encode('utf-8')).hexdigest()
    
    logger.info("eBay verification challenge received", 
                challenge_code=challenge_code,
                endpoint_url=ENDPOINT_URL,
                verification_token_length=len(VERIFICATION_TOKEN))
    
    # Return JSON response as eBay expects
    return {"challengeResponse": challenge_response}

@router.post("/webhooks/ebay/account-deletion")
async def ebay_account_deletion_notification(request: Request):
    """Handle actual account deletion notifications from eBay."""
    
    try:
        # Get the notification data
        notification_data = await request.json()
        
        logger.info("eBay account deletion notification received", 
                   notification=notification_data)
        
        # For your Pokemon card system, you don't actually need to process these
        # Just acknowledge receipt so eBay doesn't keep retrying
        
        # You could store/log these if needed, but for card price data it's not necessary
        
        # Return success status as eBay expects
        return Response(status_code=200, content="Notification received")
        
    except Exception as e:
        logger.error("Error processing eBay notification", error=str(e))
        # Still return success to avoid eBay retries
        return Response(status_code=200, content="Notification received")

@router.get("/webhooks/ebay/test")
async def test_webhook_endpoint():
    """Test endpoint to verify the webhook is working."""
    return {
        "status": "Webhook endpoint is active",
        "endpoint_url": ENDPOINT_URL,
        "verification_token_set": bool(VERIFICATION_TOKEN),
        "verification_token_length": len(VERIFICATION_TOKEN),
        "ready_for_ebay_verification": True
    }