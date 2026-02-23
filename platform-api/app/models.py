import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.database import Base

class Tenant(Base):
    __tablename__ = 'tenants'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    hashed_password = Column(String(255), nullable=False)
    plan = Column(String(50), nullable=False, default='FREE')
    status = Column(String(50), nullable=False, default='ACTIVE', index=True)
    webhook_secret = Column(String(255))
    max_users = Column(Integer, nullable=False, default=100)
    max_markets = Column(Integer, nullable=False, default=10)
    
    # We use timezone-aware datetimes. This is critical for global financial apps.
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True)) # For soft deletes

    # Relationships allow us to access tenant.api_keys easily in Python
    api_keys = relationship("APIKey", back_populates="tenant", cascade="all, delete-orphan")
    usage_logs = relationship("UsageLog", back_populates="tenant", cascade="all, delete-orphan")


class APIKey(Base):
    __tablename__ = 'api_keys'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    
    # We only store the prefix for display (e.g., snt_a3f9...), NEVER the full key[cite: 226].
    key_prefix = Column(String(20), nullable=False)
    # The actual key is hashed using bcrypt, just like a password[cite: 226].
    key_hash = Column(String(255), nullable=False, unique=True, index=True)
    
    name = Column(String(100))
    is_active = Column(Boolean, nullable=False, default=True)
    last_used_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    revoked_at = Column(DateTime(timezone=True))

    tenant = relationship("Tenant", back_populates="api_keys")


class UsageLog(Base):
    __tablename__ = 'usage_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey('tenants.id', ondelete='CASCADE'), nullable=False, index=True)
    endpoint = Column(String(255), nullable=False)
    status_code = Column(SmallInteger, nullable=False)
    response_ms = Column(Integer)
    logged_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    tenant = relationship("Tenant", back_populates="usage_logs")