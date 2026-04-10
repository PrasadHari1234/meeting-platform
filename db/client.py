"""Supabase client wrapper — DB + Storage operations."""

import uuid
from datetime import datetime
from typing import Optional
from supabase import create_client, Client
from config import settings


def get_client() -> Client:
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


# ── Meetings ─────────────────────────────────────────────────────────────────

def create_meeting(user_id: str, title: str = None, scheduled_at: str = None) -> dict:
    db = get_client()
    row = {
        "user_id": user_id,
        "title": title or "Untitled Meeting",
        "status": "pending",
        "scheduled_at": scheduled_at,
    }
    res = db.table("meetings").insert(row).execute()
    return res.data[0]


def update_meeting(meeting_id: str, **kwargs) -> dict:
    db = get_client()
    kwargs["updated_at"] = datetime.utcnow().isoformat()
    res = db.table("meetings").update(kwargs).eq("id", meeting_id).execute()
    return res.data[0]


def get_meeting(meeting_id: str) -> Optional[dict]:
    db = get_client()
    res = db.table("meetings").select("*").eq("id", meeting_id).execute()
    return res.data[0] if res.data else None


def get_user_meetings(user_id: str, limit: int = 50) -> list[dict]:
    db = get_client()
    res = (
        db.table("meetings")
        .select("*")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data


def delete_meeting(meeting_id: str) -> None:
    db = get_client()
    db.table("meetings").delete().eq("id", meeting_id).execute()


# ── Action Items ─────────────────────────────────────────────────────────────

def save_action_items(meeting_id: str, user_id: str, items: list[dict]) -> None:
    db = get_client()
    rows = [
        {
            "meeting_id": meeting_id,
            "user_id": user_id,
            "item": a.get("item", ""),
            "owner": a.get("owner", "TBD"),
            "deadline": a.get("deadline", "Not specified"),
            "priority": a.get("priority", "Medium"),
            "status": "open",
        }
        for a in items
    ]
    if rows:
        db.table("action_items").insert(rows).execute()


def get_user_action_items(user_id: str, status: str = None) -> list[dict]:
    db = get_client()
    q = (
        db.table("action_items")
        .select("*, meetings(title, created_at)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
    )
    if status:
        q = q.eq("status", status)
    return q.execute().data


def update_action_item(item_id: str, **kwargs) -> dict:
    db = get_client()
    res = db.table("action_items").update(kwargs).eq("id", item_id).execute()
    return res.data[0]


# ── Buckets, Participants, Decisions, Follow-ups ──────────────────────────────

def save_meeting_details(meeting_id: str, analysis: dict) -> None:
    db = get_client()

    if analysis.get("buckets"):
        rows = [
            {
                "meeting_id": meeting_id,
                "name": b["name"],
                "is_new": b.get("is_new", False),
                "items": b.get("items", []),
            }
            for b in analysis["buckets"] if b.get("items")
        ]
        if rows:
            db.table("meeting_buckets").insert(rows).execute()

    if analysis.get("participants_mentioned"):
        rows = [{"meeting_id": meeting_id, "name": p}
                for p in analysis["participants_mentioned"]]
        db.table("participants").insert(rows).execute()

    if analysis.get("decisions_made"):
        rows = [{"meeting_id": meeting_id, "decision": d}
                for d in analysis["decisions_made"]]
        db.table("decisions").insert(rows).execute()

    if analysis.get("follow_up_questions"):
        rows = [{"meeting_id": meeting_id, "question": q}
                for q in analysis["follow_up_questions"]]
        db.table("follow_up_questions").insert(rows).execute()


def get_meeting_full(meeting_id: str) -> dict:
    """Fetch meeting with all related data."""
    db = get_client()
    meeting  = db.table("meetings").select("*").eq("id", meeting_id).execute().data
    if not meeting:
        return {}
    m = meeting[0]
    m["action_items"]   = db.table("action_items").select("*").eq("meeting_id", meeting_id).execute().data
    m["buckets"]        = db.table("meeting_buckets").select("*").eq("meeting_id", meeting_id).execute().data
    m["participants"]   = db.table("participants").select("*").eq("meeting_id", meeting_id).execute().data
    m["decisions"]      = db.table("decisions").select("*").eq("meeting_id", meeting_id).execute().data
    m["follow_ups"]     = db.table("follow_up_questions").select("*").eq("meeting_id", meeting_id).execute().data
    return m


# ── Upcoming Meetings ─────────────────────────────────────────────────────────

def get_upcoming_meetings(user_id: str) -> list[dict]:
    db = get_client()
    res = (
        db.table("upcoming_meetings")
        .select("*")
        .eq("user_id", user_id)
        .gte("scheduled_at", datetime.utcnow().isoformat())
        .order("scheduled_at")
        .limit(10)
        .execute()
    )
    return res.data


def create_upcoming_meeting(user_id: str, data: dict) -> dict:
    db = get_client()
    data["user_id"] = user_id
    res = db.table("upcoming_meetings").insert(data).execute()
    return res.data[0]


# ── Storage ──────────────────────────────────────────────────────────────────

def upload_audio(user_id: str, meeting_id: str, audio_bytes: bytes, ext: str = "webm") -> str:
    db = get_client()
    path = f"{user_id}/{meeting_id}/audio.{ext}"
    db.storage.from_("meetings").upload(path, audio_bytes, {"content-type": f"audio/{ext}"})
    return path


def get_signed_url(path: str, expires_in: int = 3600) -> str:
    db = get_client()
    res = db.storage.from_("meetings").create_signed_url(path, expires_in)
    return res.get("signedURL", "")


def upload_docx(user_id: str, meeting_id: str, docx_bytes: bytes) -> str:
    db = get_client()
    path = f"{user_id}/{meeting_id}/notes.docx"
    db.storage.from_("meetings").upload(
        path, docx_bytes,
        {"content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}
    )
    return path


# ── Stats ────────────────────────────────────────────────────────────────────

def get_user_stats(user_id: str) -> dict:
    db = get_client()
    meetings     = db.table("meetings").select("id", count="exact").eq("user_id", user_id).eq("status", "completed").execute()
    open_actions = db.table("action_items").select("id", count="exact").eq("user_id", user_id).eq("status", "open").execute()
    done_actions = db.table("action_items").select("id", count="exact").eq("user_id", user_id).eq("status", "done").execute()
    return {
        "total_meetings":      meetings.count or 0,
        "open_action_items":   open_actions.count or 0,
        "done_action_items":   done_actions.count or 0,
    }
