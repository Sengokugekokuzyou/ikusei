"""Plan pipeline (spec §39 Phase 1, §44).

Wires the stages together:

    research -> fact-check -> ideas(>=10) -> critique -> score -> judge

and writes the six report artifacts a human reviews before Phase 2:

    reports/YYYY-MM-DD_<slug>/
      research.json  ideas.json  critique.json
      scores.json    selected_plan.json  sources.json
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from datetime import date
from pathlib import Path

from .config import Config
from .database import ToolDatabase
from .llm import build_provider
from .planner import Critic, IdeaGenerator, Judge, Scorer
from .research import BeginnerTranslator, FactChecker, Researcher, extract_tools
from .script import BeginnerQA, FactQA, ScriptWriter, TTSFormatter
from .storyboard import StoryboardBuilder, SubtitleBuilder, to_srt
from .voice import VoiceSynthesizer, build_adapter
from .thumbnail import ChromiumThumbnailRenderer, ThumbnailDirector, ThumbnailJudge
from .video import VideoBuilder
from .capture import CaptureRecorder, placeholder_recipe
from .image import ImageManager, build_image_provider
from .image.manager import build_credits
from .schemas import (
    BeginnerQAReport,
    FactQAReport,
    Finding,
    ResearchReport,
    AudioUnit,
    Scene,
    Script,
    ScriptLine,
    ScriptSection,
    SelectedPlan,
    Storyboard,
    ThumbnailCandidate,
    ThumbnailSet,
    TTSScript,
    Verdict,
    VideoResult,
    VoiceClip,
    VoiceManifest,
    CaptureManifest,
    ImageAsset,
    ImageManifest,
    to_json,
)


def slugify(text: str) -> str:
    """ASCII slug when possible, else a safe fallback for report dir names."""
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    ascii_text = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_text).strip("-").lower()
    return ascii_text or "topic"


class PlanPipeline:
    def __init__(self, config: Config) -> None:
        self._cfg = config
        self._tool_db = ToolDatabase(config.tools_db_dir())
        tools_dict = self._tool_db.all()
        provider_name = config.get("providers.text", "mock")
        model = config.get(f"providers.models.{provider_name}", "")
        self._llm = build_provider(provider_name, model=model, tool_db=tools_dict)

    def run(self, topic: str, on_date: date | None = None) -> tuple[SelectedPlan, Path]:
        produced_at = (on_date or date.today()).isoformat()
        known = self._tool_db.known_tools()
        tools = extract_tools(topic, known)

        # 1) Research + fact-check
        researcher = Researcher(self._llm)
        research = researcher.run(topic, tools, produced_at)

        fact_checker = FactChecker(self._llm, self._tool_db.all())
        fact = fact_checker.run(topic, tools, produced_at)
        research.fact_check = fact

        # 2) Ideas (>=10) -> critique -> score -> judge
        generator = IdeaGenerator(self._llm, self._cfg.get("planner.ideas_per_topic", 10))
        idea_set = generator.run(topic, tools, research)

        critic = Critic(self._llm, self._cfg.get("planner.min_weaknesses_per_idea", 5))
        critique_set = critic.run(idea_set)

        scorer = Scorer(self._llm, self._cfg.get("planner.score_weights", {}))
        score_set = scorer.run(idea_set, critique_set)

        judge = Judge(
            video_min=self._cfg.get("planner.judge.video_min", 80),
            shorts_min=self._cfg.get("planner.judge.shorts_min", 65),
            min_fact_score=self._cfg.get("fact_check.min_fact_score", 95),
        )
        plan = judge.run(topic, produced_at, idea_set, score_set, research, fact)

        # 3) Write artifacts
        out_dir = self._cfg.report_root() / f"{produced_at}_{slugify(topic)}"
        out_dir.mkdir(parents=True, exist_ok=True)
        self._write(out_dir / "research.json", research)
        self._write(out_dir / "ideas.json", idea_set)
        self._write(out_dir / "critique.json", critique_set)
        self._write(out_dir / "scores.json", score_set)
        self._write(out_dir / "selected_plan.json", plan)
        self._write(
            out_dir / "sources.json",
            {"topic": topic, "produced_at": produced_at, "sources": research.sources},
        )
        return plan, out_dir

    # --- Phase 2: Script system (§17/§8/§20/§13) ---------------------------
    def build_script(
        self, plan: SelectedPlan, research: ResearchReport
    ) -> tuple[Script, BeginnerQAReport, FactQAReport, "TTSScriptType"]:
        translator = BeginnerTranslator()
        tool_db = self._tool_db.all()
        writer = ScriptWriter(self._llm, tool_db, translator)
        beginner_qa = BeginnerQA(threshold=80, translator=translator)
        fact_qa = FactQA(tool_db, threshold=self._cfg.get("fact_check.min_fact_score", 95))
        formatter = TTSFormatter()

        # Regeneration loop (§20/§30): rewrite until beginner QA clears the bar.
        max_attempts = 3
        script = writer.run(plan, research)
        bqa = beginner_qa.run(script, attempts=1)
        attempt = 1
        while not bqa.passed and attempt < max_attempts:
            attempt += 1
            script = writer.run(plan, research)
            bqa = beginner_qa.run(script, attempts=attempt)

        fqa = fact_qa.run(script, research)
        tts = formatter.run(script)
        return script, bqa, fqa, tts

    # --- Phase 3: Voice + Storyboard (§7/§8/§21-24/§28) --------------------
    def build_media(self, script: Script, tts, out_dir: Path) -> tuple[object, Storyboard, object]:
        adapter = build_adapter(
            self._cfg.get("voice.adapter", "mock"),
            sample_rate=self._cfg.get("voice.sample_rate", 24000),
            endpoint=os.environ.get("VOICEVOX_ENDPOINT", self._cfg.get("voice.endpoint", "")),
            speaker=self._cfg.get("voice.speaker", 3),
        )
        voice = VoiceSynthesizer(adapter).run(tts, out_dir)
        storyboard = StoryboardBuilder().run(script, voice)
        subtitles = SubtitleBuilder().run(tts, voice)
        return voice, storyboard, subtitles

    # --- Thumbnails (§61-64) — free HTML→Chromium rendering ---------------
    def build_thumbnails(self, plan: SelectedPlan, out_dir: Path) -> ThumbnailSet:
        director = ThumbnailDirector()
        judge = ThumbnailJudge()
        renderer = ChromiumThumbnailRenderer(self._cfg.get("thumbnail.chrome_path", ""))
        n = self._cfg.get("thumbnail.candidates", 3)
        specs = director.run(plan)[:max(3, n)]
        result = ThumbnailSet(topic=plan.topic, produced_at=plan.produced_at, renderer="chromium")
        if not renderer.available:
            result.warnings.append(
                "Chromiumが見つからずサムネ未生成。thumbnail.chrome_path を設定してください。"
            )
            result.candidates = [ThumbnailCandidate(spec=s) for s in specs]
            return result
        for spec in specs:
            rel = f"thumbnails/thumb_{spec.label}.png"
            w, h = renderer.render(spec, out_dir / rel)
            result.candidates.append(
                ThumbnailCandidate(spec=spec, image_path=rel, width=w, height=h)
            )
        result.chosen_label = judge.judge(result.candidates)
        return result

    def run_script_from_dir(
        self, report_dir: Path
    ) -> tuple[Script, BeginnerQAReport, FactQAReport, Storyboard, ThumbnailSet]:
        plan = _load_plan(report_dir / "selected_plan.json")
        research = _load_research(report_dir / "research.json")
        script, bqa, fqa, tts = self.build_script(plan, research)
        self._write(report_dir / "script.json", script)
        self._write(report_dir / "script_tts.json", tts)
        self._write(report_dir / "beginner_qa.json", bqa)
        self._write(report_dir / "fact_qa.json", fqa)

        # Phase 3: voice + storyboard + subtitles.
        voice, storyboard, subtitles = self.build_media(script, tts, report_dir)
        self._write_media(report_dir, voice, storyboard, subtitles)

        # Thumbnails (free, Chromium-rendered).
        thumbnails = self.build_thumbnails(plan, report_dir)
        self._write(report_dir / "thumbnails.json", thumbnails)
        return script, bqa, fqa, storyboard, thumbnails

    def _write_media(self, report_dir: Path, voice, storyboard, subtitles) -> None:
        self._write(report_dir / "voice.json", voice)
        self._write(report_dir / "storyboard.json", storyboard)
        self._write(report_dir / "subtitles.json", subtitles)
        (report_dir / "captions.srt").write_text(to_srt(subtitles), encoding="utf-8")

    def resynth_voice_from_dir(self, report_dir: Path) -> VoiceManifest:
        """Re-synthesize narration with the configured adapter (e.g. voicevox).

        Real engine durations differ from the mock estimate, so the storyboard
        and subtitles are re-derived from the new timing too.
        """
        script = _load_script(report_dir / "script.json")
        tts = _load_tts(report_dir / "script_tts.json")
        voice, storyboard, subtitles = self.build_media(script, tts, report_dir)
        self._write_media(report_dir, voice, storyboard, subtitles)
        return voice

    # --- Phase 5: Browser capture (§5-6) — Playwright recording -----------
    def build_capture_from_dir(self, report_dir: Path, created_at: str) -> CaptureManifest:
        storyboard = _load_storyboard(report_dir / "storyboard.json")
        demo_scenes = [s.scene_id for s in storyboard.scenes if s.section == "real_demo"]
        manifest = CaptureManifest(topic=storyboard.topic, produced_at=storyboard.produced_at)
        recorder = CaptureRecorder(
            chrome_path=self._cfg.get("thumbnail.chrome_path", ""),
            ffmpeg_path=self._cfg.get("video.ffmpeg_path", ""),
        )
        ok, reason = recorder.available()
        if not ok:
            manifest.warnings.append(reason)
            self._write(report_dir / "capture.json", manifest)
            return manifest
        if not demo_scenes:
            manifest.warnings.append("storyboardにreal_demoシーンがありません。")
            self._write(report_dir / "capture.json", manifest)
            return manifest
        # Record the safe placeholder demo attached to the first real_demo scene.
        recipe = placeholder_recipe(report_dir, scene_id=demo_scenes[0])
        asset = recorder.record(recipe, report_dir, created_at)
        manifest.assets.append(asset)
        manifest.warnings.append(
            "これは§49準拠のプレースホルダ収録です。実サービスの操作映像は、"
            "各自のログイン済みローカル環境で recipe を差し替えて収録してください。"
        )
        self._write(report_dir / "capture.json", manifest)
        return manifest

    # --- Images (§48/§49/§70) — free stock/CC/local B-roll ----------------
    def build_images_from_dir(self, report_dir: Path) -> ImageManifest:
        from .config import REPO_ROOT
        storyboard = _load_storyboard(report_dir / "storyboard.json")
        provider = build_image_provider(
            self._cfg.get("image.provider", "none"),
            api_key=os.environ.get("PIXABAY_API_KEY", ""),
        )
        assets_dir = REPO_ROOT / self._cfg.get("image.assets_dir", "assets")
        manifest = ImageManager(provider, assets_dir).run(storyboard, report_dir)
        self._write(report_dir / "images.json", manifest)
        (report_dir / "credits.txt").write_text(build_credits(manifest), encoding="utf-8")
        return manifest

    # --- Phase 4: Video (§4-5) — free FFmpeg render -----------------------
    def build_video_from_dir(self, report_dir: Path) -> VideoResult:
        storyboard = _load_storyboard(report_dir / "storyboard.json")
        voice = _load_voice(report_dir / "voice.json")
        captures = _load_captures(report_dir / "capture.json")
        images = _load_images(report_dir / "images.json")
        result = VideoBuilder(self._cfg).run(
            storyboard, voice, report_dir, captures=captures, images=images)
        self._write(report_dir / "video.json", result)
        return result

    @staticmethod
    def _write(path: Path, obj) -> None:
        path.write_text(to_json(obj) + "\n", encoding="utf-8")


# Type alias used only for the return annotation above.
from .schemas import TTSScript as TTSScriptType  # noqa: E402


def _load_plan(path: Path) -> SelectedPlan:
    d = json.loads(path.read_text(encoding="utf-8"))
    d["verdict"] = Verdict(d.get("verdict", "discard"))
    return SelectedPlan(**d)


def _load_script(path: Path) -> Script:
    d = json.loads(path.read_text(encoding="utf-8"))
    sections = [
        ScriptSection(
            section=s.get("section", ""),
            lines=[
                ScriptLine(
                    text=ln.get("text", ""), jargon=list(ln.get("jargon", [])),
                    is_claim=bool(ln.get("is_claim", False)),
                )
                for ln in s.get("lines", [])
            ],
        )
        for s in d.get("sections", [])
    ]
    return Script(
        topic=d.get("topic", ""), produced_at=d.get("produced_at", ""),
        idea_id=d.get("idea_id", 0), working_title=d.get("working_title", ""),
        target_viewer=d.get("target_viewer", ""),
        comparison_targets=list(d.get("comparison_targets", [])), sections=sections,
    )


def _load_tts(path: Path) -> TTSScript:
    d = json.loads(path.read_text(encoding="utf-8"))
    units = [
        AudioUnit(
            id=u.get("id", 0), section=u.get("section", ""), text=u.get("text", ""),
            line=u.get("line", 0), speaker=u.get("speaker", "default"),
            speed=u.get("speed", 1.0), pause_after=u.get("pause_after", 0.3),
            emotion=u.get("emotion", "friendly"), emphasis=list(u.get("emphasis", [])),
        )
        for u in d.get("units", [])
    ]
    return TTSScript(topic=d.get("topic", ""), produced_at=d.get("produced_at", ""), units=units)


def _load_storyboard(path: Path) -> Storyboard:
    d = json.loads(path.read_text(encoding="utf-8"))
    scenes = [
        Scene(
            scene_id=s.get("scene_id", i + 1), section=s.get("section", ""),
            duration=s.get("duration", 0.0), voice=s.get("voice", ""),
            visual_type=s.get("visual_type", ""), component=s.get("component", ""),
            params=dict(s.get("params", {})), animation=s.get("animation", ""),
            camera=s.get("camera", ""), start=s.get("start", 0.0),
        )
        for i, s in enumerate(d.get("scenes", []))
    ]
    return Storyboard(
        topic=d.get("topic", ""), produced_at=d.get("produced_at", ""),
        working_title=d.get("working_title", ""),
        total_duration=d.get("total_duration", 0.0), scenes=scenes,
        visual_mix=dict(d.get("visual_mix", {})), warnings=list(d.get("warnings", [])),
    )


def _load_voice(path: Path) -> VoiceManifest:
    d = json.loads(path.read_text(encoding="utf-8"))
    clips = [
        VoiceClip(
            id=c.get("id", 0), section=c.get("section", ""), line=c.get("line", 0),
            text=c.get("text", ""), start=c.get("start", 0.0), end=c.get("end", 0.0),
            duration=c.get("duration", 0.0), pause_after=c.get("pause_after", 0.0),
            audio_path=c.get("audio_path", ""),
        )
        for c in d.get("clips", [])
    ]
    return VoiceManifest(
        topic=d.get("topic", ""), produced_at=d.get("produced_at", ""),
        adapter=d.get("adapter", "mock"), total_duration=d.get("total_duration", 0.0),
        clips=clips,
    )


def _load_images(path: Path) -> dict:
    """Map scene_id -> ImageAsset from images.json (if it exists)."""
    if not path.exists():
        return {}
    d = json.loads(path.read_text(encoding="utf-8"))
    out: dict = {}
    for a in d.get("assets", []):
        if a.get("file_path") and a.get("scene_id"):
            out[a["scene_id"]] = ImageAsset(
                scene_id=a["scene_id"], role=a.get("role", "broll"),
                source=a.get("source", "local"), query=a.get("query", ""),
                file_path=a.get("file_path", ""), page_url=a.get("page_url", ""),
                author=a.get("author", ""), license=a.get("license", ""),
                attribution_required=bool(a.get("attribution_required")),
                caption=a.get("caption", ""), is_official=bool(a.get("is_official")),
            )
    return out


def _load_captures(path: Path) -> dict:
    """Map scene_id -> captured mp4 path from capture.json (if it exists)."""
    if not path.exists():
        return {}
    d = json.loads(path.read_text(encoding="utf-8"))
    out: dict = {}
    for a in d.get("assets", []):
        if a.get("video_path") and a.get("scene_id"):
            out[a["scene_id"]] = a["video_path"]
    return out


def _load_research(path: Path) -> ResearchReport:
    d = json.loads(path.read_text(encoding="utf-8"))
    findings = [
        Finding(
            claim=f.get("claim", ""),
            detail=f.get("detail", ""),
            source_urls=list(f.get("source_urls", [])),
            kind=f.get("kind", "fact"),
        )
        for f in d.get("findings", [])
    ]
    # FactQA only needs topic + findings; keep the loader minimal.
    return ResearchReport(
        topic=d.get("topic", ""),
        produced_at=d.get("produced_at", ""),
        tools_covered=list(d.get("tools_covered", [])),
        findings=findings,
    )
