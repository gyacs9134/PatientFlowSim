"""Clean setup screen with progressive disclosure and one primary action."""

from __future__ import annotations

from datetime import time
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

from patientflowsim.config import SimulationConfig, config_from_dict, load_config
from patientflowsim.floorplan_component import floorplan_component
from patientflowsim.layout import HospitalLayout


PRIMARY_ACTION_LABEL = "Start Simulation"
ADVANCED_SETTINGS_EXPANDED = False
SCENARIO_PATH = Path(__file__).resolve().parents[1] / "config" / "scenarios.yaml"


def _clock(value: str) -> time:
    hours, minutes = (int(part) for part in value.split(":"))
    return time(hours, minutes)


def _clock_text(value: time) -> str:
    return value.strftime("%H:%M")


def _scenario_definitions() -> dict[str, dict[str, Any]]:
    return yaml.safe_load(SCENARIO_PATH.read_text(encoding="utf-8"))


def _service_time_controls(config: SimulationConfig, scenario_key: str) -> dict[str, dict[str, float | str]]:
    result: dict[str, dict[str, float | str]] = {}
    labels = {
        "first_check_in": "First check-in",
        "triage": "Triage",
        "initial_consultation": "Initial doctor consultation",
        "laboratory": "Laboratory examination",
        "imaging": "Imaging examination",
        "return_check_in": "Return check-in",
        "return_consultation": "Return doctor consultation",
    }
    for stage, label in labels.items():
        service = config.service_times[stage]
        st.markdown(f"**{label}**")
        columns = st.columns(4)
        kind = columns[0].selectbox(
            "Distribution",
            ["fixed", "normal", "lognormal"],
            index=["fixed", "normal", "lognormal"].index(service.kind),
            key=f"{scenario_key}_{stage}_kind",
            label_visibility="collapsed",
        )
        mean = columns[1].number_input("Mean", 0.0, 240.0, float(service.mean), key=f"{scenario_key}_{stage}_mean")
        std = columns[2].number_input("Std. dev.", 0.0, 120.0, float(service.std), key=f"{scenario_key}_{stage}_std")
        minimum = columns[3].number_input("Minimum", 0.0, 120.0, float(service.minimum), key=f"{scenario_key}_{stage}_minimum")
        result[stage] = {"kind": kind, "mean": mean, "std": std, "minimum": minimum}
    return result


