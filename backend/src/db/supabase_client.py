import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from src.config import settings

# Optional real Supabase client initialization
_supabase_client = None

def get_supabase_client():
    """Lazily initializes and returns the Supabase client."""
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = settings.clean_supabase_url
    key = settings.SUPABASE_SERVICE_ROLE_KEY

    if not url or not key:
        return None

    try:
        from supabase import create_client, Client
        _supabase_client = create_client(url, key)
        return _supabase_client
    except Exception:
        return None


# ==============================================================================
# In-memory storage for offline testing / sandbox fallback
# ==============================================================================
_mock_contacts: Dict[str, Dict[str, Any]] = {}
_mock_interactions: Dict[str, Dict[str, Any]] = {}
_mock_action_queue: Dict[str, Dict[str, Any]] = {}


def reset_mock_db():
    """Utility function to clear in-memory mock database during unit tests."""
    global _mock_contacts, _mock_interactions, _mock_action_queue
    _mock_contacts.clear()
    _mock_interactions.clear()
    _mock_action_queue.clear()


# ==============================================================================
# Contacts Queries (Table: contacts)
# ==============================================================================

def upsert_contact(contact_data: Dict[str, Any]) -> Dict[str, Any]:
    """Upserts a contact record in `contacts`."""
    client = get_supabase_client()
    now_iso = datetime.now(timezone.utc).isoformat()

    data = {
        "full_name": contact_data.get("full_name", ""),
        "email": contact_data.get("email"),
        "headline": contact_data.get("headline"),
        "company": contact_data.get("company"),
        "linkedin_url": contact_data.get("linkedin_url"),
        "location": contact_data.get("location"),
        "metadata": contact_data.get("metadata", {}),
        "updated_at": now_iso,
    }
    if contact_data.get("embedding"):
        data["embedding"] = contact_data["embedding"]

    if client:
        try:
            if contact_data.get("id"):
                data["id"] = contact_data["id"]
                res = client.table("contacts").upsert(data).execute()
            elif contact_data.get("linkedin_url"):
                res = client.table("contacts").upsert(data, on_conflict="linkedin_url").execute()
            else:
                res = client.table("contacts").insert(data).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    # Mock in-memory fallback
    cid = contact_data.get("id") or str(uuid.uuid4())
    existing = _mock_contacts.get(cid, {})
    saved = {
        **existing,
        **data,
        "id": cid,
        "created_at": existing.get("created_at", now_iso),
    }
    _mock_contacts[cid] = saved
    return saved


def get_contact_by_linkedin(linkedin_url: str) -> Optional[Dict[str, Any]]:
    """Retrieves a contact by LinkedIn URL."""
    if not linkedin_url:
        return None
    client = get_supabase_client()
    if client:
        try:
            res = client.table("contacts").select("*").eq("linkedin_url", linkedin_url).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    for contact in _mock_contacts.values():
        if contact.get("linkedin_url") == linkedin_url:
            return contact
    return None


def get_contact_by_id(contact_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves a contact by its UUID."""
    if not contact_id:
        return None
    client = get_supabase_client()
    if client:
        try:
            res = client.table("contacts").select("*").eq("id", contact_id).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    return _mock_contacts.get(contact_id)


def update_contact_embedding(contact_id: str, embedding: List[float]) -> Optional[Dict[str, Any]]:
    """Updates the normalized 768-dim vector embedding of a contact."""
    client = get_supabase_client()
    now_iso = datetime.now(timezone.utc).isoformat()
    if client:
        try:
            res = client.table("contacts").update({
                "embedding": embedding,
                "updated_at": now_iso
            }).eq("id", contact_id).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    if contact_id in _mock_contacts:
        _mock_contacts[contact_id]["embedding"] = embedding
        _mock_contacts[contact_id]["updated_at"] = now_iso
        return _mock_contacts[contact_id]
    return None


# ==============================================================================
# Interactions Queries (Table: interactions)
# ==============================================================================

def insert_interaction(interaction_data: Dict[str, Any]) -> Dict[str, Any]:
    """Inserts a record into the `interactions` table."""
    client = get_supabase_client()
    now_iso = datetime.now(timezone.utc).isoformat()
    record = {
        "contact_id": interaction_data["contact_id"],
        "type": interaction_data.get("type", "message"),
        "channel": interaction_data.get("channel", "linkedin"),
        "direction": interaction_data.get("direction", "outbound"),
        "content": interaction_data.get("content", ""),
        "interaction_date": interaction_data.get("interaction_date", now_iso),
        "metadata": interaction_data.get("metadata", {}),
        "created_at": now_iso,
    }
    if interaction_data.get("id"):
        record["id"] = interaction_data["id"]

    if client:
        try:
            res = client.table("interactions").insert(record).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    iid = record.get("id") or str(uuid.uuid4())
    record["id"] = iid
    _mock_interactions[iid] = record
    return record


# ==============================================================================
# Action Queue Queries (Table: action_queue)
# ==============================================================================

def insert_action_queue(action_data: Dict[str, Any]) -> Dict[str, Any]:
    """Inserts an item into `action_queue` awaiting human approval."""
    client = get_supabase_client()
    now_iso = datetime.now(timezone.utc).isoformat()

    content = action_data.get("content", "")
    action_type = action_data.get("action_type", "draft_comment")
    # Enforce strictly <= 300 characters for connection notes
    if action_type == "connection_note" and len(content) > 300:
        content = content[:297] + "..."

    record = {
        "contact_id": action_data.get("contact_id"),
        "action_type": action_type,
        "content": content,
        "status": action_data.get("status", "pending_approval"),
        "scheduled_for": action_data.get("scheduled_for"),
        "metadata": action_data.get("metadata", {}),
        "created_at": now_iso,
        "updated_at": now_iso,
    }
    if action_data.get("id"):
        record["id"] = action_data["id"]

    if client:
        try:
            res = client.table("action_queue").insert(record).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    aid = record.get("id") or str(uuid.uuid4())
    record["id"] = aid
    _mock_action_queue[aid] = record
    return record


def get_action_queue(status: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieves items from `action_queue`, optionally filtered by status."""
    client = get_supabase_client()
    if client:
        try:
            query = client.table("action_queue").select("*").order("created_at", desc=True)
            if status:
                query = query.eq("status", status)
            res = query.execute()
            if res.data:
                return res.data
        except Exception:
            pass

    items = list(_mock_action_queue.values())
    if status:
        items = [i for i in items if i.get("status") == status]
    return sorted(items, key=lambda x: x.get("created_at", ""), reverse=True)


def get_action_by_id(action_id: str) -> Optional[Dict[str, Any]]:
    """Retrieves an action queue item by ID."""
    client = get_supabase_client()
    if client:
        try:
            res = client.table("action_queue").select("*").eq("id", action_id).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    return _mock_action_queue.get(action_id)


def update_action_queue_status(action_id: str, status: str) -> Optional[Dict[str, Any]]:
    """Updates the status of an action queue item."""
    client = get_supabase_client()
    now_iso = datetime.now(timezone.utc).isoformat()
    if client:
        try:
            res = client.table("action_queue").update({
                "status": status,
                "updated_at": now_iso
            }).eq("id", action_id).execute()
            if res.data:
                return res.data[0]
        except Exception:
            pass

    if action_id in _mock_action_queue:
        _mock_action_queue[action_id]["status"] = status
        _mock_action_queue[action_id]["updated_at"] = now_iso
        return _mock_action_queue[action_id]
    return None
