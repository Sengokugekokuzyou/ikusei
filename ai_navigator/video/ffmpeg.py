"""FFmpeg discovery + capability check.

Prefers a full build (libx264/aac/subtitles). The `imageio-ffmpeg` pip package
ships one for free; the Playwright-bundled ffmpeg is webm/vp8-only and cannot
mux audio, so it does not qualify as "full".
"""

from __future__ import annotations

import functools
import shutil
import subprocess


def find_ffmpeg(override: str = "") -> str | None:
    if override:
        return override
    # A full static build bundled by imageio-ffmpeg (free).
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        pass
    for name in ("ffmpeg",):
        found = shutil.which(name)
        if found:
            return found
    return None


@functools.lru_cache(maxsize=8)
def ffmpeg_has_full_support(exe: str) -> bool:
    """True if this ffmpeg can encode H.264 + AAC and burn subtitles."""
    try:
        enc = subprocess.run([exe, "-hide_banner", "-encoders"],
                             capture_output=True, text=True, timeout=20).stdout
        filt = subprocess.run([exe, "-hide_banner", "-filters"],
                              capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return False
    return ("libx264" in enc) and ("aac" in enc) and ("subtitles" in filt)
