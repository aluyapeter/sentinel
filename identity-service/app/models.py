import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    email = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    date_of_birth = Column(Date, nullable=True)
    country_code = Column(String(2), nullable=True) # ISO 3166-1 alpha-2 e.g., 'NG', 'US'
    kyc_status = Column(String(50), nullable=False, default='UNVERIFIED')
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('tenant_id', 'email', name='uix_tenant_email'),
    )

    kyc_documents = relationship("KYCDocument", back_populates="user", cascade="all, delete-orphan")


class KYCDocument(Base):
    __tablename__ = 'kyc_documents'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    
    document_type = Column(String(50), nullable=False)  #'PASSPORT', 'DRIVERS_LICENSE'
    document_url = Column(String(1024), nullable=False) # In a real app, an S3/Blob storage URL
    document_ref = Column(String(255), nullable=True) # Provider reference ID
    status = Column(String(50), nullable=False, default='PENDING') # PENDING, APPROVED, REJECTED
    decision = Column(String(50), nullable=True)
    rejection_reason = Column(String(500), nullable=True)
    
    submitted_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=True)
    
    user = relationship("User", back_populates="kyc_documents")