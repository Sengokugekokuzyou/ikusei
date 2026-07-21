"""Browser capture stage (spec §5-6, §55) — Playwright screen recording."""

from .recorder import CaptureRecorder, playwright_available
from .demo import placeholder_recipe

__all__ = ["CaptureRecorder", "playwright_available", "placeholder_recipe"]
