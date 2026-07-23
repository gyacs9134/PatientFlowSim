"""Pure helpers for interpolating spatial timelines and deriving live overlays."""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
from math import hypot
from typing import Any


PATIENT_SHAPE = "circle"
NURSE_SHAPE = "triangle"
DOCTOR_SHAPE = "square"
SATISFACTION_BORDERS = {
    "normal": "#334155",
    "warning": "#eab308",
    "critical": "#dc2626",
}


def shape_for_role(role: str) -> str:
    """Return the immutable marker shape for a patient, nurse, or doctor."""
    shapes = {"patient": PATIENT_SHAPE, "nurse": NURSE_SHAPE, "doctor": DOCTOR_SHAPE}
    if role not in shapes:
        raise ValueError(f"Unsupported animated role: {role}")
    return shapes[role]


def satisfaction_border(score: float) -> str:
    """Map satisfaction to a border colour without changing workflow fill colour."""
    if score < 40:
        return SATISFACTION_BORDERS["critical"]
    if score < 60:
        return SATISFACTION_BORDERS["warning"]
    return SATISFACTION_BORDERS["normal"]


def _current_keyframe(keyframes: list[dict[str, Any]], time_min: float) -> tuple[dict[str, Any], dict[str, Any] | None]:
    current_index = 0
    for index, keyframe in enumerate(keyframes):
        if float(keyframe["time"]) > time_min:
            break
        current_index = index
    previous = keyframes[current_index - 1] if current_index > 0 else None
    return keyframes[current_index], previous


def _point_along_path(path: list[dict[str, Any]], progress: float) -> tuple[float, float]:
    """Interpolate a point along a polyline using distance-weighted segments."""
    if not path:
        return 0.0, 0.0
    if len(path) == 1:
        return float(path[0]["x_m"]), float(path[0]["y_m"])
    lengths = [
        hypot(float(second["x_m"]) - float(first["x_m"]), float(second["y_m"]) - float(first["y_m"]))
        for first, second in zip(path, path[1:])
    ]
    total = sum(lengths)
    if total <= 0:
        return float(path[-1]["x_m"]), float(path[-1]["y_m"])
    remaining = min(1.0, max(0.0, progress)) * total
    for index, length in enumerate(lengths):
        if remaining <= length:
            fraction = remaining / length if length else 1.0
            return (
                float(path[index]["x_m"]) + (float(path[index + 1]["x_m"]) - float(path[index]["x_m"])) * fraction,
                float(path[index]["y_m"]) + (float(path[index + 1]["y_m"]) - float(path[index]["y_m"])) * fraction,
            )
        remaining -= length
    return float(path[-1]["x_m"]), float(path[-1]["y_m"])


def interpolate_entity(entity: dict[str, Any], time_min: float) -> dict[str, Any]:
    """Return an entity state at a simulation minute using waypoint movement."""
    keyframes = entity.get("keyframes", [])
    if not keyframes:
        return deepcopy(entity)
    if time_min < float(keyframes[0]["time"]):
        return {**deepcopy(entity), "visible": False, "shape": shape_for_role(entity.get("role", "patient"))}
    current, previous = _current_keyframe(keyframes, time_min)
    state = {**entity, **deepcopy(current)}
    state["visible"] = True
    travel_duration = float(current.get("travel_duration_min", 0.0))
    elapsed = time_min - float(current["time"])
    source = current.get("source_location") or previous
    if source is not None and travel_duration > 0 and 0 <= elapsed < travel_duration:
        progress = min(1.0, max(0.0, elapsed / travel_duration))
        path = current.get("path") or [source, current]
        state["x_m"], state["y_m"] = _point_along_path(path, progress)
        state["moving"] = True
    else:
        state["moving"] = False
    state["shape"] = shape_for_role(entity.get("role", "patient"))
    if entity.get("role") == "patient":
        state["border"] = satisfaction_border(float(state.get("satisfaction", 80)))
    return state


def frame_at_time(timeline: dict[str, Any], time_min: float) -> dict[str, Any]:
    """Build one deterministic animation frame for browser playback or GIF rendering."""
    duration = float(timeline.get("duration", 0))
    current_time = min(max(0.0, float(time_min)), duration)
    patients = [
        state
        for entity in timeline.get("patients", [])
        if (state := interpolate_entity(entity, current_time)).get("visible", True)
    ]
    staff = [
        state
        for entity in timeline.get("staff", [])
        if (state := interpolate_entity(entity, current_time)).get("visible", True)
    ]
    occupied = {patient.get("seat_id"): patient["id"] for patient in patients if patient.get("seat_id")}
    seats = []
    for seat in timeline.get("seats", []):
        rendered = dict(seat)
        rendered["occupied"] = seat["id"] in occupied
        rendered["patient_id"] = occupied.get(seat["id"])
        seats.append(rendered)
    counts = legend_counts(patients)
    inside = sum(patient.get("state") != "discharged" for patient in patients)
    satisfaction = [float(patient.get("satisfaction", 80)) for patient in patients if patient.get("state") != "discharged"]
    doctor_capacity = int(timeline.get("resource_capacity", {}).get("doctors", 0))
    doctor_busy = sum(
        max(0.0, min(current_time, float(end)) - float(start))
        for start, end in timeline.get("resource_intervals", {}).get("doctors", [])
        if float(start) < current_time
    )
    metrics = {
        "time": current_time,
        "patients_inside": inside,
        "available_seats": sum(seat.get("available", True) and not seat["occupied"] for seat in seats),
        "average_satisfaction": sum(satisfaction) / len(satisfaction) if satisfaction else 0.0,
        "doctor_utilisation": doctor_busy / (doctor_capacity * current_time) if doctor_capacity and current_time else 0.0,
        **counts,
    }
    return {
        "time": current_time,
        "patients": patients,
        "staff": staff,
        "seats": seats,
        "occupied_seats": occupied,
        "counts": counts,
        "metrics": metrics,
    }


def legend_counts(patients: list[dict[str, Any]]) -> dict[str, int]:
    """Count current patient workflow states for the fixed legend."""
    counter = Counter(patient.get("state", "arrived_check_in") for patient in patients)
    return {state: int(counter.get(state, 0)) for state in (
        "arrived_check_in",
        "waiting_triage",
        "waiting_initial_consultation",
        "consultation",
        "travelling_examination",
        "examination",
        "returning_examination",
        "waiting_return_consultation",
        "discharged",
    )}
