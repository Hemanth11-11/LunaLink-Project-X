"""SpaceX-style explorable LunaLink 3D model, embedded as a Three.js component.

A self-contained WebGL scene (bundled Three.js r128, no pip dependency, works
offline) rendered inside Streamlit via ``components.v1.html``. All interactivity
- exploded view, part toggles, subsystem highlight, click-for-info, orbit
controls - runs client-side; Python only supplies live subsystem metrics.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_WEBGL = _ROOT / "assets" / "webgl"
_TEMPLATE = Path(__file__).with_name("spacecraft_explorer.html")


@lru_cache(maxsize=1)
def _libraries() -> tuple[str, str, str]:
    return (
        (_WEBGL / "three.min.js").read_text(encoding="utf-8"),
        (_WEBGL / "OrbitControls.js").read_text(encoding="utf-8"),
        _TEMPLATE.read_text(encoding="utf-8"),
    )


def build_explorer_html(theme: str = "dark", live_metrics: dict[str, str] | None = None) -> str:
    """Assemble the standalone explorer HTML (usable in Streamlit or a browser)."""

    three_js, orbit_js, template = _libraries()
    data = json.dumps({"theme": theme, "metrics": live_metrics or {}})
    return (
        template.replace("__THREE__", three_js)
        .replace("__ORBIT__", orbit_js)
        .replace("__DATA__", data)
    )


def spacecraft_explorer(
    theme: str = "dark", live_metrics: dict[str, str] | None = None, height: int = 640
) -> None:
    """Render the explorer inside a Streamlit app."""

    import streamlit.components.v1 as components

    components.html(build_explorer_html(theme, live_metrics), height=height, scrolling=False)
