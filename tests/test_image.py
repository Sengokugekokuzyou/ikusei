"""Image stage tests. Standalone: `python tests/test_image.py`."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ai_navigator.image import ImageDirector, ImageManager
from ai_navigator.image.manager import build_credits
from ai_navigator.image.providers import (
    NoneProvider,
    OpenverseProvider,
    PixabayProvider,
    build_image_provider,
)
from ai_navigator.htmlrender import _write_png_rgb
from ai_navigator.schemas import Scene, Storyboard


def _storyboard():
    scenes = [
        Scene(scene_id=1, section="opening", duration=4.0, voice="はじめ", visual_type="motion_graphic"),
        Scene(scene_id=2, section="comparison", duration=4.0, voice="比較",
              visual_type="comparison_card", params={"left": "A", "right": "B"}),
        Scene(scene_id=3, section="real_demo", duration=3.0, voice="実演", visual_type="real_capture"),
        Scene(scene_id=4, section="recommended_for", duration=3.0, voice="向いてる", visual_type="motion_graphic"),
    ]
    return Storyboard(topic="t", produced_at="d", working_title="タイトル", scenes=scenes)


def test_director_selects_human_scenes_only():
    plan = ImageDirector().plan(_storyboard())
    ids = {sid for sid, _r, _q in plan}
    assert 1 in ids and 4 in ids       # opening, recommended_for
    assert 2 not in ids                 # comparison keeps its VS card
    assert 3 not in ids                 # real_demo is reserved for real capture (§70)


def test_local_override_with_source_caption():
    tmp = Path(tempfile.mkdtemp(prefix="ainav-img-"))
    assets = tmp / "assets"
    assets.mkdir()
    _write_png_rgb(assets / "scene_1.png", 8, 8, bytes(8 * 8 * 3))
    (assets / "scene_1.txt").write_text("出典: 公式発表", encoding="utf-8")
    report = tmp / "report"
    report.mkdir()

    manifest = ImageManager(NoneProvider(), assets).run(_storyboard(), report)
    a = manifest.by_scene().get(1)
    assert a is not None
    assert a.is_official and a.caption == "出典: 公式発表"
    assert (report / a.file_path).exists()


def test_openverse_parse_attribution():
    data = {"results": [
        {"url": "https://img/x.jpg", "foreign_landing_url": "https://page/x",
         "creator": "Jane", "license": "by", "license_version": "2.0"},
    ]}
    cands = OpenverseProvider.parse(data)
    assert cands[0]["image_url"] == "https://img/x.jpg"
    assert cands[0]["attribution_required"] is True
    assert "CC BY" in cands[0]["license"]


def test_pixabay_parse_no_attribution():
    data = {"hits": [
        {"largeImageURL": "https://img/y.jpg", "pageURL": "https://page/y", "user": "Bob"},
    ]}
    cands = PixabayProvider.parse(data)
    assert cands[0]["image_url"] == "https://img/y.jpg"
    assert cands[0]["attribution_required"] is False


def test_build_credits_lists_required_attribution():
    tmp = Path(tempfile.mkdtemp(prefix="ainav-cred-"))
    assets = tmp / "assets"; assets.mkdir()
    _write_png_rgb(assets / "scene_1.png", 8, 8, bytes(8 * 8 * 3))
    (assets / "scene_1.txt").write_text("出典: 公式X", encoding="utf-8")
    report = tmp / "r"; report.mkdir()
    manifest = ImageManager(NoneProvider(), assets).run(_storyboard(), report)
    text = build_credits(manifest)
    assert "公式X" in text


def test_provider_factory():
    assert build_image_provider("none").name == "none"
    assert build_image_provider("openverse").name == "openverse"
    try:
        build_image_provider("pixabay", api_key="")
        assert False, "pixabay without key should raise"
    except ValueError:
        pass


def test_frame_composites_image():
    from ai_navigator.htmlrender import find_chrome
    if not find_chrome():
        return  # no browser; skip
    from ai_navigator.video.frames import SceneFrameRenderer
    from ai_navigator.schemas import ImageAsset
    tmp = Path(tempfile.mkdtemp(prefix="ainav-comp-"))
    (tmp / "images").mkdir()
    _write_png_rgb(tmp / "images" / "scene_1.png", 64, 64, bytes(64 * 64 * 3))
    sb = _storyboard()
    sb.scenes = [sb.scenes[0]]  # just the opening scene
    imgs = {1: ImageAsset(scene_id=1, file_path="images/scene_1.png", caption="出典: x")}
    frames = SceneFrameRenderer().render_all(sb, tmp, images=imgs)
    assert (tmp / frames[0][0]).exists()


def _run_standalone() -> int:
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except Exception as exc:  # noqa: BLE001
            failed += 1
            print(f"FAIL {fn.__name__}: {exc!r}")
    print(f"\n{len(fns) - failed}/{len(fns)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(_run_standalone())
