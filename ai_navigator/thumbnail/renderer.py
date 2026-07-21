"""Thumbnail renderer — HTML/CSS to PNG via headless Chromium (spec §54, §61).

Free and key-less: composes the thumbnail as HTML (Japanese via the installed
IPAGothic font) and screenshots it at 1280×720. Rendering is delegated to the
shared ``htmlrender`` module.
"""

from __future__ import annotations

from pathlib import Path

from ..htmlrender import find_chrome, render_html_to_png
from ..schemas import ThumbnailSpec

WIDTH, HEIGHT = 1280, 720

# JP-capable stack: IPAGothic is installed; WenQuanYi as CJK fallback.
_FONT = "'IPAPGothic','IPAGothic','WenQuanYi Zen Hei','Noto Sans CJK JP',sans-serif"

__all__ = ["ChromiumThumbnailRenderer", "build_html", "find_chrome"]


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_html(spec: ThumbnailSpec) -> str:
    subjects = spec.subjects or []
    grad = f"linear-gradient(135deg,{spec.bg_from},{spec.bg_to})"
    shadow = "0 6px 24px rgba(0,0,0,.55)"

    if spec.layout == "split" and len(subjects) >= 2:
        head = "" if spec.text.strip().upper() in ("", "VS") else f'<div class="head">{_esc(spec.text)}</div>'
        body = f"""
        {head}
        <div class="split">
          <div class="panel">{_esc(subjects[0])}</div>
          <div class="vs">VS</div>
          <div class="panel">{_esc(subjects[1])}</div>
        </div>"""
    elif spec.layout == "recommend":
        subj = subjects[0] if subjects else ""
        body = f"""
        <div class="big">{_esc(spec.text)}</div>
        <div class="pill">{_esc(subj)}</div>"""
    else:  # question
        pills = "".join(f'<span class="pill">{_esc(s)}</span>' for s in subjects[:3])
        body = f"""
        <div class="big">{_esc(spec.text)}</div>
        <div class="pills">{pills}</div>"""

    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
    html,body{{margin:0;padding:0;background:{grad};overflow:hidden}}
    .canvas{{position:absolute;top:0;left:0;width:{WIDTH}px;height:{HEIGHT}px;background:{grad};
      font-family:{_FONT};color:#fff;box-sizing:border-box;padding:64px;
      display:flex;flex-direction:column;align-items:center;justify-content:center;
      gap:36px;text-align:center;overflow:hidden}}
    .head{{font-size:96px;font-weight:900;text-shadow:{shadow};letter-spacing:2px}}
    .big{{font-size:150px;font-weight:900;line-height:1.05;text-shadow:{shadow}}}
    .split{{display:flex;align-items:center;justify-content:center;gap:40px;width:100%}}
    .panel{{flex:1;background:rgba(255,255,255,.10);border:6px solid {spec.accent};
      border-radius:28px;padding:44px 24px;font-size:76px;font-weight:800;
      text-shadow:{shadow};max-width:460px;word-break:break-word}}
    .vs{{font-size:120px;font-weight:900;color:{spec.accent};text-shadow:{shadow}}}
    .pills{{display:flex;gap:28px;flex-wrap:wrap;justify-content:center}}
    .pill{{background:{spec.accent};color:#111;font-size:64px;font-weight:800;
      border-radius:999px;padding:16px 44px;text-shadow:none}}
    </style></head><body><div class="canvas">{body}</div></body></html>"""


class ChromiumThumbnailRenderer:
    name = "chromium"

    def __init__(self, chrome_path: str = "") -> None:
        self._chrome_path = chrome_path
        self._chrome = find_chrome(chrome_path)

    @property
    def available(self) -> bool:
        return self._chrome is not None

    def render(self, spec: ThumbnailSpec, out_path: Path) -> tuple[int, int]:
        return render_html_to_png(
            build_html(spec), out_path, width=WIDTH, height=HEIGHT, chrome_path=self._chrome_path
        )
