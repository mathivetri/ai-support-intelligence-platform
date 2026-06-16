"""Tests for the authentication endpoints (register, login, refresh)."""

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"

VALID_USER = {
    "username": "alice",
    "email": "alice@example.com",
    "password": "Secure123",
    "confirm_password": "Secure123",
}


async def test_register_success(client):
    resp = await client.post(REGISTER_URL, json=VALID_USER)
    assert resp.status_code == 201
    body = resp.json()
    assert body["access_token"] and body["refresh_token"]
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "alice@example.com"
    assert "hashed_password" not in body["user"]


async def test_register_duplicate_email(client):
    await client.post(REGISTER_URL, json=VALID_USER)
    resp = await client.post(REGISTER_URL, json={**VALID_USER, "username": "alice2"})
    assert resp.status_code == 409


async def test_register_weak_password(client):
    resp = await client.post(
        REGISTER_URL,
        json={**VALID_USER, "password": "weak", "confirm_password": "weak"},
    )
    assert resp.status_code == 422


async def test_login_success(client):
    await client.post(REGISTER_URL, json=VALID_USER)
    resp = await client.post(
        LOGIN_URL, json={"email": "alice@example.com", "password": "Secure123"}
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_login_wrong_password(client):
    await client.post(REGISTER_URL, json=VALID_USER)
    resp = await client.post(
        LOGIN_URL, json={"email": "alice@example.com", "password": "WrongPass1"}
    )
    assert resp.status_code == 401


async def test_login_unregistered_email(client):
    resp = await client.post(
        LOGIN_URL, json={"email": "ghost@example.com", "password": "Secure123"}
    )
    assert resp.status_code == 401


async def test_protected_route_requires_token(client):
    resp = await client.get("/api/v1/tickets/")
    assert resp.status_code == 401


async def test_refresh_returns_new_access_token(client):
    reg = await client.post(REGISTER_URL, json=VALID_USER)
    refresh_token = reg.json()["refresh_token"]
    resp = await client.post(REFRESH_URL, json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    assert resp.json()["access_token"]


async def test_refresh_rejects_an_access_token(client):
    # An access token must NOT be usable as a refresh token (type guard).
    reg = await client.post(REGISTER_URL, json=VALID_USER)
    access_token = reg.json()["access_token"]
    resp = await client.post(REFRESH_URL, json={"refresh_token": access_token})
    assert resp.status_code == 401


async def test_refresh_rejects_garbage(client):
    resp = await client.post(REFRESH_URL, json={"refresh_token": "not.a.token"})
    assert resp.status_code == 401
