"""
Summary Agent
─────────────
Generates a concise executive summary + meeting metadata from a transcript.
Runs in parallel with ActionItemsAgent and BucketingAgent.
"""

from agents.base import BaseAgent


class SummaryAgent(BaseAgent):

    SYSTEM = """You are an expert meeting analyst. Your job is to produce a concise,
    accurate summary of what happened in a meeting. Return ONLY valid JSON — no prose."""

    async def process(self, transcript: str) -> dict:
        """
        Returns:
            {
              title, meeting_type, sentiment, summary,
              participants_mentioned, decisions_made, follow_up_questions
            }
        """
        prompt = f"""Analyze this meeting transcript and return JSON:
{{
  "title": "short descriptive title",
  "meeting_type": "Sprint Planning | Status Update | Decision Meeting | Brainstorm | 1:1 | Other",
  "sentiment": "Positive | Neutral | Tense | Mixed",
  "summary": "2-4 sentence executive summary of outcomes",
  "participants_mentioned": ["name1", "name2"],
  "decisions_made": ["decision1"],
  "follow_up_questions": ["unanswered question 1"]
}}

TRANSCRIPT:
{transcript}"""

        return await self._call_json(prompt, max_tokens=1024)
