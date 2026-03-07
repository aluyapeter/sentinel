import hmac
import hashlib
import json
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.database import TenantScopedSession
from app.config import settings

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

@router.post("/kyc-result", status_code=status.HTTP_200_OK)
async def kyc_webhook_receiver(
    request: Request, 
    session: AsyncSession = Depends(get_db)
):
    """
    Receives an automated decision from the 3rd-party KYC provider.
    Strictly verifies the HMAC signature to prevent tampering.
    """
    raw_body = await request.body()
    signature_header = request.headers.get("X-Webhook-Signature")
    
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing HMAC signature")

    secret_bytes = settings.identity_secret_key.encode('utf-8')
    expected_signature = hmac.new(secret_bytes, raw_body, hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_signature, signature_header):
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")
    
    try:
        payload = json.loads(raw_body)
        tenant_id = payload["tenant_id"]
        user_id = payload["user_id"]
        document_id = payload["document_id"]
        decision_status = payload["status"] # APPROVED or REJECTED
        decision_reason = payload.get("decision")
    except KeyError:
        raise HTTPException(status_code=422, detail="Malformed webhook payload")

    db = TenantScopedSession(session, tenant_id)
    
    user = await db.get_user_by_id(user_id)
    document = await db.get_document_by_id(document_id)

    if not user or not document:
        raise HTTPException(status_code=404, detail="User or Document not found")

    # Update Document
    document.status = decision_status
    document.decision = decision_reason
    document.decided_at = datetime.now(timezone.utc) #type: ignore
    db.add(document) 

    if decision_status == "APPROVED":
        user.kyc_status = "VERIFIED" # type: ignore
    else:
        user.kyc_status = "REJECTED" # type: ignore
    db.add(user)

    await db.commit()
    
    return {"message": "Webhook processed successfully"}