"""
Meeting Platform — FastAPI Application
───────────────────────────────────────
Routes:
  GET  /                    → redirect to /dashboard or /login
  GET  /login               → login page
  GET  /auth/google         → start Google OAuth (via Supabase)
  GET  /auth/callback       → OAuth callback
  GET  /auth/logout         → clear session
  GET  /dashboard           → main dashboard
  GET  /meetings/{id}       → meeting detail
  GET  /action-items        → all action items
  GET  /upcoming            → upcoming meetings
  POST /meetings/upload     → upload audio file → trigger pipeline
  POST /meetings/record     → receive browser mic recording → trigger pipeline
  POST /upcoming            → add upcoming meeting
  PATCH /action-items/{id}  → update status
  DELETE /meetings/{id}     → delete meeting
  GET  /meetings/{id}/stream → SSE: real-time processing status
"""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Optional

import httpx
from fastapi import (FastAPI, Request, Form, File, UploadFile,
                     HTTPException, BackgroundTasks, Response)
from fastapi.responses import (HTMLResponse, RedirectResponse,
                                JSONResponse, StreamingResponse)
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from config import settings
from agents import OrchestratorAgent
import db.client as db

# ── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(title="Meeting Platform", version="2.0")
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")
templates = Jinja2Templates(directory="frontend/templates")

orchestrator = OrchestratorAgent()

# ── Auth helpers ──────────────────────────────────────────────────────────────

def get_user(request: Request) -> Optional[dict]:
    return request.session.get("user")

def require_user(request: Request) -> dict:
    user = get_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user

def _supabase_oauth_url(redirect_uri: str) -> str:
    return (
        f"{settings.SUPABASE_URL}/auth/v1/authorize"
        f"?provider=google"
        f"&redirect_to={redirect_uri}"
    )

# ── Auth routes ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    if get_user(request):
        return RedirectResponse("/dashboard")
    return RedirectResponse("/login")


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if get_user(request):
        return RedirectResponse("/dashboard")
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/auth/google")
async def auth_google(request: Request):
    callback = f"{settings.APP_URL}/auth/callback"
    return RedirectResponse(_supabase_oauth_url(callback))


@app.get("/auth/callback")
async def auth_callback(request: Request, access_token: str = None,
                        refresh_token: str = None, code: str = None):
    """Handle Supabase OAuth callback — exchange code for user info."""
    try:
        from supabase import create_client
        sb = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)

        if code:
            session = sb.auth.exchange_code_for_session({"auth_code": code})
            user    = session.user
        elif access_token:
            resp = sb.auth.get_user(access_token)
            user = resp.user
        else:
            return RedirectResponse("/login?error=no_token")

        request.session["user"] = {
            "id":    user.id,
            "email": user.email,
            "name":  user.user_metadata.get("full_name", user.email),
            "avatar": user.user_metadata.get("avatar_url", ""),
        }
        return RedirectResponse("/dashboard")
    except Exception as e:
        print(f"Auth error: {e}")
        return RedirectResponse(f"/login?error=auth_failed")


@app.get("/auth/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login")

    meetings  = db.get_user_meetings(user["id"], limit=20)
    upcoming  = db.get_upcoming_meetings(user["id"])
    stats     = db.get_user_stats(user["id"])

    return templates.TemplateResponse("dashboard.html", {
        "request":  request,
        "user":     user,
        "meetings": meetings,
        "upcoming": upcoming,
        "stats":    stats,
    })


# ── Meeting detail ────────────────────────────────────────────────────────────

@app.get("/meetings/{meeting_id}", response_class=HTMLResponse)
async def meeting_detail(request: Request, meeting_id: str):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login")

    meeting = db.get_meeting_full(meeting_id)
    if not meeting or meeting.get("user_id") != user["id"]:
        raise HTTPException(404, "Meeting not found")

    return templates.TemplateResponse("meeting.html", {
        "request": request,
        "user":    user,
        "meeting": meeting,
    })


@app.delete("/meetings/{meeting_id}")
async def delete_meeting(request: Request, meeting_id: str):
    user = get_user(request)
    if not user:
        raise HTTPException(401)
    meeting = db.get_meeting(meeting_id)
    if not meeting or meeting["user_id"] != user["id"]:
        raise HTTPException(404)
    db.delete_meeting(meeting_id)
    return JSONResponse({"ok": True})


# ── Action items ──────────────────────────────────────────────────────────────

@app.get("/action-items", response_class=HTMLResponse)
async def action_items_page(request: Request, status: str = None):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login")

    items = db.get_user_action_items(user["id"], status=status)
    return templates.TemplateResponse("action_items.html", {
        "request": request,
        "user":    user,
        "items":   items,
        "filter":  status,
    })


