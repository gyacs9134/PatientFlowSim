"""Deterministic congestion, bottleneck, replay, and findings analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass(frozen=True, slots=True)
class StageDefinition:
    """Fields used to calculate one visible operational stage."""

    name: str
    queue_start: str
    service_start: str
    wait_column: str
    capacity_field: str
    utilisation_metric: str
    examination_type: str | None = None


STAGES = (
    StageDefinition("Check-in", "actual_arrival_time", "first_check_in_start", "first_check_in_wait", "check_in_staff", "check_in_utilisation"),
    StageDefinition("Triage", "first_check_in_end", "triage_start", "triage_wait", "triage_nurses", "triage_utilisation"),
    StageDefinition("Initial consultation", "first_doctor_queue_entry", "initial_consultation_start", "first_doctor_wait", "doctors", "doctors_utilisation"),
    StageDefinition("Laboratory", "examination_queue_entry", "examination_start", "examination_wait", "laboratory_capacity", "laboratory_utilisation", "laboratory"),
    StageDefinition("Imaging", "examination_queue_entry", "examination_start", "examination_wait", "imaging_capacity", "imaging_utilisation", "imaging"),
    StageDefinition("Return check-in", "return_to_clinic_time", "second_check_in_start", "return_check_in_wait", "check_in_staff", "check_in_utilisation"),
    StageDefinition("Return consultation", "return_consultation_queue_entry", "return_consultation_start", "return_consultation_wait", "doctors", "doctors_utilisation"),
)

STATUS_LEVELS = {"normal": 0, "busy": 1, "congested": 2, "critical": 3}


def congestion_status(queue_length: int, longest_wait: float, capacity: int, utilisation: float) -> str:
    """Classify operational pressure using transparent fixed thresholds."""
    capacity = max(1, int(capacity))
    pressure = queue_length / capacity
    if pressure > 3 or longest_wait >= 60 or (utilisation >= 0.95 and pressure > 1):
        return "critical"
    if pressure > 2 or longest_wait >= 30 or (utilisation >= 0.9 and pressure > 0.5):
        return "congested"
    if pressure > 1 or longest_wait >= 15 or utilisation >= 0.75:
        return "busy"
    return "normal"


def queue_time_series(result: Any, step_minutes: float = 5.0) -> pd.DataFrame:
    """Sample current queues and waits from patient queue-entry/service-start intervals."""
    if step_minutes <= 0:
        raise ValueError("Queue time-series step must be greater than zero")
    patients = result.patients.loc[~result.patients["no_show"]]
    end = float(result.metrics.get("simulation_end_time", patients["discharge_time"].max() or 0.0))
    times = np.arange(0.0, end + step_minutes, step_minutes)
    rows: list[dict[str, Any]] = []
    for stage in STAGES:
        stage_patients = patients
        if stage.examination_type is not None:
            stage_patients = stage_patients.loc[stage_patients["examination_type"] == stage.examination_type]
        starts = stage_patients[stage.queue_start]
        finishes = stage_patients[stage.service_start]
        capacity = int(getattr(result.config.resources, stage.capacity_field))
        utilisation = float(result.metrics.get(stage.utilisation_metric, 0.0))
        for time in times:
            waiting = starts.notna() & (starts <= time) & (finishes.isna() | (finishes > time))
            queue_length = int(waiting.sum())
            longest_wait = float((time - starts.loc[waiting]).max()) if queue_length else 0.0
            rows.append(
                {
                    "time": float(time),
                    "stage": stage.name,
                    "queue_length": queue_length,
                    "longest_current_wait": max(0.0, longest_wait),
                    "capacity": capacity,
                    "utilisation": utilisation,
                    "status": congestion_status(queue_length, longest_wait, capacity, utilisation),
                }
            )
    return pd.DataFrame(rows)


def calculate_bottleneck_ranking(result: Any, step_minutes: float = 5.0) -> pd.DataFrame:
    """Rank stages with a documented 100-point operational pressure score.

    Queue pressure contributes 30 points, 90th-percentile waiting contributes
    30, utilisation contributes 25, and duration above capacity contributes 15.
    """
    series = queue_time_series(result, step_minutes)
    patients = result.patients.loc[~result.patients["no_show"]]
    rows: list[dict[str, Any]] = []
    for stage in STAGES:
        stage_series = series.loc[series["stage"] == stage.name]
        stage_patients = patients
        if stage.examination_type is not None:
            stage_patients = stage_patients.loc[stage_patients["examination_type"] == stage.examination_type]
        waits = stage_patients[stage.wait_column].dropna().clip(lower=0)
        capacity = max(1, int(getattr(result.config.resources, stage.capacity_field)))
        maximum_queue = int(stage_series["queue_length"].max()) if len(stage_series) else 0
        average_queue = float(stage_series["queue_length"].mean()) if len(stage_series) else 0.0
        longest_wait = float(waits.max()) if len(waits) else 0.0
        average_wait = float(waits.mean()) if len(waits) else 0.0
        p90_wait = float(np.percentile(waits, 90)) if len(waits) else 0.0
        peak_row = stage_series.loc[stage_series["queue_length"].idxmax()] if len(stage_series) else None
        peak_time = float(peak_row["time"]) if peak_row is not None else 0.0
        utilisation = float(result.metrics.get(stage.utilisation_metric, 0.0))
        minutes_above_capacity = float((stage_series["queue_length"] > capacity).sum() * step_minutes)
        queue_score = min(maximum_queue / (capacity * 2), 1.0) * 30.0
        wait_score = min(p90_wait / 60.0, 1.0) * 30.0
        utilisation_score = min(utilisation / 0.95, 1.0) * 25.0
        duration_score = min(minutes_above_capacity / 120.0, 1.0) * 15.0
        displayed_components = [round(queue_score, 2), round(wait_score, 2), round(utilisation_score, 2), round(duration_score, 2)]
        rows.append(
            {
                "department": stage.name,
                "bottleneck_score": round(sum(displayed_components), 2),
                "queue_score": displayed_components[0],
                "wait_score": displayed_components[1],
                "utilisation_score": displayed_components[2],
                "duration_score": displayed_components[3],
                "maximum_queue": maximum_queue,
                "average_queue": round(average_queue, 2),
                "longest_wait": round(longest_wait, 2),
                "average_wait": round(average_wait, 2),
                "p90_wait": round(p90_wait, 2),
                "peak_congestion_time": peak_time,
                "resource_utilisation": utilisation,
                "minutes_above_capacity": minutes_above_capacity,
                "affected_patients": int(len(waits)),
            }
        )
    ranking = pd.DataFrame(rows).sort_values(
        ["bottleneck_score", "department"], ascending=[False, True], kind="stable"
    ).reset_index(drop=True)
    ranking.insert(0, "rank", np.arange(1, len(ranking) + 1))
    return ranking


def patient_flow_time_series(result: Any, step_minutes: float = 5.0) -> pd.DataFrame:
    """Return clinic population, flow, arrivals, completions, and seat use over time."""
    patients = result.patients.loc[~result.patients["no_show"]]
    end = float(result.metrics.get("simulation_end_time", patients["discharge_time"].max() or 0.0))
    times = np.arange(0.0, end + step_minutes, step_minutes)
    rows: list[dict[str, Any]] = []
    for time in times:
        arrived = patients["actual_arrival_time"] <= time
        inside = arrived & (patients["discharge_time"].isna() | (patients["discharge_time"] > time))
        at_examination = (
            patients["examination_queue_entry"].notna()
            & (patients["examination_queue_entry"] <= time)
            & (patients["return_to_clinic_time"].isna() | (patients["return_to_clinic_time"] > time))
        )
        return_flow = (
            patients["return_to_clinic_time"].notna()
            & (patients["return_to_clinic_time"] <= time)
            & (patients["discharge_time"].isna() | (patients["discharge_time"] > time))
        )
        initial_flow = inside & ~at_examination & ~return_flow
        seated_first = (
            (patients["first_seat_available"] == True)  # noqa: E712
            & patients["first_doctor_queue_entry"].notna()
            & (patients["first_doctor_queue_entry"] <= time)
            & (patients["initial_consultation_start"].isna() | (patients["initial_consultation_start"] > time))
        )
        seated_return = (
            (patients["return_seat_available"] == True)  # noqa: E712
            & patients["return_consultation_queue_entry"].notna()
            & (patients["return_consultation_queue_entry"] <= time)
            & (patients["return_consultation_start"].isna() | (patients["return_consultation_start"] > time))
        )
        standing_first = (
            (patients["first_seat_available"] == False)  # noqa: E712
            & patients["first_doctor_queue_entry"].notna()
            & (patients["first_doctor_queue_entry"] <= time)
            & (patients["initial_consultation_start"].isna() | (patients["initial_consultation_start"] > time))
        )
        standing_return = (
            (patients["return_seat_available"] == False)  # noqa: E712
            & patients["return_consultation_queue_entry"].notna()
            & (patients["return_consultation_queue_entry"] <= time)
            & (patients["return_consultation_start"].isna() | (patients["return_consultation_start"] > time))
        )
        rows.append(
            {
                "time": float(time),
                "patients_inside": int(inside.sum()),
                "initial_flow": int(initial_flow.sum()),
                "at_examination": int(at_examination.sum()),
                "return_flow": int(return_flow.sum()),
                "arrived_cumulative": int(arrived.sum()),
                "completed_cumulative": int((patients["discharge_time"].notna() & (patients["discharge_time"] <= time)).sum()),
                "seat_occupancy": int(seated_first.sum() + seated_return.sum()),
                "patients_without_seats": int(standing_first.sum() + standing_return.sum()),
                "examination_returns_cumulative": int(
                    (patients["return_to_clinic_time"].notna() & (patients["return_to_clinic_time"] <= time)).sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def identify_replay_periods(result: Any) -> dict[str, dict[str, float]]:
    """Identify deterministic full, peak, return-surge, and final-hour replay ranges."""
    end = float(result.metrics.get("simulation_end_time", 0.0))
    queue_series = queue_time_series(result)
    totals = queue_series.groupby("time", as_index=False)["queue_length"].sum()
    peak_time = float(totals.loc[totals["queue_length"].idxmax(), "time"]) if len(totals) else 0.0
    events = result.events
    returns = events.loc[events["event_type"] == "patient_returned", "time"] if len(events) else pd.Series(dtype=float)
    if len(returns):
        bins = np.arange(0.0, end + 15.0, 15.0)
        counts, edges = np.histogram(returns, bins=bins)
        return_time = float(edges[int(np.argmax(counts))])
    else:
        return_time = peak_time
    return {
        "full_simulation": {"start": 0.0, "end": end},
        "peak_congestion": {"start": max(0.0, peak_time - 30.0), "end": min(end, peak_time + 30.0)},
        "examination_return_surge": {"start": max(0.0, return_time - 15.0), "end": min(end, return_time + 45.0)},
        "final_hour": {"start": max(0.0, end - 60.0), "end": end},
    }


def operational_findings(result: Any) -> list[str]:
    """Generate evidence-backed operational observations from measured results."""
    ranking = calculate_bottleneck_ranking(result)
    findings: list[str] = []
    if ranking.empty:
        return ["No operational stages contained measurable demand in this run."]
    top = ranking.iloc[0]
    findings.append(
        f"{top.department} ranked first with a bottleneck score of {top.bottleneck_score:.1f}/100, "
        f"a peak queue of {int(top.maximum_queue)}, and a longest wait of {top.longest_wait:.1f} minutes."
    )
    high_util = ranking.loc[ranking["resource_utilisation"] >= 0.9]
    if len(high_util):
        row = high_util.iloc[0]
        findings.append(
            f"{row.department} resource utilisation reached {row.resource_utilisation:.0%}; "
            f"its queue remained above configured capacity for {row.minutes_above_capacity:.0f} sampled minutes."
        )
    doctor_rows = ranking.loc[ranking["department"].isin(["Initial consultation", "Return consultation"])]
    return_rows = ranking.loc[ranking["department"] == "Return consultation"]
    if len(return_rows) and int(return_rows.iloc[0].affected_patients):
        initial_demand = int(doctor_rows.loc[doctor_rows["department"] == "Initial consultation", "affected_patients"].sum())
        return_demand = int(return_rows.iloc[0].affected_patients)
        share = return_demand / max(1, initial_demand + return_demand)
        peak_queue = int(return_rows.iloc[0].maximum_queue)
        if peak_queue:
            findings.append(
                f"Return consultations represented {share:.0%} of measured doctor-queue demand "
                f"and peaked at {peak_queue} waiting patients."
            )
        else:
            findings.append(
                f"Return consultations represented {share:.0%} of measured doctor-queue demand "
                "without forming a sustained return-consultation queue."
            )
    seats = float(result.metrics.get("percentage_waiting_periods_without_seat", 0.0))
    if seats > 0:
        if top.department in {"Initial consultation", "Return consultation"}:
            findings.append(
                f"{seats:.1f}% of waiting periods had no seat. More seats could improve comfort, but the leading delay was doctor capacity."
            )
        else:
            findings.append(f"{seats:.1f}% of waiting periods had no available seat, directly affecting comfort scores.")
    if len(findings) < 3:
        findings.append(
            f"Average total waiting time was {float(result.metrics.get('average_total_waiting_time', 0)):.1f} minutes "
            f"and final satisfaction averaged {float(result.metrics.get('average_final_satisfaction', 0)):.1f}/100."
        )
    return findings


def result_summary_frame(result: Any) -> pd.DataFrame:
    """Return a tidy two-column summary suitable for CSV/report export."""
    labels = {
        "total_patients_scheduled": "Scheduled patients",
        "total_patients_arriving": "Arrived patients",
        "completed_patients": "Completed patients",
        "patients_unfinished_at_closing": "Unfinished at closing",
        "average_total_waiting_time": "Average total waiting time (min)",
        "p90_total_waiting_time": "90th percentile waiting time (min)",
        "average_total_visit_duration": "Average visit duration (min)",
        "average_final_satisfaction": "Average final satisfaction",
        "patients_below_satisfaction_60": "Patients below satisfaction 60",
        "overtime_duration": "Overtime duration (min)",
    }
    return pd.DataFrame(
        [{"metric": label, "value": result.metrics.get(key, 0)} for key, label in labels.items()]
    )
