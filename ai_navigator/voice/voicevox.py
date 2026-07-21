"""VOICEVOX adapter (spec §7) — real Japanese narration.

Talks to a running VOICEVOX engine over HTTP (default http://127.0.0.1:50021),
using stdlib urllib (no extra dependency). Selected via config
``voice.adapter = "voicevox"``.

Running the engine locally (free):
    docker run --rm -p 50021:50021 voicevox/voicevox_engine:cpu-ubuntu20.04-latest
or launch the VOICEVOX desktop app (it serves the same API on :50021).
"""

from __future__ import annotations

import contextlib
import json
import urllib.error
import urllib.parse
import urllib.request
import wave
from pathlib import Path

from .base import VoiceAdapter


class VoicevoxUnavailable(RuntimeError):
    pass


class VoicevoxAdapter(VoiceAdapter):
    name = "voicevox"

    def __init__(self, endpoint: str = "http://127.0.0.1:50021", speaker: int = 3) -> None:
        self._endpoint = (endpoint or "http://127.0.0.1:50021").rstrip("/")
        self._speaker = int(speaker)
        self._check_reachable()

    def _check_reachable(self) -> None:
        try:
            with urllib.request.urlopen(f"{self._endpoint}/version", timeout=5) as resp:
                resp.read()
        except (urllib.error.URLError, OSError) as exc:
            raise VoicevoxUnavailable(
                f"VOICEVOXエンジンに接続できません（{self._endpoint}）。"
                "エンジンを起動してください: "
                "`docker run --rm -p 50021:50021 "
                "voicevox/voicevox_engine:cpu-ubuntu20.04-latest`。詳細: " + str(exc)
            ) from exc

    def _post(self, path: str, params: dict, body: bytes | None = None) -> bytes:
        url = f"{self._endpoint}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, data=body, method="POST")
        if body is not None:
            req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.read()

    def synthesize(self, text: str, *, speed: float, out_path: Path) -> float:
        query = json.loads(self._post("/audio_query", {"text": text, "speaker": self._speaker}))
        query["speedScale"] = float(speed)
        audio = self._post(
            "/synthesis", {"speaker": self._speaker},
            body=json.dumps(query).encode("utf-8"),
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(audio)
        with contextlib.closing(wave.open(str(out_path), "rb")) as wf:
            return round(wf.getnframes() / float(wf.getframerate()), 3)
