"""
Action Items Agent
──────────────────
Extracts every task, commitment, and follow-up from the transcript
with owner, deadline, and priority. Runs in parallel with other agents.
"""

from agents.base import BaseAgent


class ActionItemsAgent(BaseAgent):

    SYSTEM = """You are a meticulous action item extractor. Your only job is to find
    every task, commitment, and follow-up mentioned in a meeting transcript.
    Be thorough — err on the side of capturing more rather than fewer.
    Return ONLY a JSON array."""

    async def process(self, transcript: str) -> list[dict]:
        """
        Returns:
            [{ item, owner, deadline, priority }]
        """
        prompt = f"""Extract ALL action items, tasks, and commitments from this transcript.
For each one return:
{{
  "item": "clear description of what needs to be done",
  "owner": "person responsible (or TBD if unclear)",
  "deadline": "specific date or timeframe if mentioned, else Not specified",
  "priority": "High | Medium | Low  (infer from context — urgency, blockers, revenue impact)"
}}

Return a JSON array. If no action items exist, return [].

TRANSCRIPT:
{transcript}"""

        result = await self._call_json(prompt, max_tokens=2048)
        return result if isinstance(result, list) else []
