import json
from typing import Any, Dict
from src.config import settings
from src.graph.state import WorkflowState
from src.models.schemas import ProfilerOutput, ActionQueueModel
from src.services.embeddings import generate_embedding
from src.db.supabase_client import (
    upsert_contact,
    get_contact_by_linkedin,
    get_contact_by_id,
    insert_action_queue,
    update_contact_embedding,
    insert_interaction,
)


def _get_genai_client():
    if not settings.GEMINI_API_KEY:
        return None
    try:
        from google import genai
        return genai.Client(api_key=settings.GEMINI_API_KEY)
    except Exception:
        return None


# ==============================================================================
# Node 1: profiler_node
# Analyzes profile payload + existing relationship context, returning ProfilerOutput
# ==============================================================================

def profiler_node(state: WorkflowState) -> WorkflowState:
    profile = state.profile_data or {}
    full_name = profile.get("full_name", "Professional")
    headline = profile.get("headline", "")
    company = profile.get("company", "")
    recent_post = profile.get("recent_post_text", "")
    linkedin_url = profile.get("linkedin_url", "")

    # Look up existing contact if not already provided
    contact = None
    if state.contact_id:
        contact = get_contact_by_id(state.contact_id)
    elif linkedin_url:
        contact = get_contact_by_linkedin(linkedin_url)

    if contact and not state.contact_id:
        state.contact_id = contact.get("id")

    client = _get_genai_client()
    profiler_result: ProfilerOutput

    if client:
        try:
            prompt = f"""
            You are an expert AI networking strategist. Analyze this LinkedIn profile and context:
            Name: {full_name}
            Headline: {headline}
            Company: {company}
            Recent Post / Content: {recent_post}
            Existing Contact Context: {json.dumps(state.context or {})}

            Evaluate:
            1. Relevance score (0-100) based on AI/engineering/business synergy.
            2. 2-3 specific shared conversation hooks or talking points.
            3. Recommended action:
               - "draft_comment" if they have an engaging recent post
               - "connection_note" if not yet connected
               - "follow_up" if prior interaction exists

            Respond strictly in valid JSON matching this schema:
            {{
                "relevance_score": <int between 0 and 100>,
                "shared_hooks": ["<hook1>", "<hook2>"],
                "recommended_action": "draft_comment" | "connection_note" | "follow_up"
            }}
            """
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            data = json.loads(response.text)
            profiler_result = ProfilerOutput(**data)
        except Exception:
            profiler_result = _fallback_profiler(profile, recent_post)
    else:
        profiler_result = _fallback_profiler(profile, recent_post)

    state.profiler_output = profiler_result
    state.action_type = profiler_result.recommended_action
    return state


def _fallback_profiler(profile: Dict[str, Any], recent_post: str) -> ProfilerOutput:
    headline = (profile.get("headline") or "").lower()
    score = 75
    if any(k in headline for k in ["ai", "founder", "engineer", "agent", "llm", "cto"]):
        score = 92

    hooks = [
        f"Synergy between our AI workflows and {profile.get('company', 'your current projects')}",
        f"Alignment with your background as {profile.get('headline', 'builder')}",
    ]

    action = "draft_comment" if recent_post else "connection_note"
    return ProfilerOutput(
        relevance_score=score,
        shared_hooks=hooks,
        recommended_action=action
    )


# ==============================================================================
# Node 2: drafter_node
# Generates personalized draft (strictly <= 300 chars for connection notes)
# and inserts into action_queue with status="pending_approval"
# ==============================================================================

