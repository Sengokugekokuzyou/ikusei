"""A safe, self-contained demo capture (spec §49-compliant).

Writes a clearly-labelled *placeholder* page and a recipe that types a prompt
and clicks a button, so the recorder produces real footage without pretending
to be any real AI product. Replace this with a recipe pointing at a real,
authorised service (run locally, logged in) for genuine operation footage.
"""

from __future__ import annotations

from pathlib import Path

from ..schemas import CaptureAction, CaptureRecipe

_FONT = "'IPAPGothic','IPAGothic','WenQuanYi Zen Hei',sans-serif"

_PAGE = f"""<!doctype html><html><head><meta charset="utf-8"><style>
  html,body{{margin:0;font-family:{_FONT};background:#0b1220;color:#e5e7eb}}
  .banner{{background:#f59e0b;color:#111;font-weight:800;padding:10px 20px;font-size:18px}}
  .wrap{{padding:36px;max-width:1120px;margin:0 auto}}
  h1{{font-size:34px;margin:8px 0 24px}}
  textarea{{width:100%;height:150px;font-size:22px;padding:18px;border-radius:12px;
    border:2px solid #334155;background:#0f172a;color:#e5e7eb;box-sizing:border-box}}
  button{{margin-top:18px;font-size:22px;font-weight:800;padding:14px 40px;border:0;
    border-radius:999px;background:#2563eb;color:#fff;cursor:pointer}}
  #out{{margin-top:26px;min-height:150px;background:#0f172a;border:2px solid #334155;
    border-radius:12px;padding:22px;font-size:22px;white-space:pre-wrap;line-height:1.7}}
</style></head><body>
  <div class="banner">収録デモ（プレースホルダ）— 実在サービスの画面ではありません</div>
  <div class="wrap">
    <h1>プロンプトを入力して実行するデモ</h1>
    <textarea id="prompt" placeholder="ここにプロンプトを入力…"></textarea>
    <button id="run">実行</button>
    <div id="out"></div>
  </div>
  <script>
    document.getElementById('run').addEventListener('click', () => {{
      const out = document.getElementById('out');
      const text = '入力を受け取りました。ここに結果が表示されます（デモ表示）。';
      out.textContent = '';
      let i = 0;
      const t = setInterval(() => {{ out.textContent += text[i++] || ''; if (i > text.length) clearInterval(t); }}, 35);
    }});
  </script>
</body></html>"""


def placeholder_recipe(out_dir: Path, scene_id: int = 0) -> CaptureRecipe:
    src = out_dir / "capture_src"
    src.mkdir(parents=True, exist_ok=True)
    page = src / "demo.html"
    page.write_text(_PAGE, encoding="utf-8")
    return CaptureRecipe(
        name="demo",
        url=page.resolve().as_uri(),
        section="real_demo",
        scene_id=scene_id,
        settle_ms=1200,
        is_real_service=False,
        actions=[
            CaptureAction(kind="wait", ms=600),
            CaptureAction(kind="type", selector="#prompt",
                          text="初心者向けにToDoアプリを作って"),
            CaptureAction(kind="wait", ms=500),
            CaptureAction(kind="click", selector="#run"),
            CaptureAction(kind="wait", ms=1800),
            CaptureAction(kind="highlight", selector="#out"),
            CaptureAction(kind="wait", ms=700),
        ],
    )
