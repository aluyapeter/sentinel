from pydantic import BaseModel, EmailStr
from uuid import UUID

class TenantRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class TenantResponse(BaseModel):
    tenant_id: UUID
    api_key: str
    message: str

class TenantLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class APIKeyCreateResponse(BaseModel):
    key_id: str
    raw_key: str
    message: str