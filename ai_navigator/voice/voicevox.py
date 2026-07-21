"""VOICEVOX adapter (spec §7).

Talks to a running VOICEVOX engine over HTTP (default http://127.0.0.1:50021).
Uses stdlib urllib so no extra dependency. Only used when the engine is up and
config selects it; otherwise the mock adapter is used.
"""

from __future__ import annotations

import contextlib
import json
import urllib.parse
import urllib.request
import wave
from pathlib import Path

from .base import VoiceAdapter


class VoicevoxAdapter(VoiceAdapter):
    name = "voicevox"

    def __init__(self, endpoint: str = "http://127.0.0.1:50021", speaker: int = 3) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._speaker = speaker

    def _post(self, path: str, params: dict, body: bytes | None = None) -> bytes:
        url = f"{self._endpoint}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, data=body, method="POST")
        if body is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read()

    def synthesize(self, text: str, *, speed: float, out_path: Path) -> float:
        query = json.loads(self._post("/audio_query", {"text": text, "speaker": self._speaker}))
        query["speedScale"] = speed
        audio = self._post(
            "/synthesis",
            {"speaker": self._speaker},
            body=json.dumps(query).encode("utf-8"),
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(audio)
        # Measure the real duration from the returned WAV.
        with contextlib.closing(wave.open(str(out_path), "rb")) as wf:
            return round(wf.getnframes() / float(wf.getframerate()), 3)
