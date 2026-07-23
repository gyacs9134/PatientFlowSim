"""PatientFlowSim's explicit Setup → Live Simulation → Results interface."""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from dashboard import editor_screen, live_simulation, results_screen, setup_screen
from dashboard.app_state import AppState, transition
from dashboard.floorplan_tab import current_layout, timeline_for_result
from dashboard.styles import apply_app_styles
from patientflowsim.simulation import run_simulation


st.set_page_config(
    page_title="PatientFlowSim",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed",
)
apply_app_styles()

if "app_state" not in st.session_state:
    st.session_state.app_state = AppState.SETUP.value
if "show_floorplan_editor" not in st.session_state:
    st.session_state.show_floorplan_editor = False


def _set_state(target: AppState) -> None:
    current = AppState(st.session_state.app_state)
    st.session_state.app_state = transition(current, target).value


def _start_run(config, scenario_name: str) -> None:
    with st.spinner("Preparing the clinic day and animation timeline…"):
        result = run_simulation(config)
        timeline = timeline_for_result(result, current_layout())
    st.session_state.result = result
    st.session_state.active_timeline = timeline
    st.session_state.active_config = config
    st.session_state.scenario_name = scenario_name
    st.session_state.run_id = datetime.now().strftime("PFS-%Y%m%d-%H%M%S")
    st.session_state.replay_period = None
    st.session_state.result_comparison = None
    _set_state(AppState.LIVE)
    st.rerun()


if st.session_state.show_floorplan_editor:
    editor_action = editor_screen.render(st.session_state.get("result"))
    if editor_action == "back":
        st.session_state.show_floorplan_editor = False
        st.rerun()
    st.stop()


state = AppState(st.session_state.app_state)
layout = current_layout()

if state == AppState.SETUP:
    action, config, scenario = setup_screen.render(layout)
    if action == "edit_layout":
        st.session_state.show_floorplan_editor = True
        st.rerun()
    if action == "start" and config is not None:
        _start_run(config, scenario)

elif state == AppState.LIVE:
    result = st.session_state.get("result")
    timeline = st.session_state.get("active_timeline")
    if result is None or timeline is None:
        st.error("This simulation is no longer available. Return to setup and start a new run.")
        if st.button("Return to Setup", type="primary"):
            _set_state(AppState.SETUP)
            st.rerun()
    else:
        action = live_simulation.render(
            layout,
            timeline,
            st.session_state.get("scenario_name", "Baseline"),
            st.session_state.get("replay_period"),
        )
        if action == "setup":
            _set_state(AppState.SETUP)
            st.rerun()
        if action == "results":
            st.session_state.replay_period = None
            _set_state(AppState.RESULTS)
            st.rerun()

elif state == AppState.RESULTS:
    result = st.session_state.get("result")
    timeline = st.session_state.get("active_timeline")
    if result is None or timeline is None:
        _set_state(AppState.SETUP)
        st.rerun()
    action, replay_period = results_screen.render(
        result,
        timeline,
        layout,
        st.session_state.get("scenario_name", "Baseline"),
        st.session_state.get("run_id", "PFS-run"),
    )
    if action == "run_again":
        _start_run(st.session_state.active_config, st.session_state.get("scenario_name", "Baseline"))
    elif action == "setup":
        _set_state(AppState.SETUP)
        st.rerun()
    elif action == "edit_layout":
        st.session_state.show_floorplan_editor = True
        st.rerun()
    elif action == "replay":
        st.session_state.replay_period = replay_period
        _set_state(AppState.LIVE)
        st.rerun()

st.caption(
    "Synthetic patient data only. Educational and operational-modelling use; not clinical decision support."
)
