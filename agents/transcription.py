"""
Transcription Agent
───────────────────
Converts audio (file path or URL) to text using OpenAI Whisper API.
Runs first in the pipeline — all other agents depend on its output.
"""

import httpx
import tempfile
from pathlib import Path
import openai
from config import settings

_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

SUPPORTED_FORMATS = {".mp3", ".mp4", ".mpeg", ".mpga", ".m4a", ".wav", ".webm", ".ogg"}


class TranscriptionAgent:

    async def process(self, audio_source: str | bytes, filename: str = "audio.webm") -> str:
        """
        Args:
            audio_source: local file path (str), URL (str starting with http), or raw bytes
            filename:     original filename (used to infer format)
        Returns:
            Plain text transcript
        """
        audio_bytes = await self._get_audio_bytes(audio_source)
        return await self._transcribe(audio_bytes, filename)

    async def _get_audio_bytes(self, source: str | bytes) -> bytes:
        if isinstance(source, bytes):
            return source
        if source.startswith("http"):
            async with httpx.AsyncClient() as client:
                resp = await client.get(source, timeout=120)
                resp.raise_for_status()
                return resp.content
        return Path(source).read_bytes()

    async def _transcribe(self, audio_bytes: bytes, filename: str) -> str:
        # Whisper API accepts a file-like tuple: (filename, bytes, content_type)
        ext = Path(filename).suffix.lower() or ".webm"
        mime = {
            ".webm": "audio/webm", ".mp3": "audio/mpeg",
            ".mp4": "audio/mp4",   ".wav": "audio/wav",
            ".m4a": "audio/mp4",   ".ogg": "audio/ogg",
        }.get(ext, "audio/webm")

        response = await _client.audio.transcriptions.create(
            model="whisper-1",
            file=(filename, audio_bytes, mime),
            response_format="text",
        )
        return str(response).strip()
