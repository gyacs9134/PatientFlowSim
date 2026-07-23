"""Streamlit integration for the spatial editor, animation, and GIF export."""

from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

import streamlit as st

from patientflowsim.floorplan_component import floorplan_component
from patientflowsim.gif_export import GifExportConfig, render_gif, sampled_frame_times
from patientflowsim.layout import (
    HospitalLayout,
    LayoutValidationError,
    layout_from_json,
    layout_to_json,
    load_layout,
    save_layout,
)
from patientflowsim.spatial_events import prepare_spatial_timeline


LAYOUT_DIRECTORY = Path(__file__).resolve().parents[1] / "data" / "layouts"


def current_layout() -> HospitalLayout:
    """Return the current validated layout stored in the Streamlit session."""
    if "floorplan_layout" not in st.session_state:
        st.session_state.floorplan_layout = load_layout()
    return st.session_state.floorplan_layout


def _safe_name(value: str) -> str:
    name = re.sub(r"[^A-Za-z0-9_-]+", "_", value.strip()).strip("_")
    if not name:
        raise ValueError("Layout name must contain at least one letter or number")
    return name


def timeline_for_result(result: Any, layout: HospitalLayout) -> dict[str, Any] | None:
    """Prepare or reuse the deterministic spatial timeline for a result/layout pair."""
    if result is None:
        return None
    signature = (
        int(result.config.simulation.random_seed),
        len(result.events),
        hash(layout_to_json(layout)),
    )
    if st.session_state.get("floorplan_timeline_signature") != signature:
        st.session_state.floorplan_timeline = prepare_spatial_timeline(result.events, result.patients, layout)
        st.session_state.floorplan_timeline_signature = signature
    return st.session_state.floorplan_timeline


def receive_editor_value(value: dict[str, Any] | None, layout: HospitalLayout) -> None:
    """Validate and store meaningful layout updates returned by the component."""
    if not value or value.get("type") != "layout_changed" or not isinstance(value.get("layout"), dict):
        return
    try:
        edited = HospitalLayout.from_dict(value["layout"])
    except LayoutValidationError as exc:
        st.error(f"The editor returned an invalid layout: {exc}")
        return
    if layout_to_json(edited) != layout_to_json(layout):
        st.session_state.floorplan_layout = edited
        st.rerun()


def render_editor(layout: HospitalLayout, result: Any) -> None:
    """Render the dedicated metre-based layout editor."""
    st.caption("All saved coordinates and dimensions are in metres. Wheel to zoom; drag empty canvas to pan; Shift-click for multi-selection.")
    for warning in layout.overlap_warnings():
        st.warning(warning)
    if result is not None:
        for warning in layout.station_capacity_warnings(result.config.resources):
            st.warning(warning)
    value = floorplan_component(layout, mode="editor", height=780, key="floorplan_editor_component")
    receive_editor_value(value, layout)


def render_simulation(layout: HospitalLayout, timeline: dict[str, Any] | None) -> None:
    if timeline is None:
        st.info("Run the Python simulation first, then return here to replay its event log.")
        return
    st.caption("Playback runs locally in the component; it does not trigger one Streamlit rerun per frame.")
    value = floorplan_component(layout, timeline, mode="simulation", height=780, key="floorplan_simulation_component")
    receive_editor_value(value, layout)


