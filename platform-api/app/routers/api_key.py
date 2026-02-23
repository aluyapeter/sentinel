import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import AsyncSessionLocal
from app.models import APIKey, Tenant
from app.security import verify_jwt, pwd_context
from app.schemas import APIKeyCreateResponse
from app.dependencies import get_db

router = APIRouter(prefix="/tenants/api-keys", tags=["API Keys"])

@router.post("/", response_model=APIKeyCreateResponse, status_code=201)
async def generate_api_key(
    name: str = "Default", 
    db: AsyncSession = Depends(get_db),
    current_tenant: Tenant = Depends(verify_jwt)):
    """
    Generates a new API key for the authenticated tenant.
    Requires a valid session JWT.
    """
    stmt = select(APIKey).where(APIKey.tenant_id == current_tenant.id, APIKey.is_active == True)
    result = await db.execute(stmt)
    active_keys = result.scalars().all()
    
    if len(active_keys) >= 5:
        raise HTTPException(status_code=400, detail="Maximum number of active API keys reached")

    raw_key = "snt_" + secrets.token_hex(32)
    key_prefix = raw_key[:12]
    key_hash = pwd_context.hash(raw_key)

    new_api_key = APIKey(
        tenant_id=current_tenant.id,
        key_prefix=key_prefix,
        key_hash=key_hash,
        name=name
    )
    
    db.add(new_api_key)
    await db.commit()
    await db.refresh(new_api_key)

    return APIKeyCreateResponse(
        key_id=str(new_api_key.id),
        raw_key=raw_key,
        message="Copy your API key now. It cannot be displayed again."
    )

@router.get("/", status_code=200)
async def list_api_keys(
    db: AsyncSession = Depends(get_db),
    current_tenant: Tenant = Depends(verify_jwt)
):
    """
    Lists all active API keys for the authenticated tenant.
    Requires a valid session JWT.
    """
    stmt = select(APIKey).where(
        APIKey.tenant_id == current_tenant.id, 
        APIKey.is_active == True
    )
    result = await db.execute(stmt)
    keys = result.scalars().all()

    # return the api-key prefix
    return [
        {
            "id": str(k.id),
            "name": k.name,
            "prefix": k.key_prefix,
            "created_at": k.created_at
        }
        for k in keys
    ]

@router.delete("/{key_id}", status_code=204)
async def revoke_api_key(
    key_id: str,
    db: AsyncSession = Depends(get_db),
    current_tenant: Tenant = Depends(verify_jwt)
):
    """
    Revokes an existing API key. 
    Requires a valid session JWT.
    """
    key_to_revoke = await db.get(APIKey, key_id)
    
    # ensure the key belongs to the tenant making the request
    if not key_to_revoke or str(key_to_revoke.tenant_id) != str(current_tenant.id):
        raise HTTPException(status_code=404, detail="API Key not found")

    setattr(key_to_revoke, "is_active", False)
    await db.commit()
    return None