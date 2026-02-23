from fastapi import APIRouter, Depends
from app.models import Tenant
from app.security import verify_api_key

# We use the /internal prefix to denote that this should not be exposed to the public internet
router = APIRouter(prefix="/internal", tags=["Internal"])

@router.get("/verify-key", status_code=200)
async def resolve_api_key(current_tenant: Tenant = Depends(verify_api_key)):
    """
    Internal endpoint called by the Identity Service and Trade Engine.
    Validates the X-API-Key header and returns the active tenant's ID.
    """
    return {
        "tenant_name": current_tenant.name,
        "tenant_email": current_tenant.email,
        "tenant_id": str(current_tenant.id),
        "status": current_tenant.status,
        "plan": current_tenant.plan
    }