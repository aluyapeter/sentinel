import uuid
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.future import select
from app.config import settings

engine = create_async_engine(settings.identity_database_url, echo=True) #type: ignore
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class TenantScopedSession:
    """
    A strict wrapper around the database session.
    It guarantees that all queries and inserts are isolated to the authenticated tenant.
    """
    def __init__(self, session: AsyncSession, tenant_id: str):
        self.session = session
        self.tenant_id = uuid.UUID(str(tenant_id))

    def add(self, instance):
        if hasattr(instance, 'tenant_id'):
            instance.tenant_id = self.tenant_id
        self.session.add(instance)

    async def commit(self):
        await self.session.commit()

    async def refresh(self, instance):
        await self.session.refresh(instance)
    
    async def get_user_by_email(self, email: str):

        from app.models import User
        stmt = select(User).where(
            User.tenant_id == self.tenant_id,
            User.email == email
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: str):
        """Fetches a user by ID, strictly scoped to the current tenant."""
        from app.models import User 
        
        stmt = select(User).where(
            User.tenant_id == self.tenant_id,
            User.id == uuid.UUID(str(user_id))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_document_by_id(self, document_id: str):
        """Fetches a KYC document by ID, strictly scoped to the current tenant."""
        from app.models import KYCDocument
        
        stmt = select(KYCDocument).where(
            # We enforce tenant isolation through the document's relationship to the user
            KYCDocument.id == uuid.UUID(str(document_id)),
            KYCDocument.user.has(tenant_id=self.tenant_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()