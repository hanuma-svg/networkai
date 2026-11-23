from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from src.models.schemas import ProfilerOutput, ActionQueueModel


class WorkflowState(BaseModel):
    """LangGraph execution state passed through profiler, drafter, and memory nodes."""
    profile_data: Dict[str, Any] = Field(default_factory=dict)
    contact_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    profiler_output: Optional[ProfilerOutput] = None
    action_type: Optional[str] = None
    draft_content: Optional[str] = None
    action_id: Optional[str] = None
    action_status: Optional[str] = None
    action_item: Optional[ActionQueueModel] = None
    interaction_summary: Optional[str] = None
    embedding: Optional[List[float]] = None
    memory_updated: bool = False
    error: Optional[str] = None
