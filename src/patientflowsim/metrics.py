"""Patient-level and clinic-wide metric calculation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


RESOURCE_FIELDS = {
    "check_in": "check_in_staff",
    "triage": "triage_nurses",
    "doctors": "doctors",
    "laboratory": "laboratory_capacity",
    "imaging": "imaging_capacity",
}


def _safe_mean(frame: pd.DataFrame, column: str) -> float:
    values = frame[column].dropna() if column in frame else pd.Series(dtype=float)
    return float(values.mean()) if not values.empty else 0.0


def _safe_percentile(frame: pd.DataFrame, column: str, percentile: float) -> float:
    values = frame[column].dropna() if column in frame else pd.Series(dtype=float)
    return float(np.percentile(values, percentile)) if not values.empty else 0.0


def _safe_median(frame: pd.DataFrame, column: str) -> float:
    values = frame[column].dropna() if column in frame else pd.Series(dtype=float)
    return float(values.median()) if not values.empty else 0.0


def calculate_metrics(
    patients: pd.DataFrame,
    events: pd.DataFrame,
    history: list[dict[str, Any]],
    busy: dict[str, float],
    resources: Any,
    end: float,
    closing: float,
) -> dict[str, float | int]:
    """Calculate safe scalar metrics for dashboards and scenario comparison."""
    arrived = patients.loc[~patients["no_show"]].copy()
    complete = arrived.loc[arrived["discharge_time"].notna()].copy()
    unfinished_at_closing = arrived.loc[
        arrived["discharge_time"].isna() | (arrived["discharge_time"] > closing)
    ]

    metric: dict[str, float | int] = {
        "total_patients_scheduled": int(len(patients)),
        "total_patients_arriving": int(len(arrived)),
        "no_show_patients": int(patients["no_show"].sum()),
        "completed_patients": int(len(complete)),
        "patients_unfinished_at_closing": int(len(unfinished_at_closing)),
        "patients_completing_after_closing": int((complete["discharge_time"] > closing).sum()),
        "patients_discharged_before_closing": int((complete["discharge_time"] <= closing).sum()),
        "average_first_check_in_wait": _safe_mean(complete, "first_check_in_wait"),
        "average_triage_wait": _safe_mean(complete, "triage_wait"),
        "average_first_doctor_wait": _safe_mean(complete, "first_doctor_wait"),
        "median_first_doctor_wait": _safe_median(complete, "first_doctor_wait"),
        "p90_first_doctor_wait": _safe_percentile(complete, "first_doctor_wait", 90),
        "average_examination_wait": _safe_mean(complete, "examination_wait"),
        "average_return_check_in_wait": _safe_mean(complete, "return_check_in_wait"),
        "average_return_consultation_wait": _safe_mean(complete, "return_consultation_wait"),
        "median_return_consultation_wait": _safe_median(complete, "return_consultation_wait"),
        "p90_return_consultation_wait": _safe_percentile(complete, "return_consultation_wait", 90),
        "average_total_waiting_time": _safe_mean(complete, "total_waiting_time"),
        "median_total_waiting_time": _safe_median(complete, "total_waiting_time"),
        "p90_total_waiting_time": _safe_percentile(complete, "total_waiting_time", 90),
        "average_total_visit_duration": _safe_mean(complete, "total_time_in_clinic"),
        "average_initial_satisfaction": _safe_mean(arrived, "initial_satisfaction_score"),
        "average_final_satisfaction": _safe_mean(complete, "final_satisfaction_score"),
        "median_final_satisfaction": _safe_median(complete, "final_satisfaction_score"),
        "minimum_final_satisfaction": float(complete["final_satisfaction_score"].min()) if len(complete) else 0.0,
        "maximum_final_satisfaction": float(complete["final_satisfaction_score"].max()) if len(complete) else 0.0,
        "average_satisfaction_change": (
            _safe_mean(complete, "final_satisfaction_score")
            - _safe_mean(complete, "initial_satisfaction_score")
        ),
        "patients_below_satisfaction_60": int((complete["final_satisfaction_score"] < 60).sum()),
        "patients_below_satisfaction_40": int((complete["final_satisfaction_score"] < 40).sum()),
        "percentage_below_60": float((complete["final_satisfaction_score"] < 60).mean() * 100) if len(complete) else 0.0,
        "percentage_below_40": float((complete["final_satisfaction_score"] < 40).mean() * 100) if len(complete) else 0.0,
        "maximum_combined_doctor_queue": int(
            max(
                (item["length"] for item in history if item["queue"] in {"initial_consultation", "return_consultation"}),
                default=0,
            )
        ),
        "overtime_duration": max(0.0, float(complete["discharge_time"].max()) - closing) if len(complete) else 0.0,
        "simulation_end_time": float(end),
    }

    available_minutes = max(float(end), 1.0)
    for name, capacity_field in RESOURCE_FIELDS.items():
        capacity = max(1, int(getattr(resources, capacity_field)))
        metric[f"{name}_utilisation"] = min(1.0, float(busy[name]) / (available_minutes * capacity))
        metric[f"{name}_busy_time"] = float(busy[name])
        metric[f"{name}_idle_capacity_time"] = max(0.0, available_minutes * capacity - float(busy[name]))

    waiting_periods = int(
        complete["first_seat_available"].notna().sum()
        + complete["return_seat_available"].notna().sum()
    )
    periods_without_seat = int(
        (complete["first_seat_available"] == False).sum()  # noqa: E712
        + (complete["return_seat_available"] == False).sum()  # noqa: E712
    )
    metric["waiting_periods_without_seat"] = periods_without_seat
    metric["percentage_waiting_periods_without_seat"] = (
        float(periods_without_seat / waiting_periods * 100) if waiting_periods else 0.0
    )

    with_exam = complete.loc[complete["examination_type"] != "none"]
    without_exam = complete.loc[complete["examination_type"] == "none"]
    metric["average_satisfaction_with_examination"] = _safe_mean(with_exam, "final_satisfaction_score")
    metric["average_satisfaction_without_examination"] = _safe_mean(without_exam, "final_satisfaction_score")
    metric["maximum_seat_occupancy"] = _maximum_seat_occupancy(events)
    return metric


def _maximum_seat_occupancy(events: pd.DataFrame) -> int:
    """Return the maximum concurrent seat count from acquisition/release events."""
    if events.empty or "event_type" not in events:
        return 0
    occupancy = 0
    maximum = 0
    for event in events.sort_values("time", kind="stable").itertuples(index=False):
        if event.event_type == "seat_acquired":
            occupancy += 1
            maximum = max(maximum, occupancy)
        elif event.event_type == "seat_released":
            occupancy = max(0, occupancy - 1)
    return maximum
