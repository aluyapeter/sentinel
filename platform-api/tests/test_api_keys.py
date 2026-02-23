import pytest
import secrets
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio

async def get_auth_headers(client: AsyncClient) -> dict:
    """
    Helper function to register a test tenant, log them in, 
    and return the required JWT Authorization header.
    """
    unique_email = f"test_{secrets.token_hex(4)}@domain.com"
    
    reg_res = await client.post("/tenants/register", json={
        "name": "API Key Test Tenant",
        "email": unique_email,
        "password": "secure_password"
    })

    assert reg_res.status_code == 201, f"Registration failed: {reg_res.text}"
    
    login_res = await client.post("/tenants/login", json={
        "email": unique_email,
        "password": "secure_password"
    })
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

async def test_generate_api_key_success(client: AsyncClient):
    """Test that a tenant with a valid JWT can generate a new API key."""
    headers = await get_auth_headers(client)
    
    response = await client.post("/tenants/api-keys/?name=ProductionKey", headers=headers)
    
    assert response.status_code == 201
    data = response.json()
    assert "key_id" in data
    assert "raw_key" in data
    assert data["raw_key"].startswith("snt_")

async def test_generate_api_key_unauthorised(client: AsyncClient):
    """Test the JWT bouncer: An unauthenticated request must be rejected."""
    response = await client.post("/tenants/api-keys/?name=HackerKey")
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authorization token"

async def test_list_and_revoke_api_keys(client: AsyncClient):
    """
    Test the full lifecycle: Generating a key, verifying it appears in the list,
    revoking it, and verifying it is removed from the active list.
    """
    headers = await get_auth_headers(client)
    
    # Generate a key to revoke
    gen_res = await client.post("/tenants/api-keys/?name=KeyToRevoke", headers=headers)
    key_id = gen_res.json()["key_id"]
    
    # List keys and ensure it is there
    list_res = await client.get("/tenants/api-keys/", headers=headers)
    assert list_res.status_code == 200
    keys = list_res.json()
    assert len(keys) == 2 # 1 default key from registration + 1 we just generated
    
    # Revoke the specific key we just created
    del_res = await client.delete(f"/tenants/api-keys/{key_id}", headers=headers)
    assert del_res.status_code == 204
    
    # List keys again to ensure the revoked key is gone
    list_res_2 = await client.get("/tenants/api-keys/", headers=headers)
    keys_after_delete = list_res_2.json()
    assert len(keys_after_delete) == 1 # Only the default key should remain