def render(layout: HospitalLayout) -> tuple[str | None, SimulationConfig | None, str]:
    """Render setup and return an action, validated config, and scenario name."""
    st.markdown('<div class="pfs-kicker">Outpatient operations simulator</div>', unsafe_allow_html=True)
    st.markdown('<div class="pfs-title">PatientFlowSim</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="pfs-subtitle">Configure one synthetic clinic day, then watch patients move, queues form, and examination returns compete for capacity.</div>',
        unsafe_allow_html=True,
    )
    st.write("")

    preview_column, setup_column = st.columns([1.08, 0.92], gap="large")
    with preview_column:
        heading, action = st.columns([3, 1])
        heading.subheader("Selected floor plan")
        edit = action.button("Edit Floor Plan", width="stretch")
        st.caption(f"{layout.name} · {layout.canvas_width_m:g} × {layout.canvas_height_m:g} metres")
        floorplan_component(layout, mode="preview", height=505, key="floorplan_setup_preview")
    if edit:
        return "edit_layout", None, ""

    with setup_column:
        definitions = _scenario_definitions()
        scenario_name = st.selectbox("Scenario", list(definitions), index=0, key="setup_scenario")
        selected_config = config_from_dict(definitions[scenario_name])
        scenario_key = scenario_name.lower().replace(" ", "_").replace("-", "_")
        st.caption("Essential settings are visible. Technical assumptions remain tucked away until needed.")
        with st.form("simulation_setup_form", border=True):
            first, second = st.columns(2)
            scheduled_count = first.number_input(
                "Scheduled patients", 1, 500, selected_config.patients.scheduled_count, key=f"{scenario_key}_patients"
            )
            random_seed = second.number_input(
                "Random seed", 0, 2_147_483_647, selected_config.simulation.random_seed, key=f"{scenario_key}_seed"
            )
            opening = first.time_input("Clinic opens", _clock(selected_config.clinic.opening_time), key=f"{scenario_key}_opening")
            closing = second.time_input("Clinic closes", _clock(selected_config.clinic.closing_time), key=f"{scenario_key}_closing")

            resource_columns = st.columns(2)
            doctors = resource_columns[0].number_input("Doctors", 1, 30, selected_config.resources.doctors, key=f"{scenario_key}_doctors")
            nurses = resource_columns[1].number_input("Triage nurses", 1, 30, selected_config.resources.triage_nurses, key=f"{scenario_key}_nurses")
            laboratory = resource_columns[0].number_input("Laboratory capacity", 1, 30, selected_config.resources.laboratory_capacity, key=f"{scenario_key}_lab")
            imaging = resource_columns[1].number_input("Imaging capacity", 1, 30, selected_config.resources.imaging_capacity, key=f"{scenario_key}_imaging")
            seats = st.number_input("Waiting-area seats", 0, 500, selected_config.resources.waiting_area_seats, key=f"{scenario_key}_seats")
            st.markdown("**Examination demand**")
            examination_columns = st.columns(2)
            laboratory_probability = examination_columns[0].slider(
                "Laboratory", 0.0, 1.0, float(selected_config.examinations.laboratory_probability), 0.01, key=f"{scenario_key}_lab_probability"
            )
            imaging_probability = examination_columns[1].slider(
                "Imaging", 0.0, 1.0, float(selected_config.examinations.imaging_probability), 0.01, key=f"{scenario_key}_imaging_probability"
            )

            with st.expander("Advanced Settings", expanded=ADVANCED_SETTINGS_EXPANDED):
                arrival_tab, service_tab, policy_tab, satisfaction_tab = st.tabs(
                    ["Appointments", "Service times", "Queue policy", "Satisfaction"]
                )
                with arrival_tab:
                    appointment_distribution = st.selectbox(
                        "Appointment distribution",
                        ["evenly_spaced", "morning_heavy"],
                        index=["evenly_spaced", "morning_heavy"].index(selected_config.patients.appointment_distribution),
                        key=f"{scenario_key}_distribution",
                    )
                    appointment_interval = st.number_input(
                        "Appointment interval (minutes)", 0.1, 60.0, float(selected_config.patients.appointment_interval_minutes), key=f"{scenario_key}_interval"
                    )
                    no_show_rate = st.slider("No-show rate", 0.0, 1.0, float(selected_config.patients.no_show_rate), 0.01, key=f"{scenario_key}_no_show")
                    lateness_rate = st.slider("Late-arrival rate", 0.0, 1.0, float(selected_config.patients.lateness_rate), 0.01, key=f"{scenario_key}_late")
                    early_max = st.number_input("Maximum early arrival (minutes)", 0.0, 120.0, float(selected_config.patients.early_arrival_range[1]), key=f"{scenario_key}_early_max")
                    late_max = st.number_input("Maximum late arrival (minutes)", 0.0, 240.0, float(selected_config.patients.late_arrival_range[1]), key=f"{scenario_key}_late_max")
                    check_in_staff = st.number_input("Check-in staff", 1, 30, selected_config.resources.check_in_staff, key=f"{scenario_key}_checkin")
                with service_tab:
                    service_times = _service_time_controls(selected_config, scenario_key)
                with policy_tab:
                    policies = ["shared_fifo", "return_priority", "reserved_return"]
                    queue_policy = st.selectbox(
                        "Doctor queue policy",
                        policies,
                        index=policies.index(selected_config.queue_policy.consultation_policy),
                        key=f"{scenario_key}_policy",
                    )
                    reserved_doctors = st.number_input(
                        "Doctors reserved for returns", 0, max(0, int(doctors) - 1), min(selected_config.queue_policy.reserved_return_doctors, max(0, int(doctors) - 1)), key=f"{scenario_key}_reserved"
                    )
                with satisfaction_tab:
                    satisfaction_rules = {}
                    for rule, value in selected_config.satisfaction_rules.items():
                        satisfaction_rules[rule] = st.number_input(
                            rule.replace("_", " ").title(), value=float(value), key=f"{scenario_key}_satisfaction_{rule}"
                        )

            st.write("")
            submitted = st.form_submit_button(PRIMARY_ACTION_LABEL, type="primary", width="stretch")

        if submitted:
            overrides = {
                "clinic": {"opening_time": _clock_text(opening), "closing_time": _clock_text(closing)},
                "patients": {
                    "scheduled_count": int(scheduled_count),
                    "appointment_interval_minutes": float(appointment_interval),
                    "appointment_distribution": appointment_distribution,
                    "no_show_rate": float(no_show_rate),
                    "lateness_rate": float(lateness_rate),
                    "early_arrival_range": [0.0, float(early_max)],
                    "late_arrival_range": [1.0, float(late_max)],
                },
                "resources": {
                    "check_in_staff": int(check_in_staff),
                    "triage_nurses": int(nurses),
                    "doctors": int(doctors),
                    "laboratory_capacity": int(laboratory),
                    "imaging_capacity": int(imaging),
                    "waiting_area_seats": int(seats),
                },
                "examinations": {
                    "laboratory_probability": float(laboratory_probability),
                    "imaging_probability": float(imaging_probability),
                },
                "queue_policy": {
                    "consultation_policy": queue_policy,
                    "reserved_return_doctors": int(reserved_doctors),
                },
                "simulation": {"random_seed": int(random_seed)},
                "service_times": service_times,
                "satisfaction_rules": satisfaction_rules,
            }
            merged = selected_config.to_dict()
            for section, values in overrides.items():
                merged[section] = values
            try:
                return "start", config_from_dict(merged), scenario_name
            except ValueError as exc:
                st.error(str(exc))
    return None, None, scenario_name
