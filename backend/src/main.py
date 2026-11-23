from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
import inngest.fast_api

from src.config import settings
from src.models.schemas import (
    ProfileAnalyzeRequest,
    ProfileAnalyzeResponse,
    DiscoveryRequest,
    DiscoveryResponse,
    PublishPostRequest,
    PublishPostResponse,
    ActionQueueModel,
    QueueActionApprovalResponse,
)
from src.graph.workflow import execute_profile_analysis, execute_memory_update
from src.services.discovery import discovery_service
from src.services.linkedin_publisher import linkedin_publisher
from src.db.supabase_client import (
    get_action_queue,
    get_action_by_id,
    update_action_queue_status,
)
from src.jobs.client import inngest_client
from src.jobs.inngest_functions import (
    scheduled_builder_discovery,
    stale_followup_checker,
)

app = FastAPI(
    title="NetworkAI Core Engine",
    description="Intelligent Networking Co-Pilot API powered by LangGraph, Supabase, Inngest, and Gemini",
    version="0.1.0",
)

# ==============================================================================
# CORS Configuration
# Allows localhost:3000, *.vercel.app preview/production domains, and Chrome extensions
# ==============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^(https://.*\.vercel\.app|chrome-extension://.*)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# Inngest 24/7 Cloud Background Automation Service
# Registers cron discovery (every 6h) and stale follow-up checker (daily 9am IST)
# ==============================================================================
inngest.fast_api.serve(
    app,
    inngest_client,
    [scheduled_builder_discovery, stale_followup_checker],
    serve_path="/api/inngest",
    enable_unauthed_sync=False if settings.ENVIRONMENT == "test" else None,
)


@app.get("/health")
def health_check():
    """Health check endpoint for Railway, Vercel, and uptime probes."""
    return {
        "status": "healthy",
        "service": "networkai-backend",
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "inngest_registered": True,
    }


@app.post("/api/analyze-profile", response_model=ProfileAnalyzeResponse)
def analyze_profile(payload: ProfileAnalyzeRequest):
    """Executes the LangGraph 3-node workflow (profiler_node -> drafter_node).
    
    Analyzes the profile, calculates relevance, identifies conversation hooks,
    generates a personalized draft, and queues it in Supabase action_queue.
    """
    profile_dict = payload.model_dump()
    result_state = execute_profile_analysis(profile_data=profile_dict)

    if not result_state.profiler_output or not result_state.action_item:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate profile analysis or draft action."
        )

    return ProfileAnalyzeResponse(
        status="success",
        contact_id=result_state.contact_id,
        profiler_output=result_state.profiler_output,
        action_item=result_state.action_item
    )


@app.post("/api/discover", response_model=DiscoveryResponse)
def discover_builders(payload: DiscoveryRequest):
    """Autonomous external builder discovery service.
    
    Searches public AI/ML repositories and developer profiles, extracts prospects,
    and automatically queues high-relevance connection actions.
    """
    result = discovery_service.discover_ai_builders(
        topic=payload.topic,
        limit=payload.limit
    )
    builders = result.get("builders", [])
    queued_actions = result.get("queued_actions", [])

    return DiscoveryResponse(
        status="success",
        builders_found=len(builders),
        builders=builders,
        queued_actions=queued_actions
    )


@app.post("/api/publish-post", response_model=PublishPostResponse)
def publish_post(payload: PublishPostRequest):
    """Publishes a post to LinkedIn feed using official Posts API (OAuth w_member_social)."""
    return linkedin_publisher.publish_post(
        commentary=payload.commentary,
        author_urn=payload.author_urn,
        access_token=payload.access_token,
        visibility=payload.visibility,
    )


@app.get("/api/queue", response_model=List[ActionQueueModel])
def list_action_queue(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status (e.g. pending_approval)")
):
    """Retrieves draft comments, connection notes, and follow-ups from the action_queue."""
    records = get_action_queue(status=status_filter)
    return [ActionQueueModel(**r) for r in records]


@app.post("/api/queue/{action_id}/approve", response_model=QueueActionApprovalResponse)
def approve_queue_action(action_id: str):
    """Approves a queued action item and triggers the LangGraph memory_node.
    
    1. Updates action status to 'approved'.
    2. Records the approved message in interactions table.
    3. Runs memory_node to summarize interaction and upsert normalized 768-dim vector embedding into contacts.
    """
    item = get_action_by_id(action_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Action item {action_id} not found."
        )

    # 1. Update status
    updated_item = update_action_queue_status(action_id, "approved")
    contact_id = item.get("contact_id")

    # 2. Trigger memory_node
    memory_updated = False
    if contact_id:
        mem_state = execute_memory_update(
            contact_id=contact_id,
            action_type=item.get("action_type", "message"),
            draft_content=item.get("content", ""),
        )
        memory_updated = mem_state.memory_updated

    return QueueActionApprovalResponse(
        status="approved",
        action_id=action_id,
        contact_id=contact_id,
        memory_updated=memory_updated,
        interaction_recorded=True,
    )
