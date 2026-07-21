"""Video stage (spec §4-5 Phase 4) — free FFmpeg-based rendering."""

from .ffmpeg import find_ffmpeg, ffmpeg_has_full_support
from .builder import VideoBuilder

__all__ = ["find_ffmpeg", "ffmpeg_has_full_support", "VideoBuilder"]
