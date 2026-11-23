from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, model_validator


# ==============================================================================
# Database Table Models (Exact 1:1 match with supabase/schema.sql)
# ==============================================================================

class ContactModel(BaseModel):
    """Corresponds to the `contacts` table in supabase/schema.sql."""
    id: Optional[str] = None
    full_name: str
    email: Optional[str] = None
    headline: Optional[str] = None
    company: Optional[str] = None
    linkedin_url: Optional[str] = None
    location: Optional[str] = None
    embedding: Optional[List[float]] = None  # 768-dim normalized vector
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class InteractionModel(BaseModel):
    """Corresponds to the `interactions` table in supabase/schema.sql."""
    id: Optional[str] = None
    contact_id: str
    type: Literal["message", "connection_request", "comment", "email", "meeting", "other"]
    channel: str = "linkedin"
    direction: Literal["inbound", "outbound"]
    content: Optional[str] = None
    interaction_date: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None


class ActionQueueModel(BaseModel):
    """Corresponds to the `action_queue` table in supabase/schema.sql."""
    id: Optional[str] = None
    contact_id: Optional[str] = None
    action_type: Literal["draft_comment", "connection_note", "follow_up"]
    content: str
    status: Literal["pending_approval", "approved", "rejected", "executed"] = "pending_approval"
    scheduled_for: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @model_validator(mode="after")
    def validate_connection_note_length(self) -> "ActionQueueModel":
        """Enforces schema constraint: action_type != 'connection_note' OR char_length(content) <= 300."""
        if self.action_type == "connection_note" and len(self.content) > 300:
            raise ValueError(f"Connection note must be <= 300 characters. Current length: {len(self.content)}")
        return self


# ==============================================================================
# LangGraph & API Request / Response Schemas
# ==============================================================================

class ProfilerOutput(BaseModel):
    """Structured Pydantic output produced by profiler_node in LangGraph."""
    relevance_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Relevance score from 0 to 100 based on synergy and background."
    )
    shared_hooks: List[str] = Field(
        default_factory=list,
        description="Identified common themes, shared technologies, or conversation openers."
    )
    recommended_action: Literal["draft_comment", "connection_note", "follow_up"] = Field(
        ...,
        description="Target recommended action to take."
    )


class ProfileAnalyzeRequest(BaseModel):
    """Payload for POST /api/analyze-profile."""
    full_name: str
    headline: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    recent_post_text: Optional[str] = None
    notes: Optional[str] = None


class ProfileAnalyzeResponse(BaseModel):
    """Response returned by POST /api/analyze-profile."""
    status: str
    contact_id: Optional[str] = None
    profiler_output: ProfilerOutput
    action_item: ActionQueueModel


class DiscoveryRequest(BaseModel):
    """Payload for POST /api/discover."""
    topic: str = "agentic-ai"
    keywords: List[str] = Field(default_factory=lambda: ["LangGraph", "FastAPI", "Agent"])
    limit: int = Field(default=5, ge=1, le=20)


class DiscoveredBuilder(BaseModel):
    name: str
    github_username: str
    bio: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    repository: Optional[str] = None
    website_or_linkedin: Optional[str] = None
    relevance_reason: str


class DiscoveryResponse(BaseModel):
    status: str
    builders_found: int
    builders: List[DiscoveredBuilder]
    queued_actions: List[ActionQueueModel]


class PublishPostRequest(BaseModel):
    """Payload for POST /api/publish-post (LinkedIn official API)."""
    commentary: str = Field(..., min_length=1, max_length=3000)
    author_urn: Optional[str] = None
    access_token: Optional[str] = None
    visibility: Literal["PUBLIC", "CONNECTIONS"] = "PUBLIC"


class PublishPostResponse(BaseModel):
    status: str
    post_urn: str
    lifecycle_state: str = "PUBLISHED"
    details: Dict[str, Any] = Field(default_factory=dict)


class QueueActionApprovalResponse(BaseModel):
    status: str
    action_id: str
    contact_id: Optional[str] = None
    memory_updated: bool
    interaction_recorded: bool
