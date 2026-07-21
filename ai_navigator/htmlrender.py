"""Shared HTML → PNG rendering via headless Chromium.

Used by both the thumbnail stage (§54/§61) and the video frame renderer (§25).
Free and key-less. Works around Chromium's short-viewport screenshot by
rendering into a taller window and cropping to the exact target size
(pure-Python PNG crop — no Pillow/ffmpeg dependency).
"""

from __future__ import annotations

import glob
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

# Chromium's headless layout viewport is shorter than --window-size height.
_RENDER_MARGIN = 220


def find_chrome(override: str = "") -> str | None:
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


def png_size(path: Path) -> tuple[int, int]:
    head = path.read_bytes()[:24]
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        return (0, 0)
    return struct.unpack(">II", head[16:24])


def _read_png_rgb(path: Path) -> tuple[int, int, bytes]:
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
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + typ + data + struct.pack(
            ">I", zlib.crc32(typ + data) & 0xFFFFFFFF
        )

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", comp) + chunk(b"IEND", b"")
    )


def _crop_top(path: Path, w: int, h: int) -> None:
    W, H, rgb = _read_png_rgb(path)
    if (W, H) == (w, h):
        return
    cw, chh = min(w, W), min(h, H)
    out = bytearray()
    for y in range(chh):
        out += rgb[(y * W) * 3:(y * W + cw) * 3]
    _write_png_rgb(path, cw, chh, bytes(out))


def render_html_to_png(
    html: str, out_path: Path, *, width: int, height: int, chrome_path: str = "", crop: bool = True
) -> tuple[int, int]:
    """Render HTML to a PNG screenshot.

    With ``crop=True`` the output is exactly ``width×height`` (pure-Python crop of
    Chromium's short-viewport white band). With ``crop=False`` the taller raw
    screenshot is kept — cheaper when a downstream step (e.g. ffmpeg) will crop
    the top ``width×height`` region itself.
    """
    chrome = find_chrome(chrome_path)
    if not chrome:
        raise RuntimeError("No Chromium/Chrome binary found for HTML rendering.")
    out_path = out_path.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    html_path = out_path.with_suffix(".html")
    html_path.write_text(html, encoding="utf-8")
    cmd = [
        chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
        "--hide-scrollbars", "--force-device-scale-factor=1",
        f"--window-size={width},{height + _RENDER_MARGIN}",
        # Absolute file:// URL — a relative path renders Chrome's error page.
        f"--screenshot={out_path}", f"file://{html_path}",
    ]
    subprocess.run(cmd, capture_output=True, timeout=60)
    html_path.unlink(missing_ok=True)
    if not out_path.exists():
        raise RuntimeError("Chromium did not produce a PNG.")
    if crop:
        _crop_top(out_path, width, height)
    return png_size(out_path)
