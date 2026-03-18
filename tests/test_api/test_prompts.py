import pytest
from datetime import datetime, timezone

from prompt_review.models import Developer


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_submit_prompt_unauthorized(client):
    resp = await client.post("/api/v1/prompts", json={
        "session_id": "test-session",
        "prompt_text": "hello",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }, headers={"Authorization": "Bearer invalid-key"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_submit_prompt_success(client, db_session):
    # Create a developer
    dev = Developer(username="testdev", display_name="Test Dev", api_key="test-api-key-123")
    db_session.add(dev)
    await db_session.commit()

    resp = await client.post("/api/v1/prompts", json={
        "session_id": "sess-001",
        "prompt_text": "Fix the login bug",
        "source_tool": "claude_code",
        "project_name": "my-app",
        "ticket_number": "PROJ-42",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }, headers={"Authorization": "Bearer test-api-key-123"})

    assert resp.status_code == 201
    data = resp.json()
    assert data["prompt_text"] == "Fix the login bug"
    assert data["project_name"] == "my-app"
    assert data["ticket_number"] == "PROJ-42"
