# 🎙️ Meeting Platform — Cloud Edition

Multi-agent meeting intelligence platform. Record meetings in the browser, upload files, and get structured notes — deployed on Railway, open to any team.

## Architecture

```
Browser (mic recording / file upload)
         ↓
   [FastAPI Backend]
         ↓
   [OrchestratorAgent]
         ├── [TranscriptionAgent]  → OpenAI Whisper API
         │         ↓  (transcript)
         ├── [SummaryAgent]        ┐
         ├── [ActionItemsAgent]    ├── run in parallel via asyncio.gather()
         └── [BucketingAgent]      ┘
                   ↓
           [Supabase DB + Storage]
                   ↓
           [NotificationAgent]  → email (optional)
```

## Prerequisites

You need accounts on four services (all have free tiers):

| Service | Purpose | URL |
|---------|---------|-----|
| Supabase | Database + Storage + Auth | supabase.com |
| Railway | Deployment | railway.app |
| Anthropic | Claude API | console.anthropic.com |
| OpenAI | Whisper transcription | platform.openai.com |

---

## Setup — Step by Step

### 1. Supabase

1. Create a new project at [supabase.com](https://supabase.com)
2. Go to **SQL Editor** → **New Query**, paste the contents of `db/schema.sql`, and run it
3. Go to **Authentication** → **Providers** → enable **Google**
4. Add your Google OAuth credentials (see step 3 below)
5. Go to **Settings** → **API** — copy:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_ANON_KEY`
   - `service_role` key → `SUPABASE_SERVICE_KEY`

### 2. Google OAuth

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (or use existing)
3. Go to **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth Client ID**
4. Application type: **Web application**
5. Add authorised redirect URI: `https://your-project.supabase.co/auth/v1/callback`
6. Copy **Client ID** → `GOOGLE_CLIENT_ID`
7. Copy **Client Secret** → `GOOGLE_CLIENT_SECRET`

### 3. Environment variables

Copy `.env.example` to `.env` and fill in all values:

```bash
cp .env.example .env
```

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Run locally

```bash
pip3 install -r requirements.txt
uvicorn main:app --reload
```

Open [http://localhost:8000](http://localhost:8000)

---

## Deploy to Railway

1. Push your code to a GitHub repo
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
3. Select your repo
4. Go to **Variables** and add all the keys from your `.env` file
5. Add `APP_URL` = your Railway public URL (shown in Settings → Domains)
6. Railway auto-deploys on every push

Update your Google OAuth redirect URI to include your Railway URL:
```
https://your-project.supabase.co/auth/v1/callback
```

---

## Features

- **Browser mic recording** — one click, records directly in the dashboard
- **File upload** — drop any mp3/mp4/m4a/wav/webm
- **Multi-agent analysis** — Summary, Action Items, and Bucketing agents run in parallel
- **Real-time status** — SSE stream shows processing progress live
- **Action item tracker** — all tasks across all meetings, update status inline
- **Upcoming meetings** — schedule future meetings with agenda and join link
- **Google OAuth** — no passwords, sign in with Google

## Phase 2 — Meeting Bot (auto-join)

To auto-join Zoom/Teams meetings:
- **Zoom**: register a Zoom app at [marketplace.zoom.us](https://marketplace.zoom.us) and use the Meeting SDK
- **Teams**: register an Azure AD app and use the Teams Bot Framework

These require additional app registrations with each platform. The agent code will slot into `agents/` as `ZoomBotAgent` and `TeamsBotAgent`.

## Environment Variables Reference

| Variable | Where to get it |
|----------|----------------|
| `SUPABASE_URL` | Supabase → Settings → API |
| `SUPABASE_ANON_KEY` | Supabase → Settings → API |
| `SUPABASE_SERVICE_KEY` | Supabase → Settings → API |
| `ANTHROPIC_API_KEY` | console.anthropic.com → API Keys |
| `OPENAI_API_KEY` | platform.openai.com → API Keys |
| `SECRET_KEY` | Generate randomly (see above) |
| `GOOGLE_CLIENT_ID` | Google Cloud Console → Credentials |
| `GOOGLE_CLIENT_SECRET` | Google Cloud Console → Credentials |
| `APP_URL` | Your Railway public URL |
