import pytest
from httpx import AsyncClient

# This marks all tests in this file to run asynchronously
pytestmark = pytest.mark.asyncio

async def test_register_tenant_success(client: AsyncClient):
    """
    Test the happy path: A new tenant registers successfully
    and receives their one-time API key.
    """
    payload = {
        "name": "Test Prediction Markets",
        "email": "admin@testmarkets.com",
        "password": "super_secure_password"
    }
    
    response = await client.post("/tenants/register", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    
    assert "tenant_id" in data
    assert "api_key" in data
    assert data["api_key"].startswith("snt_")

async def test_register_tenant_duplicate_email(client: AsyncClient):
    """
    Test the database constraint: We cannot register two tenants
    with the exact same email address.
    """
    payload = {
        "name": "First Tenant",
        "email": "duplicate@test.com",
        "password": "password123"
    }
    
    #Register the first tenant (Should succeed)
    res1 = await client.post("/tenants/register", json=payload)
    assert res1.status_code == 201
    
    # Attempt to register again with the same payload (Should fail)
    res2 = await client.post("/tenants/register", json=payload)
    assert res2.status_code == 409
    assert res2.json()["detail"] == "Email already registered"

async def test_login_tenant_success(client: AsyncClient):
    """
    Test the login flow: A registered tenant can log in
    and receive a valid session JWT.
    """
    # Register a tenant to exist in the database
    register_payload = {
        "name": "Login Test Tenant",
        "email": "login@test.com",
        "password": "login_password"
    }
    await client.post("/tenants/register", json=register_payload)
    
    # Attempt to log in with the correct credentials
    login_payload = {
        "email": "login@test.com",
        "password": "login_password"
    }
    response = await client.post("/tenants/login", json=login_payload)
    
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

async def test_login_tenant_invalid_credentials(client: AsyncClient):
    """
    Test the security boundary: A bad password must be rejected.
    """
    # Register a tenant
    await client.post("/tenants/register", json={
        "name": "Secure Tenant",
        "email": "secure@test.com",
        "password": "correct_password"
    })
    
    # Attempt login with a completely wrong password
    response = await client.post("/tenants/login", json={
        "email": "secure@test.com",
        "password": "wrong_password"
    })
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"