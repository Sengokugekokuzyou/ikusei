"""Thumbnail renderer — HTML/CSS to PNG via headless Chromium (spec §54, §61).

Free and key-less: composes the thumbnail as HTML (Japanese via the installed
IPAGothic font) and screenshots it at 1280×720 with the bundled Chromium.
"""

from __future__ import annotations

import glob
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

from ..schemas import ThumbnailSpec

WIDTH, HEIGHT = 1280, 720
# Chromium's headless layout viewport is shorter than --window-size height,
# so we render into a taller window and crop the top WIDTH×HEIGHT region.
_RENDER_MARGIN = 220

# JP-capable stack: IPAGothic is installed; WenQuanYi as CJK fallback.
_FONT = "'IPAPGothic','IPAGothic','WenQuanYi Zen Hei','Noto Sans CJK JP',sans-serif"


def find_chrome(override: str = "") -> str | None:
    """Locate a Chromium/Chrome binary (bundled first, then PATH)."""
    if override and Path(override).exists():
        return override
    patterns = [
        "/opt/pw-browsers/chromium-*/chrome-linux/chrome",
        "/opt/pw-browsers/chromium_headless_shell-*/chrome-linux/headless_shell",
    ]
    for pat in patterns:
        hits = sorted(glob.glob(pat))
        if hits:
            return hits[-1]
    for name in ("chromium", "chromium-browser", "google-chrome", "chrome"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _png_size(path: Path) -> tuple[int, int]:
    with path.open("rb") as fh:
        head = fh.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return (0, 0)
    w, h = struct.unpack(">II", head[16:24])
    return (w, h)


def _read_png_rgb(path: Path) -> tuple[int, int, bytes]:
    """Decode an 8-bit RGB/RGBA PNG to (W, H, RGB bytes). Undoes row filters."""
    d = path.read_bytes()
    i, W, H, ct, idat = 8, 0, 0, 0, b""
    while i < len(d):
        ln = struct.unpack(">I", d[i:i + 4])[0]
        typ = d[i + 4:i + 8]
        data = d[i + 8:i + 8 + ln]
        if typ == b"IHDR":
            W, H, _bd, ct = struct.unpack(">IIBB", data[:10])
        elif typ == b"IDAT":
            idat += data
        i += 12 + ln
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(idat)
    stride = W * ch
    out = bytearray()
    prev = bytes(stride)
    off = 0
    for _y in range(H):
        f = raw[off]
        line = bytearray(raw[off + 1:off + 1 + stride])
        off += 1 + stride
        for x in range(stride):
            a = line[x - ch] if x >= ch else 0
            b = prev[x]
            c = prev[x - ch] if x >= ch else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + b) & 255
            elif f == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 255
            elif f == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 255
        out += line
        prev = bytes(line)
    # Drop alpha if present.
    if ch == 4:
        rgb = bytearray()
        for j in range(0, len(out), 4):
            rgb += out[j:j + 3]
        return W, H, bytes(rgb)
    if ch == 1:
        rgb = bytearray()
        for v in out:
            rgb += bytes((v, v, v))
        return W, H, bytes(rgb)
    return W, H, bytes(out)


def _write_png_rgb(path: Path, w: int, h: int, rgb: bytes) -> None:
    stride = w * 3
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter: none
        raw += rgb[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + typ + data + struct.pack(
            ">I", zlib.crc32(typ + data) & 0xFFFFFFFF
        )

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")
    )


def _crop_top(path: Path, w: int, h: int) -> None:
    """Crop the PNG in place to its top-left w×h region."""
    W, H, rgb = _read_png_rgb(path)
    if (W, H) == (w, h):
        return
    cw = min(w, W)
    chh = min(h, H)
    out = bytearray()
    for y in range(chh):
        out += rgb[(y * W) * 3:(y * W + cw) * 3]
    _write_png_rgb(path, cw, chh, bytes(out))


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_html(spec: ThumbnailSpec) -> str:
    subjects = spec.subjects or []
    grad = f"linear-gradient(135deg,{spec.bg_from},{spec.bg_to})"
    shadow = "0 6px 24px rgba(0,0,0,.55)"

    if spec.layout == "split" and len(subjects) >= 2:
        # Skip the headline when it would just duplicate the VS badge below.
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
        self._chrome = find_chrome(chrome_path)

    @property
    def available(self) -> bool:
        return self._chrome is not None

    def render(self, spec: ThumbnailSpec, out_path: Path) -> tuple[int, int]:
        if not self._chrome:
            raise RuntimeError("No Chromium/Chrome binary found for thumbnail rendering.")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        html_path = out_path.with_suffix(".html")
        html_path.write_text(build_html(spec), encoding="utf-8")
        cmd = [
            self._chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
            "--hide-scrollbars", "--force-device-scale-factor=1",
            f"--window-size={WIDTH},{HEIGHT + _RENDER_MARGIN}",
            f"--screenshot={out_path}", f"file://{html_path}",
        ]
        subprocess.run(cmd, capture_output=True, timeout=60)
        html_path.unlink(missing_ok=True)
        if not out_path.exists():
            raise RuntimeError("Chromium did not produce a thumbnail PNG.")
        # Crop away Chromium's short-viewport white band to an exact 1280×720.
        _crop_top(out_path, WIDTH, HEIGHT)
        return _png_size(out_path)
