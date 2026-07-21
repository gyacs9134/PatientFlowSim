"""Python bridge for the React/Konva Streamlit floor-plan component."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit.components.v1 as components

from .layout import HospitalLayout


_BUILD_DIR = Path(__file__).resolve().parents[2] / "frontend" / "floorplan_component" / "build"
_DEV_URL = os.environ.get("PATIENTFLOWSIM_COMPONENT_URL")
_component = components.declare_component(
    "patientflowsim_floorplan",
    url=_DEV_URL if _DEV_URL else None,
    path=None if _DEV_URL else str(_BUILD_DIR),
)


def floorplan_component(
    layout: HospitalLayout,
    timeline: dict[str, Any] | None = None,
    *,
    mode: str = "editor",
    height: int = 760,
    key: str | None = None,
) -> dict[str, Any] | None:
    """Render the component and return meaningful editor state changes only."""
    if mode not in {"editor", "simulation"}:
        raise ValueError("Floor-plan mode must be 'editor' or 'simulation'")
    value = _component(
        layout=layout.to_dict(),
        timeline=timeline or {"duration": 0, "patients": [], "staff": [], "seats": []},
        mode=mode,
        height=height,
        default=None,
        key=key,
    )
    return value if isinstance(value, dict) else None

