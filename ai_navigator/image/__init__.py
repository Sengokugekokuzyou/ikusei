"""Image stage (spec §48 B-roll, §49/§70 sourcing, §55 provenance).

Free, licence-aware real imagery for scenes. Providers:
  - pixabay   : free commercial-safe photos (needs a free API key)
  - openverse : keyless CC images (attribution captured for credits)
  - local     : human-curated files in assets/ (official screenshots/quotes)

Never fabricates a product UI (§49).
"""

from .director import ImageDirector
from .manager import ImageManager
from .providers import build_image_provider

__all__ = ["ImageDirector", "ImageManager", "build_image_provider"]
