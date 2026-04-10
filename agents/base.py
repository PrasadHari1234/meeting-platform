"""Base agent class — all agents inherit from this."""

import json
import anthropic
from config import settings

_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)


class BaseAgent:
    """
    Each agent has:
      - A focused system prompt
      - A single process() method that calls Claude
      - Returns typed, structured output
    """
    SYSTEM: str = ""
    MODEL:  str = settings.CLAUDE_MODEL

    async def _call(self, prompt: str, max_tokens: int = 2048) -> str:
        msg = await _client.messages.create(
            model=self.MODEL,
            max_tokens=max_tokens,
            system=self.SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    async def _call_json(self, prompt: str, max_tokens: int = 2048) -> dict | list:
        """Call Claude and parse JSON response."""
        raw = await self._call(prompt, max_tokens)
        # Strip accidental markdown fences
        if raw.startswith("```"):
            lines = raw.split("\n")
            end = -1 if lines[-1].strip() == "```" else len(lines)
            raw = "\n".join(lines[1:end])
        return json.loads(raw.strip())
