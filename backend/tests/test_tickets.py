"""Tests for ticket CRUD, AI enrichment, and IDOR (owner scoping)."""

TICKETS_URL = "/api/v1/tickets/"

NEW_TICKET = {
    "title": "Cannot log in to my account",
    "description": "I have been unable to log in since yesterday evening and need help.",
}


async def _register(client, username, email):
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": username,
            "email": email,
            "password": "Secure123",
            "confirm_password": "Secure123",
        },
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


async def test_create_ticket_runs_ai_enrichment(client, auth_headers):
    resp = await client.post(TICKETS_URL, data=NEW_TICKET, headers=auth_headers)
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == NEW_TICKET["title"]
    assert body["status"] == "open"
    # These come from the mocked analyse_ticket in conftest:
    assert body["ai_summary"] == "Mocked AI summary."
    assert body["sentiment"] == "neutral"
    assert body["priority"] == "medium"
    # No file sent → no screenshot.
    assert body["screenshot_url"] is None


async def test_create_ticket_with_image_degrades_without_cloudinary(client, auth_headers):
    # Cloudinary is unconfigured in tests, so an attached image is skipped
    # gracefully — the ticket is still created, just without a screenshot URL.
    files = {"screenshot": ("shot.png", b"\x89PNG\r\n\x1a\nfakebytes", "image/png")}
    resp = await client.post(
        TICKETS_URL, data=NEW_TICKET, files=files, headers=auth_headers
    )
    assert resp.status_code == 201
    assert resp.json()["screenshot_url"] is None


async def test_list_returns_only_own_tickets(client, auth_headers):
    await client.post(TICKETS_URL, data=NEW_TICKET, headers=auth_headers)
    resp = await client.get(TICKETS_URL, headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


async def test_get_other_users_ticket_returns_404(client, auth_headers):
    created = await client.post(TICKETS_URL, data=NEW_TICKET, headers=auth_headers)
    ticket_id = created.json()["id"]

    bob = await _register(client, "bob", "bob@example.com")
    resp = await client.get(f"{TICKETS_URL}{ticket_id}", headers=bob)
    assert resp.status_code == 404  # IDOR prevention: not 403, not 200


async def test_update_ticket(client, auth_headers):
    created = await client.post(TICKETS_URL, data=NEW_TICKET, headers=auth_headers)
    ticket_id = created.json()["id"]
    resp = await client.patch(
        f"{TICKETS_URL}{ticket_id}", json={"status": "resolved"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "resolved"


async def test_update_with_no_fields_returns_422(client, auth_headers):
    created = await client.post(TICKETS_URL, data=NEW_TICKET, headers=auth_headers)
    ticket_id = created.json()["id"]
    resp = await client.patch(f"{TICKETS_URL}{ticket_id}", json={}, headers=auth_headers)
    assert resp.status_code == 422


async def test_delete_ticket(client, auth_headers):
    created = await client.post(TICKETS_URL, data=NEW_TICKET, headers=auth_headers)
    ticket_id = created.json()["id"]
    deleted = await client.delete(f"{TICKETS_URL}{ticket_id}", headers=auth_headers)
    assert deleted.status_code == 204
    follow = await client.get(f"{TICKETS_URL}{ticket_id}", headers=auth_headers)
    assert follow.status_code == 404
