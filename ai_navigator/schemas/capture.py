"""Browser capture schemas (spec §5-6 recording, §55 asset metadata).

Records real on-screen operation footage with Playwright. IMPORTANT (§6/§49):
capture real services only from a session you are authorised to use; never
impersonate a service with a generated/fake UI. The bundled demo recipe records
a clearly-labelled *placeholder* page, not any real product.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CaptureAction:
    kind: str                 # goto | wait | type | click | move | scroll | highlight
    selector: str = ""
    text: str = ""
    x: int = 0
    y: int = 0
    ms: int = 0
    url: str = ""


@dataclass
class CaptureRecipe:
    name: str
    url: str = ""             # http(s) or file:// (local placeholder)
    section: str = "real_demo"  # storyboard section this capture illustrates
    scene_id: int = 0         # 0 = attach to the first matching-section scene
    viewport_w: int = 1280
    viewport_h: int = 720
    settle_ms: int = 800
    actions: list[CaptureAction] = field(default_factory=list)
    # True only for footage of a real, authorised service (never a fake UI).
    is_real_service: bool = False


@dataclass
class CaptureAsset:
    """Recorded clip + provenance (spec §55)."""

    asset_id: str
    recipe: str
    created_at: str = ""
    source_url: str = ""
    video_path: str = ""      # relative path to the converted mp4
    duration: float = 0.0
    scene_id: int = 0
    section: str = "real_demo"
    is_real_service: bool = False
    used_video_ids: list[str] = field(default_factory=list)
    reuse_count: int = 0
    note: str = ""


@dataclass
class CaptureManifest:
    topic: str
    produced_at: str
    assets: list[CaptureAsset] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
