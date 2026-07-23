"""Map-dominant live simulation screen."""

from __future__ import annotations

from typing import Any

import streamlit as st

from patientflowsim.floorplan_component import floorplan_component
from patientflowsim.layout import HospitalLayout


def render(
    layout: HospitalLayout,
    timeline: dict[str, Any],
    scenario_name: str,
    replay_period: dict[str, float] | None = None,
) -> str | None:
    """Render local animation playback and return a requested state transition."""
    period = replay_period or {"start": 0.0, "end": float(timeline.get("duration", 0.0))}
    heading, setup_action = st.columns([6, 1])
    with heading:
        st.markdown('<span class="pfs-state-chip">● LIVE SIMULATION</span>', unsafe_allow_html=True)
        st.subheader(scenario_name)
        st.caption("The Python event log is the source of truth. Playback and interpolation run locally in the map.")
    if setup_action.button("Stop & modify", width="stretch"):
        return "setup"
    value = floorplan_component(
        layout,
        timeline,
        mode="simulation",
        height=810,
        auto_play=True,
        start_time=float(period["start"]),
        end_time=float(period["end"]),
        playback_speed=10.0,
        show_finish=True,
        key=f"live_simulation_{scenario_name}_{period['start']:.2f}_{period['end']:.2f}",
    )
    if value and value.get("type") in {"simulation_complete", "finish_simulation"}:
        return "results"
    return None
