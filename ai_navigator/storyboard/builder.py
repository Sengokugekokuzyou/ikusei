"""Storyboard Builder (spec §21-24).

One scene per script line, timed to the voice manifest. Each scene gets a
Remotion component (§25), a camera motion preset (§60) so nothing is fully
static (§23), and the build reports its visual-type mix against the §22 target.
"""

from __future__ import annotations

from ..schemas import Scene, Script, Storyboard, VoiceManifest

# §22 target: real operation footage should be 35–45% of runtime.
_REAL_CAPTURE_MIN = 0.35

# §60 camera presets, cycled to guarantee variation (§23).
_CAMERA_CYCLE = [
    "cinematic_zoom", "slow_push", "left_to_right", "slow_pull",
    "right_to_left", "parallax_soft", "center_focus",
]


def _visual_for(section: str) -> tuple[str, str]:
    """(visual_type, default component) for a section."""
    return {
        "opening": ("motion_graphic", "ToolIntroCard"),
        "beginner_explanation": ("motion_graphic", "BeginnerTip"),
        "what_can_it_do": ("motion_graphic", "FeatureList"),
        "real_demo": ("real_capture", ""),  # ScreenCapture placeholder (Phase 5)
        "comparison": ("comparison_card", "VSComparison"),
        "recommended_for": ("motion_graphic", "ProsConsCard"),
        "not_recommended_for": ("motion_graphic", "ProsConsCard"),
        "final_decision": ("motion_graphic", "FinalRecommendation"),
    }.get(section, ("static", ""))


class StoryboardBuilder:
    def run(self, script: Script, voice: VoiceManifest) -> Storyboard:
        # line index -> (section, ScriptLine)
        line_meta: list = []
        for sec in script.sections:
            for ln in sec.lines:
                line_meta.append((sec.section, ln))

        # Group clips by their source line, in timeline order.
        by_line: dict[int, list] = {}
        for clip in voice.clips:
            by_line.setdefault(clip.line, []).append(clip)

        tools = script.comparison_targets
        scenes: list[Scene] = []
        cam_i = 0
        for li in sorted(by_line):
            clips = by_line[li]
            section, script_line = line_meta[li] if li < len(line_meta) else ("", None)
            start = clips[0].start
            # Tile to the next scene: include the last clip's trailing pause.
            end = clips[-1].end + clips[-1].pause_after
            duration = round(end - start, 3)
            visual_type, component = _visual_for(section)
            camera = _CAMERA_CYCLE[cam_i % len(_CAMERA_CYCLE)]
            cam_i += 1

            params = self._params(section, script_line, tools, component)
            component = params.pop("_component", component)

            scenes.append(
                Scene(
                    scene_id=li + 1,
                    section=section,
                    duration=duration,
                    voice=script_line.text if script_line else "",
                    visual_type=visual_type,
                    component=component,
                    params=params,
                    animation=self._animation(section),
                    camera=camera,
                    start=round(start, 3),
                )
            )

        total = voice.total_duration or (scenes[-1].start + scenes[-1].duration if scenes else 0.0)
        mix, warnings = self._visual_mix(scenes, total)
        return Storyboard(
            topic=script.topic,
            produced_at=script.produced_at,
            working_title=script.working_title,
            total_duration=round(total, 3),
            scenes=scenes,
            visual_mix=mix,
            warnings=warnings,
        )

    @staticmethod
    def _animation(section: str) -> str:
        return {
            "opening": "text_reveal",
            "comparison": "slide_in",
            "final_decision": "fade_in",
        }.get(section, "fade_in")

    @staticmethod
    def _params(section, line, tools, component) -> dict:
        text = line.text if line else ""
        p: dict = {}
        if section == "comparison" and len(tools) >= 2:
            p["left"], p["right"] = tools[0], tools[1]
            # A line naming one tool highlights that side.
            if tools[0] in text:
                p["highlight"] = "left"
            elif tools[1] in text:
                p["highlight"] = "right"
        elif section == "what_can_it_do" and text.startswith("・"):
            p["item"] = text.lstrip("・").rstrip("。")
        elif section == "recommended_for":
            p["mode"] = "pros"
            if text.startswith("・"):
                p["item"] = text.lstrip("・").rstrip("。")
        elif section == "not_recommended_for":
            p["mode"] = "cons"
            if text.startswith("・"):
                p["item"] = text.lstrip("・").rstrip("。")
        elif section == "final_decision":
            if any(w in text for w in ["料金", "無料", "費用", "有料"]):
                p["_component"] = "PriceCard"
        elif section == "opening":
            p["title"] = text
            if tools:
                p["tools"] = tools
        elif section == "beginner_explanation" and line and line.jargon:
            p["term"] = line.jargon[0]
        return p

    @staticmethod
    def _visual_mix(scenes: list[Scene], total: float) -> tuple[dict[str, float], list[str]]:
        agg: dict[str, float] = {}
        for s in scenes:
            agg[s.visual_type] = agg.get(s.visual_type, 0.0) + s.duration
        mix = {k: round(v / total, 3) for k, v in agg.items()} if total else {}
        warnings: list[str] = []
        real = mix.get("real_capture", 0.0)
        if real < _REAL_CAPTURE_MIN:
            warnings.append(
                f"実操作映像が{real:.0%}で目標{_REAL_CAPTURE_MIN:.0%}未満(§22)。"
                "Phase 5のPlaywright実収録で補う必要があります。"
            )
        if mix.get("static", 0.0) > 0.10:
            warnings.append(f"完全静止画が{mix['static']:.0%}で上限10%超(§22/§23)。")
        return mix, warnings
