from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_db
from app.database import TenantScopedSession

router = APIRouter(prefix="/internal", tags=["Internal"])

@router.get("/verify-user/{tenant_id}/{user_id}", status_code=status.HTTP_200_OK)
async def verify_user_for_trading(
    tenant_id: str,
    user_id: str,
    session: AsyncSession = Depends(get_db)
):
    """
    Internal endpoint used by the Trade Engine (Phase 4).
    Verifies that a user exists within a specific tenant and returns their KYC status.
    """
    # We wrap the session to ensure the Trade Engine can't accidentally cross tenant boundaries
    db = TenantScopedSession(session, tenant_id)
    
    user = await db.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="User not found in this tenant environment"
        )
        
    return {
        "user_id": str(user.id),
        "tenant_id": str(user.tenant_id),
        "kyc_status": user.kyc_status
    }