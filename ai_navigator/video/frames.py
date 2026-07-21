"""Scene frame renderer (spec §25 components as still frames).

Each storyboard scene becomes one 1280×720 PNG composed in HTML/CSS (the §25
component look), rendered via the shared Chromium renderer. FFmpeg then adds
camera motion (Ken Burns) and the narration/subtitles, so the frame itself is a
clean static composition — the words are spoken and shown as burned subtitles.
"""

from __future__ import annotations

from pathlib import Path

from ..htmlrender import render_html_to_png
from ..schemas import Scene, Storyboard

W, H = 1280, 720
_FONT = "'IPAPGothic','IPAGothic','WenQuanYi Zen Hei','Noto Sans CJK JP',sans-serif"
_BG = "linear-gradient(135deg,#0f172a,#1e3a8a)"
_ACCENT = "#f59e0b"
_SHADOW = "0 6px 24px rgba(0,0,0,.55)"

_SECTION_LABEL = {
    "opening": "はじめに",
    "beginner_explanation": "そもそも何？",
    "what_can_it_do": "できること",
    "real_demo": "実演",
    "comparison": "比較",
    "recommended_for": "向いている人",
    "not_recommended_for": "向いていない人",
    "final_decision": "結論",
}


def _esc(t: str) -> str:
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _short(t: str, n: int = 26) -> str:
    t = t.strip().lstrip("・（(").rstrip("。")
    return t if len(t) <= n else t[: n - 1] + "…"


def build_scene_html(scene: Scene, working_title: str) -> str:
    label = _SECTION_LABEL.get(scene.section, "")
    p = scene.params or {}
    body = ""

    if scene.section == "comparison" and p.get("left") and p.get("right"):
        hl = p.get("highlight")
        lcls = "panel win" if hl == "left" else "panel"
        rcls = "panel win" if hl == "right" else "panel"
        body = f"""<div class="split">
          <div class="{lcls}">{_esc(p['left'])}</div>
          <div class="vs">VS</div>
          <div class="{rcls}">{_esc(p['right'])}</div></div>"""
    elif scene.section == "opening":
        tools = p.get("tools") or []
        pills = "".join(f'<span class="pill">{_esc(t)}</span>' for t in tools[:3])
        body = f'<div class="title">{_esc(_short(working_title, 30))}</div><div class="pills">{pills}</div>'
    elif scene.section in ("what_can_it_do", "recommended_for", "not_recommended_for"):
        item = p.get("item") or _short(scene.voice)
        mark = "✕" if p.get("mode") == "cons" else "✓"
        color = "#f87171" if p.get("mode") == "cons" else "#34d399"
        body = f'<div class="feature"><span class="chk" style="color:{color}">{mark}</span>{_esc(item)}</div>'
    elif scene.section == "final_decision":
        cls = "price" if scene.component == "PriceCard" else "final"
        body = f'<div class="{cls}">{_esc(_short(scene.voice, 34))}</div>'
    elif scene.section == "real_demo":
        body = ('<div class="browser"><div class="bar"><i></i><i></i><i></i></div>'
                '<div class="screen">実際の操作画面（収録予定）</div></div>')
    else:  # beginner_explanation / default
        body = f'<div class="tip">{_esc(_short(scene.voice, 34))}</div>'

    chip = f'<div class="chip">{_esc(label)}</div>' if label else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>
    html,body{{margin:0;padding:0;background:{_BG};overflow:hidden}}
    .canvas{{position:absolute;top:0;left:0;width:{W}px;height:{H}px;background:{_BG};
      font-family:{_FONT};color:#fff;box-sizing:border-box;padding:72px;
      display:flex;flex-direction:column;align-items:center;justify-content:center;gap:44px;text-align:center}}
    .chip{{position:absolute;top:48px;left:64px;background:{_ACCENT};color:#111;
      font-size:34px;font-weight:800;border-radius:999px;padding:10px 34px}}
    .title{{font-size:88px;font-weight:900;line-height:1.1;text-shadow:{_SHADOW};max-width:1050px}}
    .pills{{display:flex;gap:28px;flex-wrap:wrap;justify-content:center}}
    .pill{{background:rgba(255,255,255,.14);border:4px solid {_ACCENT};font-size:52px;
      font-weight:800;border-radius:999px;padding:14px 40px}}
    .split{{display:flex;align-items:center;justify-content:center;gap:44px;width:100%}}
    .panel{{flex:1;background:rgba(255,255,255,.10);border:6px solid rgba(255,255,255,.35);
      border-radius:28px;padding:52px 24px;font-size:72px;font-weight:800;
      text-shadow:{_SHADOW};max-width:460px;word-break:break-word}}
    .panel.win{{border-color:{_ACCENT};background:rgba(245,158,11,.16)}}
    .vs{{font-size:110px;font-weight:900;color:{_ACCENT};text-shadow:{_SHADOW}}}
    .feature{{font-size:72px;font-weight:800;line-height:1.25;text-shadow:{_SHADOW};
      max-width:1050px;display:flex;align-items:center;gap:32px}}
    .chk{{font-size:96px;font-weight:900}}
    .final{{font-size:76px;font-weight:900;line-height:1.25;text-shadow:{_SHADOW};max-width:1050px}}
    .price{{font-size:70px;font-weight:800;line-height:1.25;text-shadow:{_SHADOW};max-width:1050px;
      border:6px solid {_ACCENT};border-radius:28px;padding:44px 56px}}
    .tip{{font-size:74px;font-weight:800;line-height:1.3;text-shadow:{_SHADOW};max-width:1050px}}
    .browser{{width:1000px;background:#0b1220;border-radius:18px;overflow:hidden;
      border:2px solid rgba(255,255,255,.2)}}
    .bar{{background:#1f2937;padding:18px 24px;display:flex;gap:16px}}
    .bar i{{width:22px;height:22px;border-radius:50%;background:#4b5563;display:block}}
    .screen{{padding:120px 24px;font-size:54px;color:#93c5fd;font-weight:700}}
    </style></head><body><div class="canvas">{chip}{body}</div></body></html>"""


class SceneFrameRenderer:
    def __init__(self, chrome_path: str = "") -> None:
        self._chrome_path = chrome_path

    def render_all(self, storyboard: Storyboard, out_dir: Path) -> list[tuple[str, float]]:
        frames: list[tuple[str, float]] = []
        for sc in storyboard.scenes:
            rel = f"frames/scene_{sc.scene_id:03d}.png"
            # Render uncropped (fast); ffmpeg crops the top W×H per segment.
            render_html_to_png(
                build_scene_html(sc, storyboard.working_title),
                out_dir / rel, width=W, height=H, chrome_path=self._chrome_path, crop=False,
            )
            frames.append((rel, sc.duration))
        return frames
