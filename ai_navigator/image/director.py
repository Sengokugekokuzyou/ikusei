"""Image Director (spec §50).

Decides which storyboard scenes get a real photo, and with what search query.
Only "human/concept" scenes get B-roll — structured info (VS comparison, feature
list, final decision) stays as clean cards, and real_demo stays for real screen
capture (§70 priority 1). Never assigns a photo as a fake service UI (§49).
"""

from __future__ import annotations

from ..schemas import Storyboard

# section -> (role, English B-roll query). Sections not listed keep their card.
_SECTION_IMAGE = {
    "opening": ("background", "person using laptop modern technology office"),
    "beginner_explanation": ("concept", "person thinking laptop learning"),
    "recommended_for": ("broll", "happy person working laptop"),
    "not_recommended_for": ("broll", "confused person computer frustrated"),
}


class ImageDirector:
    def plan(self, storyboard: Storyboard) -> list[tuple[int, str, str]]:
        """Return (scene_id, role, query) for scenes that should get a photo."""
        out: list[tuple[int, str, str]] = []
        for sc in storyboard.scenes:
            # real_demo is reserved for real capture; never a stock/fake screen.
            if sc.section == "real_demo":
                continue
            mapping = _SECTION_IMAGE.get(sc.section)
            if mapping:
                role, query = mapping
                out.append((sc.scene_id, role, query))
        return out
