"""Tests for the analytics endpoints (counts + per-user scoping)."""

TICKETS_URL = "/api/v1/tickets/"

NEW_TICKET = {
    "title": "Cannot log in to my account",
    "description": "I have been unable to log in since yesterday evening and need help.",
}


async def test_overview_counts_reflect_created_tickets(client, auth_headers):
    for _ in range(3):
        await client.post(TICKETS_URL, data=NEW_TICKET, headers=auth_headers)

    resp = await client.get("/api/v1/analytics/overview", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_tickets"] == 3
    # All three enriched as medium/neutral by the AI mock:
    assert body["tickets_by_priority"]["medium"] == 3
    assert body["tickets_by_sentiment"]["neutral"] == 3


async def test_analytics_scoped_per_user(client, auth_headers):
    await client.post(TICKETS_URL, data=NEW_TICKET, headers=auth_headers)

    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "carol",
            "email": "carol@example.com",
            "password": "Secure123",
            "confirm_password": "Secure123",
        },
    )
    carol = {"Authorization": f"Bearer {resp.json()['access_token']}"}
    overview = await client.get("/api/v1/analytics/overview", headers=carol)
    assert overview.json()["total_tickets"] == 0
