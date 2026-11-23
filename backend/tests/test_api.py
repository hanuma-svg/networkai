import math
import pytest
from fastapi.testclient import TestClient
from src.main import app
from src.services.embeddings import l2_normalize, generate_embedding
from src.models.schemas import ActionQueueModel

client = TestClient(app)


# ==============================================================================
# 1. Health & Status
# ==============================================================================

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "networkai-backend"


# ==============================================================================
# 2. CORS Headers Validation
# Verifies localhost:3000, *.vercel.app, and chrome-extension://*
# ==============================================================================

def test_cors_localhost():
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_vercel_domain():
    response = client.options(
        "/health",
        headers={
            "Origin": "https://networkai-preview-abc.vercel.app",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response.headers.get("access-control-allow-origin") == "https://networkai-preview-abc.vercel.app"


def test_cors_chrome_extension():
    response = client.options(
        "/health",
        headers={
            "Origin": "chrome-extension://abcdefghijklmnop",
            "Access-Control-Request-Method": "POST"
        }
    )
    assert response.headers.get("access-control-allow-origin") == "chrome-extension://abcdefghijklmnop"


# ==============================================================================
# 3. 768-dim L2 Normalization & Embeddings
# ==============================================================================

def test_l2_normalization_math():
    raw_vector = [3.0, 4.0]
    normalized = l2_normalize(raw_vector)
    assert len(normalized) == 2
    assert math.isclose(normalized[0], 0.6, abs_tol=1e-5)
    assert math.isclose(normalized[1], 0.8, abs_tol=1e-5)
    norm = math.sqrt(sum(x * x for x in normalized))
    assert math.isclose(norm, 1.0, abs_tol=1e-5)


def test_gemini_768_dim_embedding():
    text = "AI Agent Builder building LangGraph workflows"
    embedding = generate_embedding(text)
    assert len(embedding) == 768
    # Norm must equal 1.0 (unit vector for pgvector cosine operations)
    norm = math.sqrt(sum(x * x for x in embedding))
    assert math.isclose(norm, 1.0, abs_tol=1e-4)


# ==============================================================================
# 4. Schema Constraint: Connection note strictly <= 300 chars
# ==============================================================================

def test_connection_note_schema_limit():
    # Valid note <= 300 chars
    valid_note = ActionQueueModel(
        action_type="connection_note",
        content="Hi there, would love to connect and exchange ideas on AI agents!"
    )
    assert len(valid_note.content) <= 300

    # Invalid note > 300 chars must raise validation error
    with pytest.raises(ValueError):
        ActionQueueModel(
            action_type="connection_note",
            content="A" * 301
        )

    # Draft comments can exceed 300 characters
    long_comment = ActionQueueModel(
        action_type="draft_comment",
        content="B" * 500
    )
    assert len(long_comment.content) == 500


# ==============================================================================
# 5. LangGraph Workflow Endpoint: POST /api/analyze-profile
# ==============================================================================

def test_analyze_profile_workflow():
    payload = {
        "full_name": "Sarah Connor",
        "headline": "Lead AI Architect at Skynet Systems",
        "company": "Skynet Systems",
        "location": "San Francisco, CA",
        "linkedin_url": "https://linkedin.com/in/sarah-connor-ai",
        "recent_post_text": "Evaluating LangGraph vs custom state machines for agent reliability.",
    }
    response = client.post("/api/analyze-profile", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["contact_id"] is not None

    profiler = data["profiler_output"]
    assert 0 <= profiler["relevance_score"] <= 100
    assert len(profiler["shared_hooks"]) > 0
    assert profiler["recommended_action"] in ["draft_comment", "connection_note", "follow_up"]

    action_item = data["action_item"]
    assert action_item["status"] == "pending_approval"
    assert len(action_item["content"]) > 0
    if action_item["action_type"] == "connection_note":
        assert len(action_item["content"]) <= 300


# ==============================================================================
# 6. Autonomous Discovery Endpoint: POST /api/discover
# ==============================================================================

def test_discover_builders():
    payload = {
        "topic": "agentic-ai",
        "keywords": ["LangGraph", "FastAPI"],
        "limit": 3
    }
    response = client.post("/api/discover", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] == "success"
    assert data["builders_found"] >= 1
    assert len(data["builders"]) >= 1
    assert len(data["queued_actions"]) == len(data["builders"])

    # Ensure queued actions have pending_approval status and adhere to char limits
    for action in data["queued_actions"]:
        assert action["status"] == "pending_approval"
        if action["action_type"] == "connection_note":
            assert len(action["content"]) <= 300


# ==============================================================================
# 7. Official LinkedIn Publisher Endpoint: POST /api/publish-post
# ==============================================================================

def test_publish_post():
    payload = {
        "commentary": "Announcing our new open-source agent workflow for automated networking!",
        "author_urn": "urn:li:person:mock-author-123",
        "visibility": "PUBLIC"
    }
    response = client.post("/api/publish-post", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["status"] in ["simulated", "success"]
    assert data["post_urn"].startswith("urn:li:share:")
    assert data["lifecycle_state"] == "PUBLISHED"


# ==============================================================================
# 8. Queue Management & Memory Node: GET /api/queue & POST /api/queue/{id}/approve
# ==============================================================================

def test_queue_approval_triggers_memory_node():
    # 1. Create an action item in the queue via analyze-profile
    analyze_resp = client.post("/api/analyze-profile", json={
        "full_name": "Jordan Lee",
        "headline": "VP of Engineering at FutureAI",
        "company": "FutureAI",
        "linkedin_url": "https://linkedin.com/in/jordan-lee-ai",
    })
    assert analyze_resp.status_code == 200
    action_item = analyze_resp.json()["action_item"]
    action_id = action_item["id"]

    # 2. Verify it shows up in GET /api/queue
    queue_resp = client.get("/api/queue?status=pending_approval")
    assert queue_resp.status_code == 200
    queue_items = queue_resp.json()
    assert any(item["id"] == action_id for item in queue_items)

    # 3. Approve the action item
    approve_resp = client.post(f"/api/queue/{action_id}/approve")
    assert approve_resp.status_code == 200
    approve_data = approve_resp.json()

    assert approve_data["status"] == "approved"
    assert approve_data["action_id"] == action_id
    assert approve_data["memory_updated"] is True
    assert approve_data["interaction_recorded"] is True
