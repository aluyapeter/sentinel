import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
from sqlalchemy.pool import NullPool

from app.main import app
from app.database import Base
from app.dependencies import get_db
from app.security import pwd_context

#a separate database URL specifically for testing.
TEST_DATABASE_URL = settings.platform_database_url.replace("/platform_db", "/platform_test_db")

engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    poolclass=NullPool
)
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_database():
    """Creates the tables before tests run, and drops them after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session():
    """Provides a fresh database session for a single test."""
    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def client(db_session: AsyncSession):
    """
    Overrides the get_db dependency to use the test database,
    and yields an AsyncClient to make mock HTTP requests.
    """
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest.fixture
def test_password():
    return "secure_test_password_123"

@pytest.fixture
def hashed_test_password(test_password):
    return pwd_context.hash(test_password)