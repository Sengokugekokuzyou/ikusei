"""Image asset schemas (spec §48 B-roll, §49/§70 sourcing rules, §55 provenance).

Real imagery for scenes, from three lanes:
  - stock   : free commercial-safe photos (Pixabay) — generic B-roll
  - cc       : keyless CC images (Openverse) — needs attribution
  - local   : human-curated files in assets/ (official screenshots/logos, or a
              cited official announcement / X post shown as a quotation)

NEVER used to fake a real product UI (§49); official screens must be real and
attributed. Attribution is collected so a credits list can be produced.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ImageAsset:
    scene_id: int
    role: str = "broll"          # broll | background | concept | logo | quote
    source: str = "local"        # local | pixabay | openverse | wikimedia
    query: str = ""
    file_path: str = ""          # relative path to the downloaded/copied image
    page_url: str = ""           # where it came from (for credits / 出典)
    author: str = ""
    license: str = ""            # e.g. "Pixabay", "CC BY 2.0", "official/quoted"
    attribution_required: bool = False
    # For §32 引用: an on-screen source caption (e.g. "出典: OpenAI 公式発表").
    caption: str = ""
    is_official: bool = False    # a real official screenshot/announcement (quoted)


@dataclass
class ImageManifest:
    topic: str
    produced_at: str
    provider: str = "none"
    assets: list[ImageAsset] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def by_scene(self) -> dict[int, "ImageAsset"]:
        return {a.scene_id: a for a in self.assets if a.file_path}
