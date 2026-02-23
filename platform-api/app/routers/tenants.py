import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext

from app.models import Tenant, APIKey
from app.schemas import TenantRegister, TenantResponse, TenantLogin, TokenResponse
from app.dependencies import get_db
from app.security import create_access_token

from app.security import verify_jwt

router = APIRouter(prefix="/tenants", tags=["Tenants"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

@router.post("/register", response_model=TenantResponse, status_code=201)
async def register_tenant(tenant_in: TenantRegister, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Tenant).where(Tenant.email == tenant_in.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed_pwd = pwd_context.hash(tenant_in.password)
    new_tenant = Tenant(
        name=tenant_in.name,
        email=tenant_in.email,
        hashed_password=hashed_pwd
    )
    db.add(new_tenant)
    await db.flush()

    raw_key = "snt_" + secrets.token_hex(32)
    key_prefix = raw_key[:12]
    key_hash = pwd_context.hash(raw_key)

    new_api_key = APIKey(
        tenant_id=new_tenant.id,
        key_prefix=key_prefix,
        key_hash=key_hash,
        name="Default"
    )
    db.add(new_api_key)
    
    await db.commit()

    return TenantResponse(
        tenant_id=new_tenant.id, #type: ignore
        api_key=raw_key,
        message="Copy your API key now. It cannot be displayed again."
    )

@router.post("/login", response_model=TokenResponse, status_code=200)
async def login_tenant(credentials: TenantLogin, db: AsyncSession = Depends(get_db)):
    stmt = select(Tenant).where(Tenant.email == credentials.email)
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if not tenant or not pwd_context.verify(credentials.password, str(tenant.hashed_password)):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if str(tenant.status) != 'ACTIVE':
        raise HTTPException(status_code=403, detail="Tenant account is suspended")

    access_token = create_access_token(
        data={"sub": str(tenant.id)}
    )

    return TokenResponse(access_token=access_token)

@router.get("/me", status_code=200)
async def get_current_tenant(current_tenant: Tenant = Depends(verify_jwt)):
    """
    Returns the details of the tenant making the request.
    This route is strictly protected by the verify_api_key dependency.
    """
    return {
        "tenant_id": current_tenant.id,
        "name": current_tenant.name,
        "email": current_tenant.email,
        "plan": current_tenant.plan,
        "status": current_tenant.status
    }