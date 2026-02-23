import os
from datetime import datetime, timedelta, timezone
from jose import jwt

from fastapi import Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from passlib.context import CryptContext
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from app.config import settings
import uuid
from app.database import AsyncSessionLocal
from app.models import APIKey, Tenant
from app.dependencies import get_db

jwt_bearer_scheme = HTTPBearer(auto_error=False)
api_key_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)

SECRET_KEY = settings.platform_secret_key
ALGORITHM = settings.platform_algorithm
EXPIRE_MINUTES = settings.platform_admin_jwt_expire_minutes

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

async def verify_api_key(
    api_key: str = Security(api_key_header_scheme),
    db: AsyncSession = Depends(get_db)
) -> Tenant:
    """
    Validates the API key and returns the associated Tenant object.
    Fails with 401 if the key is missing, invalid, or revoked.
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    prefix = api_key[:12]

    stmt = (
        select(APIKey)
        .join(APIKey.tenant)
        .where(
            APIKey.key_prefix == prefix,
            APIKey.is_active == True,
            Tenant.status == 'ACTIVE'
        )
    )
    result = await db.execute(stmt)
    potential_keys = result.scalars().all()

    for db_key in potential_keys:
        if pwd_context.verify(api_key, str(db_key.key_hash)):
            tenant = await db.get(Tenant, db_key.tenant_id)
            return tenant

    raise HTTPException(status_code=401, detail="Invalid or revoked API Key")

def create_access_token(data: dict) -> str:
    """
    Creates a JWT valid for a specific duration.
    The 'data' dict will contain the tenant_id as the 'sub' (subject).
    """
    to_encode = data.copy()
    
    expire = datetime.now(timezone.utc) + timedelta(minutes=EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def verify_jwt(
    token: HTTPAuthorizationCredentials = Security(jwt_bearer_scheme),
    db: AsyncSession = Depends(get_db)
) -> Tenant:
    """
    Validates the session JWT and returns the associated Tenant object.
    Used for administrative routes (like generating API keys).
    """
    if not token:
        raise HTTPException(status_code=401, detail="Missing authorization token")

    try:
        payload = jwt.decode(token.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        
        tenant_id = payload.get("sub")
        if not isinstance(tenant_id, str):
            raise HTTPException(status_code=401, detail="Invalid token payload")
        
        try:
            tenant_uuid = uuid.UUID(tenant_id)
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid tenant ID format")
            
    except JWTError:
        raise HTTPException(status_code=401, detail="Token is invalid or expired")

    tenant = await db.get(Tenant, tenant_uuid)
    if not tenant or str(tenant.status) != 'ACTIVE':
        raise HTTPException(status_code=403, detail="Tenant account suspended or deleted")

    return tenant