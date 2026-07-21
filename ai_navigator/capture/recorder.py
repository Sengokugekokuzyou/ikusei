"""Playwright capture recorder (spec §5-6).

Records a page to webm with the bundled Chromium, drives scripted actions, and
overlays a visible cursor + click ripple (§5 "cursor highlight") since headless
Chromium draws no pointer. Converts the webm to a 1280×720 H.264 mp4 so the
video builder can splice it in.
"""

from __future__ import annotations

import glob
import subprocess
from pathlib import Path

from ..htmlrender import find_chrome
from ..schemas import CaptureAsset, CaptureRecipe
from ..video.ffmpeg import ffmpeg_has_full_support, find_ffmpeg

# Injected before any page script: a cursor dot that follows the mouse and a
# ripple on click, so the recording shows where the "user" is acting.
_CURSOR_JS = r"""
() => {
  const dot = document.createElement('div');
  dot.style.cssText = 'position:fixed;z-index:2147483647;width:22px;height:22px;'
    + 'margin:-11px 0 0 -11px;border-radius:50%;background:rgba(245,158,11,.9);'
    + 'box-shadow:0 0 0 4px rgba(245,158,11,.35);pointer-events:none;left:-50px;top:-50px;'
    + 'transition:left .05s linear,top .05s linear';
  const add = () => document.body && document.body.appendChild(dot);
  if (document.body) add(); else addEventListener('DOMContentLoaded', add);
  addEventListener('mousemove', e => { dot.style.left = e.clientX+'px'; dot.style.top = e.clientY+'px'; }, true);
  addEventListener('mousedown', e => {
    const r = document.createElement('div');
    r.style.cssText = 'position:fixed;z-index:2147483646;left:'+e.clientX+'px;top:'+e.clientY+'px;'
      + 'width:10px;height:10px;margin:-5px 0 0 -5px;border-radius:50%;border:3px solid rgba(245,158,11,.9);'
      + 'pointer-events:none;animation:ainavR .5s ease-out forwards';
    document.body.appendChild(r); setTimeout(()=>r.remove(), 520);
  }, true);
  const st = document.createElement('style');
  st.textContent = '@keyframes ainavR{to{width:70px;height:70px;margin:-35px 0 0 -35px;opacity:0}}';
  document.head.appendChild(st);
}
"""


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401
        return True
    except ImportError:
        return False


class CaptureRecorder:
    def __init__(self, chrome_path: str = "", ffmpeg_path: str = "") -> None:
        self._chrome = find_chrome(chrome_path)
        self._ffmpeg = find_ffmpeg(ffmpeg_path)

    def available(self) -> tuple[bool, str]:
        if not playwright_available():
            return False, "playwrightが未導入です。`pip install playwright` で導入できます。"
        if not self._chrome:
            return False, "録画用のChromiumが見つかりません。"
        if not self._ffmpeg or not ffmpeg_has_full_support(self._ffmpeg):
            return False, "webm→mp4変換にフルffmpegが必要です（pip install imageio-ffmpeg）。"
        return True, ""

    def record(self, recipe: CaptureRecipe, out_dir: Path, created_at: str) -> CaptureAsset:
        ok, reason = self.available()
        if not ok:
            raise RuntimeError(reason)
        from playwright.sync_api import sync_playwright

        vid_dir = out_dir / "capture_raw"
        vid_dir.mkdir(parents=True, exist_ok=True)
        notes: list[str] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True, executable_path=self._chrome, args=["--no-sandbox"]
            )
            context = browser.new_context(
                viewport={"width": recipe.viewport_w, "height": recipe.viewport_h},
                record_video_dir=str(vid_dir),
                record_video_size={"width": recipe.viewport_w, "height": recipe.viewport_h},
            )
            context.add_init_script(_CURSOR_JS)
            page = context.new_page()
            if recipe.url:
                page.goto(recipe.url)
            for act in recipe.actions:
                try:
                    self._run_action(page, act)
                except Exception as exc:  # keep recording even if one action fails
                    notes.append(f"action {act.kind} failed: {exc}")
            page.wait_for_timeout(recipe.settle_ms)
            context.close()  # finalizes the webm
            browser.close()

        webms = sorted(vid_dir.glob("*.webm"), key=lambda f: f.stat().st_mtime)
        if not webms:
            raise RuntimeError("録画webmが生成されませんでした。")
        webm = webms[-1]

        rel = f"frames/capture_{recipe.name}.mp4"
        duration = self._convert(webm, out_dir / rel, recipe.viewport_w, recipe.viewport_h)
        return CaptureAsset(
            asset_id=f"cap_{recipe.name}",
            recipe=recipe.name,
            created_at=created_at,
            source_url=recipe.url,
            video_path=rel,
            duration=duration,
            scene_id=recipe.scene_id,
            section=recipe.section,
            is_real_service=recipe.is_real_service,
            note="; ".join(notes),
        )

    def _run_action(self, page, act) -> None:
        k = act.kind
        if k == "goto":
            page.goto(act.url or act.text)
        elif k == "wait":
            page.wait_for_timeout(act.ms or 500)
        elif k == "type":
            if act.selector:
                page.type(act.selector, act.text, delay=55)
            else:
                page.keyboard.type(act.text, delay=55)
        elif k == "click":
            if act.selector:
                box = page.locator(act.selector).first.bounding_box()
                if box:
                    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2, steps=12)
                page.locator(act.selector).first.click()
            else:
                page.mouse.move(act.x, act.y, steps=12)
                page.mouse.click(act.x, act.y)
        elif k == "move":
            page.mouse.move(act.x, act.y, steps=act.ms // 20 if act.ms else 20)
        elif k == "scroll":
            page.mouse.wheel(0, act.y)
        elif k == "highlight" and act.selector:
            page.eval_on_selector(
                act.selector,
                "el => { el.style.outline='4px solid #f59e0b'; el.style.transition='outline .2s'; }",
            )

    def _convert(self, webm: Path, out_path: Path, w: int, h: int) -> float:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        vf = (f"scale={w}:{h}:force_original_aspect_ratio=decrease,"
              f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,format=yuv420p")
        cmd = [
            self._ffmpeg, "-y", "-i", str(webm), "-vf", vf,
            "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p",
            "-an", "-r", "30", str(out_path),
        ]
        subprocess.run(cmd, capture_output=True, text=True)
        if not out_path.exists():
            raise RuntimeError("webm→mp4変換に失敗しました。")
        probe = subprocess.run([self._ffmpeg, "-i", str(out_path)], capture_output=True, text=True).stderr
        try:
            ts = probe.split("Duration:")[1].split(",")[0].strip()
            hh, mm, ss = ts.split(":")
            return round(int(hh) * 3600 + int(mm) * 60 + float(ss), 3)
        except Exception:
            return 0.0
