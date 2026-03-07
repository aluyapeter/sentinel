import asyncio
import logging
import sys
import hmac
import hashlib
import json
import httpx
from app.config import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

async def simulate_kyc_processing(tenant_id: str, user_id: str, document_id: str):
    """
    Simulates a 3rd-party provider analysing a document and sending a signed webhook.
    """
    logger.info(f"Background Task Started: Processing KYC for Document {document_id}")
    await asyncio.sleep(5) 
    
    payload = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "document_id": document_id,
        "status": "APPROVED",
        "decision": "Facial geometry match confirmed"
    }
    payload_bytes = json.dumps(payload).encode('utf-8')
    
    secret_bytes = settings.identity_secret_key.encode('utf-8')
    signature = hmac.new(secret_bytes, payload_bytes, hashlib.sha256).hexdigest()

    logger.info(f"Background Task: Firing HMAC signed webhook for Document {document_id}")
    async with httpx.AsyncClient() as client:
        try:
            # We hit localhost because the task is running inside the same container as the API
            response = await client.post(
                "http://127.0.0.0:8001/webhooks/kyc-result",
                content=payload_bytes,
                headers={"X-Webhook-Signature": signature},
                timeout=5.0
            )
            logger.info(f"Webhook response status: {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to deliver webhook: {e}")