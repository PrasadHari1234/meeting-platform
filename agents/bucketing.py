"""
Bucketing Agent
───────────────
Categorises meeting discussion into predefined work areas,
and auto-creates new buckets for topics outside those areas.
Runs in parallel with other analysis agents.
"""

from agents.base import BaseAgent
from config import settings


class BucketingAgent(BaseAgent):

    SYSTEM = """You are a meeting content organiser. Your job is to categorise
    everything discussed in a meeting into clear work buckets. Return ONLY valid JSON."""

    async def process(self, transcript: str, extra_buckets: list[str] = None) -> list[dict]:
        """
        Args:
            transcript:     meeting text
            extra_buckets:  user-defined additional buckets
        Returns:
            [{ name, is_new, items: [{topic, detail}] }]
        """
        buckets = settings.DEFAULT_BUCKETS.copy()
        if extra_buckets:
            buckets.extend(extra_buckets)

        prompt = f"""Organise the meeting content into work buckets.

Standard buckets to always check: {', '.join(buckets)}

Rules:
- Only include buckets that have actual content from this meeting
- Add NEW buckets (marked is_new: true) for topics clearly outside the standard list
- Each item should have a short topic headline and a detail sentence

Return a JSON array:
[
  {{
    "name": "bucket name",
    "is_new": false,
    "items": [
      {{"topic": "Short headline", "detail": "What was discussed about this topic"}}
    ]
  }}
]

If nothing fits a bucket, omit it entirely.

TRANSCRIPT:
{transcript}"""

        result = await self._call_json(prompt, max_tokens=2048)
        return result if isinstance(result, list) else []
