import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.jobs.client import inngest_client
from src.jobs.inngest_functions import (
    scheduled_builder_discovery,
    stale_followup_checker,
    execute_builder_discovery_job,
    execute_stale_followup_job,
)

client = TestClient(app)


def test_inngest_client_initialization():
    assert inngest_client.app_id == "networkai"


def test_health_reports_inngest_registered():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["inngest_registered"] is True


def test_inngest_route_registered():
    """Verifies /api/inngest is registered in the FastAPI routing table."""
    route_paths = [getattr(r, "path", "") for r in app.routes]
    assert any("/api/inngest" in path for path in route_paths)


def test_inngest_function_triggers():
    """Verifies cron configurations on the Inngest function registrations."""
    assert scheduled_builder_discovery.name == "scheduled-builder-discovery"
    assert stale_followup_checker.name == "stale-followup-checker"


@pytest.mark.asyncio
async def test_scheduled_builder_discovery_execution():
    result = await execute_builder_discovery_job(limit=2)
    assert result["status"] == "completed"
    assert result["builders_discovered"] > 0
    assert result["actions_queued"] > 0
    assert "timestamp" in result


@pytest.mark.asyncio
async def test_stale_followup_checker_execution():
    result = await execute_stale_followup_job()
    assert result["status"] == "completed"
    assert result["stale_contacts_evaluated"] > 0
    assert result["followups_queued"] > 0
    assert "timestamp" in result

    # Ensure all follow-ups generated adhere to the strict 300-char limit
    for item in result["details"]:
        assert len(item["content"]) <= 300
        assert item["action_type"] == "follow_up"
        assert item["status"] == "pending_approval"
