"""Video Builder (spec §4-5 Phase 4) — FFmpeg slideshow with motion + audio + subs.

Pipeline: render scene frames -> per-scene Ken Burns segments (§23/§58 motion)
-> concat with the narration track and burned subtitles -> final mp4.
All free: Chromium for frames, a full ffmpeg (imageio-ffmpeg) for encoding.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..htmlrender import find_chrome
from ..schemas import Storyboard, VideoResult, VoiceManifest
from .audio import build_narration_wav
from .ffmpeg import ffmpeg_has_full_support, find_ffmpeg
from .frames import SceneFrameRenderer

W, H = 1280, 720

_SUB_STYLE = (
    "FontName=IPAGothic,FontSize=18,PrimaryColour=&H00FFFFFF&,"
    "OutlineColour=&H99000000&,BorderStyle=1,Outline=2,Shadow=1,"
    "Alignment=2,MarginV=40"
)


def _kenburns_vf(index: int, dur: float, fps: int) -> str:
    """A smooth Ken Burns expression — used ONLY on real photos (§58).

    Text/graphic cards are kept static: a slow drift on a card looks amateurish
    (real explainer videos don't do it) and zoompan's integer stepping makes slow
    moves judder. Photos, by contrast, look cinematic with a gentle move.

    Smoothness: oversample the source to 3840px so each integer-pixel crop step
    is well under one output pixel at 1280×720.
    """
    n = max(2, int(round(dur * fps)))
    base = f"crop={W}:{H}:0:0,scale=3840:2160,"
    mode = index % 3
    if mode == 0:  # slow zoom in
        z = "min(zoom+0.0006,1.10)"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    elif mode == 1:  # slow zoom out
        z = "max(1.10-0.0006*on,1.0)"
        x, y = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    else:  # gentle horizontal pan at a mild fixed zoom
        z = "1.07"
        x, y = f"(iw-iw/zoom)*on/{n}", "ih/2-(ih/zoom/2)"
    return (f"{base}zoompan=z='{z}':x='{x}':y='{y}':d={n}:s={W}x{H}:fps={fps},"
            f"format=yuv420p")


class VideoBuilder:
    def __init__(self, cfg=None) -> None:
        self._fps = (cfg.get("video.fps", 30) if cfg else 30)
        self._motion = (cfg.get("video.motion", True) if cfg else True)
        self._ffmpeg_override = (cfg.get("video.ffmpeg_path", "") if cfg else "")
        self._chrome_path = (cfg.get("thumbnail.chrome_path", "") if cfg else "")

    def run(self, storyboard: Storyboard, voice: VoiceManifest, report_dir: Path,
            captures: dict | None = None, images: dict | None = None) -> VideoResult:
        result = VideoResult(
            topic=storyboard.topic, produced_at=storyboard.produced_at,
            width=W, height=H, fps=self._fps, scenes=len(storyboard.scenes),
            motion=self._motion,
        )
        ffmpeg = find_ffmpeg(self._ffmpeg_override)
        if not ffmpeg or not ffmpeg_has_full_support(ffmpeg):
            result.warnings.append(
                "H.264/AAC/字幕対応のffmpegが必要です。`pip install imageio-ffmpeg` で無料導入できます。"
            )
            return result
        if not find_chrome(self._chrome_path):
            result.warnings.append("フレーム描画用のChromiumが見つかりません。")
            return result

        # 1) Scene frames + narration track.
        frames = SceneFrameRenderer(self._chrome_path).render_all(storyboard, report_dir, images=images)
        narration = report_dir / "narration.wav"
        audio_dur = build_narration_wav(voice, report_dir, narration)
        has_audio = audio_dur > 0

        # 2) Per-scene segments: photos get Ken Burns, cards stay static.
        seg_dir = report_dir / "frames"
        seg_list = seg_dir / "segments.txt"
        captures = captures or {}
        image_ids = {
            sid for sid, a in (images or {}).items()
            if getattr(a, "file_path", "") and (report_dir / a.file_path).exists()
        }
        lines = []
        for i, (rel, dur) in enumerate(frames):
            seg_rel = f"frames/seg_{i:03d}.mp4"
            scene_id = storyboard.scenes[i].scene_id if i < len(storyboard.scenes) else -1
            clip_rel = captures.get(scene_id)
            if clip_rel and (report_dir / clip_rel).exists():
                # Real captured footage: loop/trim to the scene's narration length.
                cmd = [
                    ffmpeg, "-y", "-stream_loop", "-1", "-t", f"{dur:.3f}", "-i", clip_rel,
                    "-vf", f"scale={W}:{H},setsar=1,format=yuv420p", "-c:v", "libx264",
                    "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(self._fps), seg_rel,
                ]
                proc = subprocess.run(cmd, cwd=report_dir, capture_output=True, text=True)
                if proc.returncode != 0 or not (report_dir / seg_rel).exists():
                    result.warnings.append(f"収録シーン{i}の合成失敗: {proc.stderr[-200:]}")
                    return result
                lines.append(f"file '{Path(seg_rel).name}'")
                continue
            if self._motion and scene_id in image_ids:
                # Real photo -> smooth Ken Burns. Single image input (NO -loop):
                # zoompan d=frames emits exactly the frames we want; -loop would
                # feed zoompan a stream and explode the frame count.
                inp = ["-i", rel]
                vf = _kenburns_vf(i, dur, self._fps)
            else:
                # Text/graphic card -> keep it still (clean + no judder).
                inp = ["-loop", "1", "-t", f"{dur:.3f}", "-i", rel]
                vf = f"crop={W}:{H}:0:0,scale={W}:{H},format=yuv420p"
            cmd = [
                ffmpeg, "-y", *inp, "-vf", vf, "-c:v", "libx264",
                "-preset", "veryfast", "-pix_fmt", "yuv420p", "-r", str(self._fps), seg_rel,
            ]
            proc = subprocess.run(cmd, cwd=report_dir, capture_output=True, text=True)
            if proc.returncode != 0 or not (report_dir / seg_rel).exists():
                result.warnings.append(f"シーン{i}のエンコード失敗: {proc.stderr[-200:]}")
                return result
            lines.append(f"file '{Path(seg_rel).name}'")
        seg_list.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # 3) Concat + narration + burned subtitles -> final mp4.
        srt = report_dir / "captions.srt"
        has_subs = srt.exists()
        vf_final = f"subtitles=captions.srt:force_style='{_SUB_STYLE}'" if has_subs else None
        out_rel = "video.mp4"
        cmd = [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", "frames/segments.txt"]
        if has_audio:
            cmd += ["-i", "narration.wav"]
        if vf_final:
            cmd += ["-vf", vf_final]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p"]
        if has_audio:
            cmd += ["-c:a", "aac", "-shortest"]
        cmd += [out_rel]
        proc = subprocess.run(cmd, cwd=report_dir, capture_output=True, text=True)
        if proc.returncode != 0 or not (report_dir / out_rel).exists():
            result.warnings.append(f"最終エンコード失敗: {proc.stderr[-300:]}")
            return result

        result.path = out_rel
        result.duration = round(storyboard.total_duration, 3)
        result.has_audio = has_audio
        result.has_subtitles = has_subs
        result.ok = True
        return result