@app.patch("/action-items/{item_id}")
async def update_action_item(request: Request, item_id: str):
    user = get_user(request)
    if not user:
        raise HTTPException(401)
    body = await request.json()
    item = db.update_action_item(item_id, **body)
    return JSONResponse(item)


# ── Upcoming meetings ─────────────────────────────────────────────────────────

@app.get("/upcoming", response_class=HTMLResponse)
async def upcoming_page(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login")
    meetings = db.get_upcoming_meetings(user["id"])
    return templates.TemplateResponse("upcoming.html", {
        "request": request, "user": user, "meetings": meetings
    })


@app.post("/upcoming")
async def add_upcoming(
    request:      Request,
    title:        str = Form(...),
    scheduled_at: str = Form(...),
    attendees:    str = Form(""),
    agenda:       str = Form(""),
    meeting_link: str = Form(""),
):
    user = get_user(request)
    if not user:
        raise HTTPException(401)
    db.create_upcoming_meeting(user["id"], {
        "title":        title,
        "scheduled_at": scheduled_at,
        "attendees":    attendees,
        "agenda":       agenda,
        "meeting_link": meeting_link,
    })
    return RedirectResponse("/upcoming", status_code=303)


# ── Upload audio file → process ───────────────────────────────────────────────

@app.post("/meetings/upload")
async def upload_meeting(
    request:         Request,
    background_tasks: BackgroundTasks,
    file:             UploadFile = File(...),
    name:             str = Form(""),
    extra_buckets:    str = Form(""),
    notify_email:     str = Form(""),
):
    user = get_user(request)
    if not user:
        raise HTTPException(401)

    audio_bytes = await file.read()
    meeting     = db.create_meeting(user["id"], title=name or file.filename)
    meeting_id  = meeting["id"]

    # Upload audio to Supabase Storage
    ext  = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "webm"
    path = db.upload_audio(user["id"], meeting_id, audio_bytes, ext)
    db.update_meeting(meeting_id, audio_url=path)

    buckets = [b.strip() for b in extra_buckets.split(",") if b.strip()]

    background_tasks.add_task(
        _run_pipeline,
        meeting_id   = meeting_id,
        user_id      = user["id"],
        audio_source = audio_bytes,
        filename     = file.filename,
        extra_buckets = buckets,
        notify_email  = notify_email or None,
    )
    return RedirectResponse(f"/meetings/{meeting_id}", status_code=303)


# ── Browser mic recording → process ──────────────────────────────────────────

@app.post("/meetings/record")
async def record_meeting(
    request:          Request,
    background_tasks: BackgroundTasks,
    file:             UploadFile = File(...),
    name:             str = Form(""),
    extra_buckets:    str = Form(""),
):
    user = get_user(request)
    if not user:
        raise HTTPException(401)

    audio_bytes = await file.read()
    meeting     = db.create_meeting(user["id"], title=name or "Browser Recording")
    meeting_id  = meeting["id"]

    path = db.upload_audio(user["id"], meeting_id, audio_bytes, "webm")
    db.update_meeting(meeting_id, audio_url=path)

    buckets = [b.strip() for b in extra_buckets.split(",") if b.strip()]

    background_tasks.add_task(
        _run_pipeline,
        meeting_id    = meeting_id,
        user_id       = user["id"],
        audio_source  = audio_bytes,
        filename      = "recording.webm",
        extra_buckets = buckets,
    )
    return JSONResponse({"meeting_id": meeting_id})


# ── SSE: real-time status stream ──────────────────────────────────────────────

@app.get("/meetings/{meeting_id}/stream")
async def meeting_stream(request: Request, meeting_id: str):
    """Server-Sent Events — polls DB and pushes status to browser."""
    async def generator():
        for _ in range(120):   # poll for up to 2 minutes
            meeting = db.get_meeting(meeting_id)
            if not meeting:
                break
            status = meeting.get("status", "pending")
            yield f"data: {json.dumps({'status': status})}\n\n"
            if status in ("completed", "failed"):
                break
            await asyncio.sleep(2)
        yield "data: {\"status\": \"timeout\"}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")


# ── Background task helper ────────────────────────────────────────────────────

async def _run_pipeline(
    meeting_id:    str,
    user_id:       str,
    audio_source:  bytes,
    filename:      str,
    extra_buckets: list[str] = None,
    notify_email:  str = None,
):
    await orchestrator.run(
        meeting_id    = meeting_id,
        user_id       = user_id,
        audio_source  = audio_source,
        filename      = filename,
        extra_buckets = extra_buckets,
        notify_email  = notify_email,
        app_url       = settings.APP_URL,
    )
