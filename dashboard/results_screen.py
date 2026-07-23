"""Dedicated end-of-run results screen with analysis, replay, and exports."""

from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.express as px
import streamlit as st

from patientflowsim.analysis import (
    calculate_bottleneck_ranking,
    identify_replay_periods,
    operational_findings,
    patient_flow_time_series,
    queue_time_series,
    result_summary_frame,
)
from patientflowsim.layout import HospitalLayout
from patientflowsim.floorplan_component import floorplan_component
from patientflowsim.scenarios import load_scenario_definitions, run_scenarios
from patientflowsim.visualisation import satisfaction_chart, timeline_chart, utilisation_chart

from .floorplan_tab import render_gif_export


PRIMARY_RESULT_KEYS = (
    ("Scheduled", "total_patients_scheduled", "{:.0f}"),
    ("Arrived", "total_patients_arriving", "{:.0f}"),
    ("Completed", "completed_patients", "{:.0f}"),
    ("Unfinished at closing", "patients_unfinished_at_closing", "{:.0f}"),
    ("Average total wait", "average_total_waiting_time", "{:.1f} min"),
    ("90th percentile wait", "p90_total_waiting_time", "{:.1f} min"),
    ("Average visit", "average_total_visit_duration", "{:.1f} min"),
    ("Average satisfaction", "average_final_satisfaction", "{:.1f}/100"),
    ("Satisfaction below 60", "patients_below_satisfaction_60", "{:.0f}"),
    ("Staff overtime", "overtime_duration", "{:.1f} min"),
)


def _time_label(minutes: float, opening: str) -> str:
    start_hour, start_minute = (int(part) for part in opening.split(":"))
    total = start_hour * 60 + start_minute + int(round(minutes))
    return f"{(total // 60) % 24:02d}:{total % 60:02d}"