def drafter_node(state: WorkflowState) -> WorkflowState:
    profile = state.profile_data or {}
    full_name = profile.get("full_name", "there")
    first_name = full_name.split()[0] if full_name else "there"
    action_type = state.action_type or "connection_note"
    hooks = state.profiler_output.shared_hooks if state.profiler_output else []
    hooks_str = ", ".join(hooks)

    client = _get_genai_client()
    draft = ""

    if client:
        try:
            if action_type == "connection_note":
                prompt = f"""
                Write a concise, high-conversion LinkedIn connection request note to {first_name}.
                Headline: {profile.get('headline')}
                Company: {profile.get('company')}
                Shared hooks: {hooks_str}

                CRITICAL REQUIREMENT:
                The total note length MUST BE AT MOST 280 CHARACTERS (strict LinkedIn limit is 300).
                Do not include placeholders. Be genuine, peer-to-peer, and direct.
                """
            elif action_type == "draft_comment":
                prompt = f"""
                Write an insightful, value-adding LinkedIn post comment to {first_name}.
                Post: {profile.get('recent_post_text')}
                Shared hooks: {hooks_str}
                Length: 2-3 concise sentences. Add authentic builder perspective.
                """
            else:  # follow_up
                prompt = f"""
                Write a warm follow-up message to {first_name}.
                Context: {json.dumps(state.context or {})}
                Shared hooks: {hooks_str}
                Length: Under 80 words. Clear low-friction CTA.
                """

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
            draft = response.text.strip().strip('"')
        except Exception:
            draft = _fallback_draft(first_name, action_type, profile)
    else:
        draft = _fallback_draft(first_name, action_type, profile)

    # Strictly enforce <= 300 characters for connection notes
    if action_type == "connection_note" and len(draft) > 300:
        draft = draft[:297] + "..."

    state.draft_content = draft

    # Ensure contact is registered in Supabase
    contact = upsert_contact({
        "id": state.contact_id,
        "full_name": profile.get("full_name", "Professional"),
        "headline": profile.get("headline"),
        "company": profile.get("company"),
        "location": profile.get("location"),
        "linkedin_url": profile.get("linkedin_url"),
        "metadata": {
            "source": "langgraph_profiler",
            "relevance_score": state.profiler_output.relevance_score if state.profiler_output else None,
        }
    })
    state.contact_id = contact.get("id")

    # Insert into action_queue with status="pending_approval"
    queue_record = insert_action_queue({
        "contact_id": state.contact_id,
        "action_type": action_type,
        "content": draft,
        "status": "pending_approval",
        "metadata": {
            "hooks": hooks,
            "relevance_score": state.profiler_output.relevance_score if state.profiler_output else None,
        }
    })

    state.action_id = queue_record.get("id")
    state.action_status = queue_record.get("status")
    state.action_item = ActionQueueModel(**queue_record)
    return state


def _fallback_draft(first_name: str, action_type: str, profile: Dict[str, Any]) -> str:
    if action_type == "connection_note":
        note = f"Hi {first_name}, impressed by your work at {profile.get('company', 'your team')}. Building AI automation & agent workflows here—would love to connect!"
        return note[:300]
    elif action_type == "draft_comment":
        return f"Great insights, {first_name}! The intersection of agentic workflows and developer tooling makes this especially timely."
    else:
        return f"Hi {first_name}, following up on our previous note. Wanted to share a quick update on our AI agent experiments—open to a brief exchange?"


# ==============================================================================
# Node 3: memory_node
# Summarizes approved interactions and upserts updated normalized 768-dim vector
# embeddings into contacts.embedding in Supabase
# ==============================================================================

def memory_node(state: WorkflowState) -> WorkflowState:
    contact_id = state.contact_id
    if not contact_id and state.action_item:
        contact_id = state.action_item.contact_id

    if not contact_id:
        state.error = "Missing contact_id for memory_node."
        return state

    contact = get_contact_by_id(contact_id)
    if not contact:
        state.error = f"Contact {contact_id} not found."
        return state

    summary_text = state.interaction_summary
    if not summary_text:
        draft = state.draft_content or (state.action_item.content if state.action_item else "")
        action_type = state.action_type or (state.action_item.action_type if state.action_item else "interaction")
        summary_text = (
            f"Contact: {contact.get('full_name')}. Headline: {contact.get('headline')}. "
            f"Company: {contact.get('company')}. Interaction Type: {action_type}. Content: {draft}."
        )

    # Generate 768-dim L2-normalized embedding
    embedding = generate_embedding(summary_text)
    state.embedding = embedding

    # Update contacts table with the new embedding
    updated = update_contact_embedding(contact_id, embedding)
    if updated:
        state.memory_updated = True

    # Record interaction in interactions table
    if state.draft_content or (state.action_item and state.action_item.content):
        insert_interaction({
            "contact_id": contact_id,
            "type": state.action_type or "message",
            "channel": "linkedin",
            "direction": "outbound",
            "content": state.draft_content or state.action_item.content,
            "metadata": {"approved": True, "memory_synced": True}
        })

    return state