def render_gif_export(
    layout: HospitalLayout,
    timeline: dict[str, Any] | None,
    preset_ranges: dict[str, dict[str, float]] | None = None,
) -> None:
    """Render bounded GIF export controls and a download action."""
    if timeline is None:
        st.info("Run a simulation before exporting its animation.")
        return
    duration = float(timeline["duration"])
    range_labels = ["Complete simulation", "Selected time range"]
    preset_labels = {
        "peak_congestion": "Peak congestion period",
        "examination_return_surge": "Examination return surge",
        "final_hour": "Final hour",
    }
    if preset_ranges:
        range_labels.extend(label for key, label in preset_labels.items() if key in preset_ranges)
    export_scope = st.radio("Export range", range_labels, horizontal=True)
    first, second, third = st.columns(3)
    with first:
        start_time = st.number_input("Start minute", 0.0, max(duration - 0.01, 0.0), 0.0, disabled=export_scope != "Selected time range")
        playback_speed = st.select_slider("Playback speed", options=[1, 2, 5, 10, 20, 30, 60], value=30)
        fps = st.selectbox("Output FPS", [10, 15, 20], index=0)
    with second:
        end_time = st.number_input("End minute", 0.01, duration, duration, disabled=export_scope != "Selected time range")
        width = st.selectbox("Width", [640, 800, 960, 1280], index=2)
        height = st.selectbox("Height", [360, 480, 640, 720], index=2)
    with third:
        max_frames = st.slider("Maximum frames", 20, 300, 120, 10)
        include_ids = st.checkbox("Patient IDs")
        include_dimensions = st.checkbox("Room dimensions")
        loop = st.checkbox("Loop continuously", value=True)
    option_columns = st.columns(3)
    include_legend = option_columns[0].checkbox("Include legend", value=True)
    include_metrics = option_columns[1].checkbox("Include metrics overlay", value=True)
    include_satisfaction = option_columns[2].checkbox("Satisfaction labels", value=True)
    if export_scope == "Complete simulation":
        actual_start, actual_end = 0.0, duration
    elif export_scope == "Selected time range":
        actual_start, actual_end = float(start_time), float(end_time)
    else:
        selected_key = next(key for key, label in preset_labels.items() if label == export_scope)
        actual_start = float(preset_ranges[selected_key]["start"])  # type: ignore[index]
        actual_end = float(preset_ranges[selected_key]["end"])  # type: ignore[index]
    config = GifExportConfig(
        start_time=actual_start,
        end_time=actual_end,
        playback_speed=float(playback_speed),
        fps=int(fps),
        width=int(width),
        height=int(height),
        include_patient_ids=include_ids,
        include_dimension_labels=include_dimensions,
        include_legend=include_legend,
        include_metrics_overlay=include_metrics,
        include_satisfaction_labels=include_satisfaction,
        loop=loop,
        max_frames=max_frames,
    )
    try:
        frames = len(sampled_frame_times(duration, config))
        st.caption(f"This export will sample {frames} frames. Long days are down-sampled to protect memory.")
    except ValueError as exc:
        st.error(str(exc))
        return
    if st.button("Export Simulation as GIF", type="primary"):
        progress = st.progress(0.0, "Rendering GIF frames…")
        try:
            data = render_gif(layout, timeline, config, lambda value: progress.progress(value, f"Rendering GIF frames… {value:.0%}"))
        except ValueError as exc:
            progress.empty()
            st.error(str(exc))
        else:
            progress.progress(1.0, "GIF ready")
            st.session_state.floorplan_gif = data
    if data := st.session_state.get("floorplan_gif"):
        st.image(data, caption="Latest exported animation")
        st.download_button("Download GIF", data=data, file_name="patientflowsim_animation.gif", mime="image/gif")


def render_layout_management(layout: HospitalLayout) -> None:
    """Render JSON import/export and saved-layout management."""
    LAYOUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    st.download_button("Export current layout JSON", layout_to_json(layout), file_name=f"{_safe_name(layout.name)}.json", mime="application/json")
    uploaded = st.file_uploader("Import layout JSON", type=["json"])
    if uploaded and st.button("Load imported layout"):
        try:
            st.session_state.floorplan_layout = layout_from_json(uploaded.getvalue())
        except LayoutValidationError as exc:
            st.error(str(exc))
        else:
            st.success("Imported layout validated and loaded")
            st.rerun()
    st.divider()
    name = st.text_input("Layout name", layout.name)
    action_columns = st.columns(3)
    if action_columns[0].button("Save layout"):
        try:
            renamed = HospitalLayout.from_dict({**layout.to_dict(), "name": name})
            save_layout(renamed, LAYOUT_DIRECTORY / f"{_safe_name(name)}.json")
            st.session_state.floorplan_layout = renamed
            st.success("Layout saved. Streamlit Community Cloud local files may be ephemeral after a restart.")
        except (LayoutValidationError, ValueError) as exc:
            st.error(str(exc))
    if action_columns[1].button("Duplicate layout"):
        try:
            duplicate_name = f"{name} copy"
            duplicate = HospitalLayout.from_dict({**layout.to_dict(), "name": duplicate_name})
            save_layout(duplicate, LAYOUT_DIRECTORY / f"{_safe_name(duplicate_name)}.json")
            st.session_state.floorplan_layout = duplicate
            st.success("Layout duplicated")
        except (LayoutValidationError, ValueError) as exc:
            st.error(str(exc))
    if action_columns[2].button("Reset to default"):
        st.session_state.floorplan_layout = load_layout()
        st.rerun()
    saved = sorted(LAYOUT_DIRECTORY.glob("*.json"))
    if saved:
        selected = st.selectbox("Saved layouts", saved, format_func=lambda path: path.stem)
        load_column, delete_column = st.columns(2)
        if load_column.button("Load selected"):
            try:
                st.session_state.floorplan_layout = load_layout(selected)
            except LayoutValidationError as exc:
                st.error(str(exc))
            else:
                st.rerun()
        if delete_column.button("Delete selected"):
            selected.unlink(missing_ok=True)
            st.success(f"Deleted {selected.name}; this local file is not recoverable from the app.")


def render(result: Any = None) -> None:
    """Render the complete 2D floor-plan feature in one dashboard tab."""
    layout = current_layout()
    timeline = timeline_for_result(result, layout)
    editor_tab, simulation_tab, gif_tab, management_tab = st.tabs(["Layout Editor", "Simulation View", "GIF Export", "Layout Management"])
    with editor_tab:
        render_editor(layout, result)
    with simulation_tab:
        render_simulation(layout, timeline)
    with gif_tab:
        render_gif_export(layout, timeline)
    with management_tab:
        render_layout_management(layout)