def _summary_report(result: Any, scenario_name: str, run_id: str) -> bytes:
    ranking = calculate_bottleneck_ranking(result)
    findings = operational_findings(result)
    lines = [
        "# PatientFlowSim run summary",
        "",
        f"- Run ID: {run_id}",
        f"- Scenario: {scenario_name}",
        f"- Random seed: {result.config.simulation.random_seed}",
        "",
        "## Primary metrics",
    ]
    for row in result_summary_frame(result).itertuples(index=False):
        lines.append(f"- {row.metric}: {row.value}")
    lines.extend(["", "## Bottleneck ranking"])
    for row in ranking.itertuples(index=False):
        lines.append(
            f"{row.rank}. {row.department} — {row.bottleneck_score:.1f}/100; peak queue {row.maximum_queue}; longest wait {row.longest_wait:.1f} min"
        )
    lines.extend(["", "## Rule-based findings", *[f"- {finding}" for finding in findings]])
    lines.extend(
        [
            "",
            "## Validation note",
            "This synthetic model is educational. Real operational use requires calibration and validation with anonymised hospital data.",
        ]
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _actions(result: Any, scenario_name: str, run_id: str, key_prefix: str) -> str | None:
    columns = st.columns([1.15, 1, 1, 1, 1.15])
    if columns[0].button("↻ Run Again", type="primary", width="stretch", key=f"{key_prefix}_again"):
        return "run_again"
    if columns[1].button("Modify Scenario", width="stretch", key=f"{key_prefix}_modify"):
        return "setup"
    if columns[2].button("Edit Floor Plan", width="stretch", key=f"{key_prefix}_edit"):
        return "edit_layout"
    if columns[3].button("Replay", width="stretch", key=f"{key_prefix}_replay"):
        return "replay"
    columns[4].download_button(
        "Export Summary Report",
        _summary_report(result, scenario_name, run_id),
        file_name=f"{run_id}_summary.md",
        mime="text/markdown",
        width="stretch",
        key=f"{key_prefix}_report",
    )
    return None


def _render_bottlenecks(result: Any) -> None:
    ranking = calculate_bottleneck_ranking(result)
    st.caption(
        "Score = queue pressure (30) + p90 wait (30) + utilisation (25) + sampled minutes above capacity (15)."
    )
    for row in ranking.itertuples(index=False):
        with st.container(border=True):
            columns = st.columns([0.45, 2.3, 1, 1, 1, 1])
            columns[0].markdown(f'<div class="pfs-rank">#{row.rank}</div>', unsafe_allow_html=True)
            columns[1].markdown(f"**{row.department}**  \nScore {row.bottleneck_score:.1f}/100")
            columns[2].metric("Peak queue", row.maximum_queue)
            columns[3].metric("Longest wait", f"{row.longest_wait:.1f} min")
            columns[4].metric("Peak time", _time_label(row.peak_congestion_time, result.config.clinic.opening_time))
            columns[5].metric("Utilisation", f"{row.resource_utilisation:.0%}")
    st.subheader("Operational findings")
    for finding in operational_findings(result):
        st.info(finding)


def _render_flow(result: Any) -> None:
    flow = patient_flow_time_series(result)
    queue = queue_time_series(result)
    st.plotly_chart(
        px.line(
            flow,
            x="time",
            y=["patients_inside", "initial_flow", "at_examination", "return_flow"],
            labels={"value": "Patients", "time": "Minutes from opening", "variable": "Flow"},
            title="Patients inside the clinic and flow phase",
        ),
        width="stretch",
    )
    completed = result.patients.loc[result.patients["discharge_time"].notna()]
    detail_columns = st.columns(2)
    detail_columns[0].plotly_chart(
        px.histogram(completed, x="total_waiting_time", nbins=24, title="Total waiting-time distribution"),
        width="stretch",
    )
    detail_columns[1].plotly_chart(
        px.line(
            flow,
            x="time",
            y=["patients_without_seats", "examination_returns_cumulative"],
            title="No-seat waiting and examination returns",
            labels={"value": "Patients", "time": "Minutes from opening", "variable": "Measure"},
        ),
        width="stretch",
    )
    chart_columns = st.columns(2)
    chart_columns[0].plotly_chart(
        px.line(queue, x="time", y="queue_length", color="stage", title="Queue length by department"),
        width="stretch",
    )
    doctor_queue = queue.loc[queue["stage"].isin(["Initial consultation", "Return consultation"])]
    chart_columns[1].plotly_chart(
        px.line(doctor_queue, x="time", y="queue_length", color="stage", title="Initial versus return doctor queues"),
        width="stretch",
    )
    st.plotly_chart(
        px.line(
            flow,
            x="time",
            y=["arrived_cumulative", "completed_cumulative"],
            title="Cumulative arrivals and completions",
            labels={"value": "Patients", "time": "Minutes from opening", "variable": "Event"},
        ),
        width="stretch",
    )


def _render_resources(result: Any) -> None:
    st.plotly_chart(utilisation_chart(result), width="stretch")
    busy_rows = []
    for resource in ["check_in", "triage", "doctors", "laboratory", "imaging"]:
        busy_rows.extend(
            [
                {"resource": resource, "time_type": "Busy", "minutes": result.metrics.get(f"{resource}_busy_time", 0)},
                {"resource": resource, "time_type": "Idle capacity", "minutes": result.metrics.get(f"{resource}_idle_capacity_time", 0)},
            ]
        )
    st.plotly_chart(
        px.bar(pd.DataFrame(busy_rows), x="resource", y="minutes", color="time_type", barmode="stack", title="Busy and idle capacity minutes"),
        width="stretch",
    )
    st.metric("Overtime after closing", f"{result.metrics.get('overtime_duration', 0):.1f} min")


def _render_satisfaction(result: Any) -> None:
    completed = result.patients.loc[result.patients["discharge_time"].notna()]
    chart_columns = st.columns(2)
    chart_columns[0].plotly_chart(satisfaction_chart(result), width="stretch")
    chart_columns[1].plotly_chart(
        px.scatter(
            completed,
            x="total_waiting_time",
            y="final_satisfaction_score",
            color="examination_type",
            title="Satisfaction versus total waiting time",
        ),
        width="stretch",
    )
    st.caption("The satisfaction score is a configurable simulation assumption and is not a clinically validated experience scale.")


def _render_records(result: Any, run_id: str) -> None:
    st.download_button(
        "Export Patient Records CSV",
        result.patients.to_csv(index=False).encode("utf-8"),
        file_name=f"{run_id}_patients.csv",
        mime="text/csv",
    )
    st.dataframe(result.patients, width="stretch", hide_index=True)
    patients = result.patients.loc[~result.patients["no_show"], "patient_id"].tolist()
    if patients:
        selected = st.selectbox("Patient journey", patients)
        st.plotly_chart(timeline_chart(result, selected), width="stretch")


def render(
    result: Any,
    timeline: dict[str, Any],
    layout: HospitalLayout,
    scenario_name: str,
    run_id: str,
) -> tuple[str | None, dict[str, float] | None]:
    """Render complete run results and return a requested action/replay period."""
    st.markdown('<div class="pfs-kicker">End-of-run statistics</div>', unsafe_allow_html=True)
    st.markdown('<div class="pfs-title">Simulation Complete</div>', unsafe_allow_html=True)
    duration = float(result.metrics.get("simulation_end_time", 0.0))
    st.markdown(
        f'<div class="pfs-run-meta">{scenario_name} · Run {run_id} · {duration:.1f} simulated minutes · Seed {result.config.simulation.random_seed}</div>',
        unsafe_allow_html=True,
    )
    action = _actions(result, scenario_name, run_id, "top")
    if action:
        return action, None

    metric_columns = st.columns(5)
    for index, (label, key, formatter) in enumerate(PRIMARY_RESULT_KEYS):
        value = float(result.metrics.get(key, 0))
        metric_columns[index % 5].metric(label, formatter.format(value))

    summary_tab, bottleneck_tab, flow_tab, resource_tab, satisfaction_tab, records_tab = st.tabs(
        ["Summary", "Bottlenecks", "Patient flow", "Resources", "Satisfaction", "Patient records"]
    )
    with summary_tab:
        st.subheader("What happened")
        for finding in operational_findings(result):
            st.info(finding)
        replay_periods = identify_replay_periods(result)
        st.subheader("Replay floor plan")
        replay_label = st.selectbox(
            "Replay period",
            list(replay_periods),
            format_func=lambda value: value.replace("_", " ").title(),
        )
        with st.expander("End-of-run floor-plan summary", expanded=True):
            selected_period = replay_periods[replay_label]
            floorplan_component(
                layout,
                timeline,
                mode="simulation",
                height=560,
                auto_play=False,
                start_time=float(selected_period["start"]),
                end_time=float(selected_period["end"]),
                playback_speed=10,
                show_finish=False,
                key=f"results_floorplan_{replay_label}",
            )
        replay_columns = st.columns([1, 1, 3])
        if replay_columns[0].button("Replay selected", type="primary", width="stretch"):
            return "replay", replay_periods[replay_label]
        replay_columns[1].download_button(
            "Export Results CSV",
            result_summary_frame(result).to_csv(index=False).encode("utf-8"),
            file_name=f"{run_id}_results.csv",
            mime="text/csv",
            width="stretch",
        )
        with st.expander("GIF Export", expanded=False):
            render_gif_export(layout, timeline, replay_periods)
    with bottleneck_tab:
        _render_bottlenecks(result)
    with flow_tab:
        _render_flow(result)
    with resource_tab:
        _render_resources(result)
        st.subheader("Scenario comparison")
        definitions = load_scenario_definitions()
        choices = st.multiselect("Compare with scenarios", list(definitions), default=["Baseline", "Additional doctor"])
        if st.button("Compare Scenario", disabled=not choices):
            with st.spinner("Running comparable populations with the same random seed…"):
                st.session_state.result_comparison = run_scenarios(choices, base_config=result.config)
        comparison = st.session_state.get("result_comparison")
        if comparison is not None:
            st.dataframe(comparison, width="stretch", hide_index=True)
    with satisfaction_tab:
        _render_satisfaction(result)
    with records_tab:
        _render_records(result, run_id)

    st.divider()
    action = _actions(result, scenario_name, run_id, "bottom")
    return action, None
