"""Image Manager — resolves a real image per selected scene, with provenance.

Resolution order per scene:
  1. Local override  assets/scene_<id>.(jpg|png|webp)  (+ optional .txt = 出典)
     → for official screenshots / quoted announcements / logos you curate.
  2. Configured provider search (pixabay / openverse) → download B-roll.
  3. Otherwise: no image (scene keeps its card).

Every asset records author/license/page so a credits list can be generated.
"""

from __future__ import annotations

import shutil
import urllib.request
from pathlib import Path

from ..schemas import ImageAsset, ImageManifest, Storyboard
from .director import ImageDirector
from .providers import ImageProvider

_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def _download(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "ai-navigator/0.1"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read()
        if not data:
            return False
        dest.write_bytes(data)
        return True
    except Exception:
        return False


class ImageManager:
    def __init__(self, provider: ImageProvider, assets_dir: Path) -> None:
        self._provider = provider
        self._assets = assets_dir

    def _local_override(self, scene_id: int) -> tuple[Path, str] | None:
        for ext in _EXTS:
            p = self._assets / f"scene_{scene_id}{ext}"
            if p.exists():
                cap = ""
                side = self._assets / f"scene_{scene_id}.txt"
                if side.exists():
                    cap = side.read_text(encoding="utf-8").strip().splitlines()[0]
                return p, cap
        return None

    def run(self, storyboard: Storyboard, report_dir: Path) -> ImageManifest:
        manifest = ImageManifest(
            topic=storyboard.topic, produced_at=storyboard.produced_at,
            provider=self._provider.name,
        )
        img_dir = report_dir / "images"
        plan = ImageDirector().plan(storyboard)
        for scene_id, role, query in plan:
            local = self._local_override(scene_id)
            if local:
                src, caption = local
                rel = f"images/scene_{scene_id}{src.suffix}"
                img_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, report_dir / rel)
                manifest.assets.append(ImageAsset(
                    scene_id=scene_id, role="quote" if caption else role, source="local",
                    file_path=rel, caption=caption or "",
                    license="official/quoted" if caption else "local",
                    is_official=bool(caption), attribution_required=bool(caption),
                ))
                continue

            # Provider fetch (B-roll). Skips cleanly if no provider / offline.
            try:
                candidates = self._provider.search(query, limit=5)
            except Exception as exc:
                manifest.warnings.append(f"scene {scene_id}: 検索失敗 ({exc})")
                candidates = []
            placed = False
            for cand in candidates:
                rel = f"images/scene_{scene_id}.jpg"
                img_dir.mkdir(parents=True, exist_ok=True)
                if _download(cand["image_url"], report_dir / rel):
                    cap = ""
                    if cand.get("attribution_required"):
                        cap = f"Photo: {cand.get('author','')} / {cand.get('license','')}".strip()
                    manifest.assets.append(ImageAsset(
                        scene_id=scene_id, role=role, source=self._provider.name,
                        query=query, file_path=rel, page_url=cand.get("page_url", ""),
                        author=cand.get("author", ""), license=cand.get("license", ""),
                        attribution_required=bool(cand.get("attribution_required")),
                        caption=cap,
                    ))
                    placed = True
                    break
            if not placed and self._provider.name != "none":
                manifest.warnings.append(f"scene {scene_id}: 画像を取得できませんでした")
        return manifest


def build_credits(manifest: ImageManifest) -> str:
    """A credits block for the YouTube description (§attribution)."""
    lines = ["【画像クレジット / Image credits】"]
    any_credit = False
    for a in manifest.assets:
        if a.source == "pixabay":
            lines.append(f"- Pixabay: {a.author} ({a.page_url})")
            any_credit = True
        elif a.attribution_required:
            lines.append(f"- {a.author} / {a.license} ({a.page_url or a.caption})")
            any_credit = True
        elif a.is_official:
            lines.append(f"- {a.caption}")
            any_credit = True
    if not any_credit:
        lines.append("（クレジット必須の画像はありません）")
    return "\n".join(lines) + "\n"
