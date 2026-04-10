-- ═══════════════════════════════════════════════════════════════
--  Meeting Platform — Supabase Schema
--  Run this in: Supabase Dashboard → SQL Editor → New Query
-- ═══════════════════════════════════════════════════════════════

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── meetings ────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS meetings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title           TEXT,
    meeting_type    TEXT,
    sentiment       TEXT,
    summary         TEXT,
    transcript      TEXT,
    audio_url       TEXT,          -- Supabase Storage path
    notes_url       TEXT,          -- .docx download path
    status          TEXT DEFAULT 'pending',   -- pending | processing | completed | failed
    error_message   TEXT,
    scheduled_at    TIMESTAMPTZ,
    duration_secs   INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── action_items ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS action_items (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id  UUID REFERENCES meetings(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    item        TEXT NOT NULL,
    owner       TEXT DEFAULT 'TBD',
    deadline    TEXT DEFAULT 'Not specified',
    priority    TEXT DEFAULT 'Medium',   -- High | Medium | Low
    status      TEXT DEFAULT 'open',     -- open | in_progress | done
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── meeting_buckets ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS meeting_buckets (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id  UUID REFERENCES meetings(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    is_new      BOOLEAN DEFAULT FALSE,
    items       JSONB DEFAULT '[]',      -- [{topic, detail}]
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── participants ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS participants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id  UUID REFERENCES meetings(id) ON DELETE CASCADE,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── decisions ───────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS decisions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id  UUID REFERENCES meetings(id) ON DELETE CASCADE,
    decision    TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── follow_up_questions ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS follow_up_questions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    meeting_id  UUID REFERENCES meetings(id) ON DELETE CASCADE,
    question    TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ── upcoming_meetings ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS upcoming_meetings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title           TEXT NOT NULL,
    scheduled_at    TIMESTAMPTZ NOT NULL,
    attendees       TEXT,
    agenda          TEXT,
    meeting_link    TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Row Level Security ──────────────────────────────────────────
ALTER TABLE meetings             ENABLE ROW LEVEL SECURITY;
ALTER TABLE action_items         ENABLE ROW LEVEL SECURITY;
ALTER TABLE meeting_buckets      ENABLE ROW LEVEL SECURITY;
ALTER TABLE participants         ENABLE ROW LEVEL SECURITY;
ALTER TABLE decisions            ENABLE ROW LEVEL SECURITY;
ALTER TABLE follow_up_questions  ENABLE ROW LEVEL SECURITY;
ALTER TABLE upcoming_meetings    ENABLE ROW LEVEL SECURITY;

-- Users can only see their own data
CREATE POLICY "own meetings"   ON meetings            FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "own actions"    ON action_items        FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "own buckets"    ON meeting_buckets     FOR ALL USING (
    meeting_id IN (SELECT id FROM meetings WHERE user_id = auth.uid())
);
CREATE POLICY "own participants" ON participants      FOR ALL USING (
    meeting_id IN (SELECT id FROM meetings WHERE user_id = auth.uid())
);
CREATE POLICY "own decisions"  ON decisions           FOR ALL USING (
    meeting_id IN (SELECT id FROM meetings WHERE user_id = auth.uid())
);
CREATE POLICY "own followups"  ON follow_up_questions FOR ALL USING (
    meeting_id IN (SELECT id FROM meetings WHERE user_id = auth.uid())
);
CREATE POLICY "own upcoming"   ON upcoming_meetings   FOR ALL USING (auth.uid() = user_id);

-- ── Storage bucket ──────────────────────────────────────────────
-- Run in Supabase Storage UI: create a bucket called "meetings" (private)
-- Or via SQL:
INSERT INTO storage.buckets (id, name, public)
VALUES ('meetings', 'meetings', false)
ON CONFLICT DO NOTHING;

CREATE POLICY "own audio files" ON storage.objects
    FOR ALL USING (
        bucket_id = 'meetings' AND
        (storage.foldername(name))[1] = auth.uid()::text
    );

-- ── Indexes ─────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_meetings_user_id    ON meetings(user_id);
CREATE INDEX IF NOT EXISTS idx_meetings_status     ON meetings(status);
CREATE INDEX IF NOT EXISTS idx_meetings_created_at ON meetings(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_action_items_user   ON action_items(user_id);
CREATE INDEX IF NOT EXISTS idx_action_items_status ON action_items(status);
CREATE INDEX IF NOT EXISTS idx_upcoming_scheduled  ON upcoming_meetings(scheduled_at);
