from pydantic import BaseModel, EmailStr, Field
from datetime import date, datetime
from typing import Optional
import uuid

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Must be at least 8 characters long")
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    country_code: Optional[str] = Field(None, max_length=2, description="ISO 3166-1 alpha-2 e.g., NG")

class UserResponse(BaseModel):
    id: uuid.UUID
    email: str
    phone: Optional[str]
    kyc_status: str
    created_at: datetime

    class Config:
        from_attributes = True

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class KYCDocumentCreate(BaseModel):
    document_type: str = Field(..., description="e.g., PASSPORT, DRIVERS_LICENSE, NATIONAL_ID")
    document_url: str = Field(..., description="The secure URL where the file is stored (e.g., AWS S3)")
    document_ref: Optional[str] = Field(None, description="Optional third-party provider reference ID")

class KYCDocumentResponse(BaseModel):
    id: uuid.UUID
    document_type: str
    status: str
    submitted_at: datetime

    class Config:
        from_attributes = True