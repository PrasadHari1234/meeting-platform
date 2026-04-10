"""
Orchestrator Agent
──────────────────
The brain of the system. Coordinates the full meeting pipeline:

  Audio
    └─► [TranscriptionAgent]  (sequential — others depend on transcript)
          └─► [SummaryAgent]       ┐
              [ActionItemsAgent]   ├── all run in PARALLEL via asyncio.gather()
              [BucketingAgent]     ┘
                    └─► [StorageAgent]  saves everything to Supabase
                          └─► [NotificationAgent]  sends email (optional)
"""

import asyncio
from datetime import datetime

from agents.transcription import TranscriptionAgent
from agents.summary       import SummaryAgent
from agents.action_items  import ActionItemsAgent
from agents.bucketing     import BucketingAgent
from agents.notification  import NotificationAgent
import db.client as db
from config import settings


class OrchestratorAgent:

    def __init__(self):
        self.transcription = TranscriptionAgent()
        self.summary       = SummaryAgent()
        self.action_items  = ActionItemsAgent()
        self.bucketing     = BucketingAgent()
        self.notification  = NotificationAgent()

    async def run(
        self,
        meeting_id:     str,
        user_id:        str,
        audio_source:   str | bytes,
        filename:       str = "audio.webm",
        extra_buckets:  list[str] = None,
        notify_email:   str = None,
        app_url:        str = None,
    ) -> dict:
        """
        Full pipeline. Updates meeting status in DB at each stage.
        Returns the completed meeting dict.
        """
        try:
            # ── [1] Transcribe ────────────────────────────────────────────
            db.update_meeting(meeting_id, status="processing",
                              updated_at=datetime.utcnow().isoformat())
            print(f"[Orchestrator] Meeting {meeting_id}: transcribing …")

            transcript = await self.transcription.process(audio_source, filename)

            if not transcript.strip():
                raise ValueError("Empty transcript — no speech detected")

            db.update_meeting(meeting_id, transcript=transcript)
            print(f"[Orchestrator] Transcript ready: {len(transcript)} chars")

            # ── [2] Analyse in parallel ───────────────────────────────────
            print(f"[Orchestrator] Running 3 analysis agents in parallel …")
            summary_data, action_items_data, buckets_data = await asyncio.gather(
                self.summary.process(transcript),
                self.action_items.process(transcript),
                self.bucketing.process(transcript, extra_buckets),
            )

            # ── [3] Persist ───────────────────────────────────────────────
            print(f"[Orchestrator] Saving to database …")
            db.update_meeting(
                meeting_id,
                title        = summary_data.get("title", "Meeting"),
                meeting_type = summary_data.get("meeting_type"),
                sentiment    = summary_data.get("sentiment"),
                summary      = summary_data.get("summary"),
                status       = "completed",
            )

            analysis = {
                **summary_data,
                "action_items":  action_items_data,
                "buckets":       buckets_data,
            }
            db.save_action_items(meeting_id, user_id, action_items_data)
            db.save_meeting_details(meeting_id, analysis)

            # ── [4] Fetch full record ─────────────────────────────────────
            meeting = db.get_meeting_full(meeting_id)

            # ── [5] Notify (optional) ─────────────────────────────────────
            if notify_email and app_url:
                await self.notification.process(meeting, notify_email, app_url)

            print(f"[Orchestrator] ✔ Meeting {meeting_id} complete — "
                  f"{len(action_items_data)} actions, {len(buckets_data)} buckets")
            return meeting

        except Exception as exc:
            print(f"[Orchestrator] ✖ Meeting {meeting_id} failed: {exc}")
            db.update_meeting(meeting_id, status="failed", error_message=str(exc))
            raise
