from typing import Any, Dict, Optional
from langgraph.graph import StateGraph, END
from src.graph.state import WorkflowState
from src.graph.nodes import profiler_node, drafter_node, memory_node


# ==============================================================================
# LangGraph Workflow 1: Profile Analysis & Action Drafting
# profiler_node -> drafter_node -> END
# ==============================================================================
_profile_graph_builder = StateGraph(WorkflowState)
_profile_graph_builder.add_node("profiler", profiler_node)
_profile_graph_builder.add_node("drafter", drafter_node)
_profile_graph_builder.set_entry_point("profiler")
_profile_graph_builder.add_edge("profiler", "drafter")
_profile_graph_builder.add_edge("drafter", END)

profile_analysis_workflow = _profile_graph_builder.compile()


# ==============================================================================
# LangGraph Workflow 2: Memory Update & 768-dim Embedding Sync
# memory_node -> END
# ==============================================================================
_memory_graph_builder = StateGraph(WorkflowState)
_memory_graph_builder.add_node("memory", memory_node)
_memory_graph_builder.set_entry_point("memory")
_memory_graph_builder.add_edge("memory", END)

memory_update_workflow = _memory_graph_builder.compile()


# ==============================================================================
# Execution Helpers
# ==============================================================================

def execute_profile_analysis(
    profile_data: Dict[str, Any],
    context: Optional[Dict[str, Any]] = None,
    contact_id: Optional[str] = None
) -> WorkflowState:
    """Executes the profiler_node -> drafter_node pipeline, returning state with draft & queue record."""
    initial_state = WorkflowState(
        profile_data=profile_data,
        context=context,
        contact_id=contact_id
    )
    result = profile_analysis_workflow.invoke(initial_state)
    if isinstance(result, dict):
        return WorkflowState(**result)
    return result


def execute_memory_update(
    contact_id: str,
    action_type: str = "message",
    draft_content: str = "",
    summary: Optional[str] = None
) -> WorkflowState:
    """Executes memory_node to summarize interactions and update 768-dim L2-normalized embedding."""
    initial_state = WorkflowState(
        contact_id=contact_id,
        action_type=action_type,
        draft_content=draft_content,
        interaction_summary=summary
    )
    result = memory_update_workflow.invoke(initial_state)
    if isinstance(result, dict):
        return WorkflowState(**result)
    return result
