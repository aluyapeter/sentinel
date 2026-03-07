import httpx
from fastapi import Security, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from app.config import settings
from app.models import User
from fastapi.security.api_key import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal, TenantScopedSession

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

security = HTTPBearer()

async def get_db():
    """
    Yields a database session for the Identity Service and ensures it is safely closed after the request completes.
    """
    async with AsyncSessionLocal() as session:
        yield session

async def get_current_tenant(api_key: str = Security(api_key_header)) -> str:
    """
    Intercepts the API key and makes a real-time network request to the 
    Platform API to verify it. Returns the tenant_id string if successful.
    """
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    # We use httpx to make an internal HTTP call over the Docker network.
    # The URL matches the container name 'platform-api' defined in docker-compose.yml.
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "http://platform-api:8000/internal/verify-key",
                headers={"X-API-Key": api_key},
                timeout=5.0
            )
        except httpx.RequestError:
            raise HTTPException(
                status_code=503, 
                detail="Platform authentication service unavailable"
            )

    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid or revoked API Key")

    # Extract and return just the tenant_id so the identity routes can use it
    tenant_data = response.json()
    return tenant_data["tenant_id"]

async def get_tenant_session(
    session: AsyncSession = Depends(get_db),
    tenant_id: str = Depends(get_current_tenant)
) -> TenantScopedSession:
    """
    This for the Identity Service gets a raw database session, asks the Platform API to validate the X-API-Key and return the tenant_id. It wraps them both together in our secure TenantScopedSession and hands it to the route.
    """
    return TenantScopedSession(session, tenant_id)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
    tenant_id: str = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db)
) -> User:
    """
    Validates an end-user's JWT and ensures it strictly belongs to the calling tenant.
    Requires BOTH the X-API-Key and the Authorization header.
    """
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.identity_secret_key, algorithms=[settings.identity_algorithm])
        
        user_id = payload.get("sub")
        token_tenant_id = payload.get("tenant_id")
        
        if user_id is None or token_tenant_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
         
        if token_tenant_id != tenant_id:
            raise HTTPException(
                status_code=403, 
                detail="Critical: Token does not belong to the authenticated tenant environment"
            )
            
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

    from app.database import TenantScopedSession
    scoped_db = TenantScopedSession(session, tenant_id)
    
    user = await scoped_db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
        
    return user