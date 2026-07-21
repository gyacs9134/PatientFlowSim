"""Convert the existing SimPy event log into deterministic spatial keyframes."""

from __future__ import annotations

import ast
from collections import defaultdict
from copy import deepcopy
from math import hypot
from typing import Any

import pandas as pd

from .animation import DOCTOR_SHAPE, NURSE_SHAPE, PATIENT_SHAPE
from .layout import DEFAULT_PATIENT_COLOURS, HospitalLayout, LayoutPoint, ResourceStation


EVENT_STATES = {
    "patient_arrived": "arrived_check_in",
    "first_check_in_started": "arrived_check_in",
    "first_check_in_completed": "waiting_triage",
    "triage_started": "waiting_triage",
    "triage_completed": "waiting_initial_consultation",
    "first_doctor_queue_joined": "waiting_initial_consultation",
    "initial_consultation_started": "consultation",
    "initial_consultation_completed": "consultation",
    "examination_queue_joined": "travelling_examination",
    "examination_started": "examination",
    "examination_completed": "examination",
    "patient_returned": "returning_examination",
    "return_check_in_started": "returning_examination",
    "return_check_in_completed": "waiting_return_consultation",
    "return_doctor_queue_joined": "waiting_return_consultation",
    "return_consultation_started": "consultation",
    "return_consultation_completed": "consultation",
    "patient_discharged": "discharged",
}

QUEUE_JOIN_EVENTS = {
    "patient_arrived": "check_in",
    "first_check_in_completed": "triage",
    "first_doctor_queue_joined": "initial_consultation",
    "examination_queue_joined": None,
    "patient_returned": "return_check_in",
    "return_doctor_queue_joined": "return_consultation",
}
QUEUE_START_EVENTS = {
    "first_check_in_started": "check_in",
    "triage_started": "triage",
    "initial_consultation_started": "initial_consultation",
    "examination_started": None,
    "return_check_in_started": "return_check_in",
    "return_consultation_started": "return_consultation",
}


def stable_queue_position(layout: HospitalLayout, queue_type: str, index: int, spacing_m: float = 0.45) -> tuple[float, float]:
    """Return a stable, non-overlapping position for a queue index."""
    point = next((candidate for candidate in layout.queue_points if candidate.point_type == queue_type), None)
    if point is None:
        point = LayoutPoint(f"fallback_{queue_type}", 1.0, 1.0, queue_type)
    if point.direction == "horizontal":
        return min(layout.canvas_width_m, point.x_m + index * spacing_m), point.y_m
    return point.x_m, min(layout.canvas_height_m, point.y_m + index * spacing_m)


def _patient_number(patient_id: str) -> int:
    digits = "".join(character for character in patient_id if character.isdigit())
    return int(digits or 0)


def _station(layout: HospitalLayout, station_type: str, patient_id: str) -> ResourceStation | None:
    stations = [station for station in layout.resource_stations if station.station_type == station_type]
    if not stations:
        return None
    return stations[_patient_number(patient_id) % len(stations)]


def _department_position(layout: HospitalLayout, department_type: str, patient_id: str) -> tuple[float, float, str | None]:
    departments = [department for department in layout.departments if department.department_type == department_type]
    if not departments:
        return layout.canvas_width_m / 2, layout.canvas_height_m / 2, None
    department = departments[_patient_number(patient_id) % len(departments)]
    x_m, y_m = department.centre
    return x_m, y_m, department.id


def _point_position(points: list[LayoutPoint], fallback: tuple[float, float]) -> tuple[float, float, str | None]:
    if not points:
        return fallback[0], fallback[1], None
    return points[0].x_m, points[0].y_m, points[0].department_id


def _normalise_satisfaction_events(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return value
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        parsed = ast.literal_eval(value)
    except (SyntaxError, ValueError):
        return []
    return parsed if isinstance(parsed, list) else []


def _travel_minutes(previous: dict[str, Any] | None, x_m: float, y_m: float, walking_speed_m_s: float) -> float:
    if previous is None or walking_speed_m_s <= 0:
        return 0.0
    distance = hypot(x_m - float(previous["x_m"]), y_m - float(previous["y_m"]))
    return distance / (walking_speed_m_s * 60.0)


def prepare_spatial_timeline(
    events: pd.DataFrame,
    patients: pd.DataFrame,
    layout: HospitalLayout,
    walking_speed_m_s: float = 1.2,
) -> dict[str, Any]:
    """Prepare browser-ready keyframes from the event log without resimulating care."""
    layout.validate()
    if walking_speed_m_s <= 0:
        raise ValueError("Walking speed must be greater than zero")
    ordered = events.copy()
    if ordered.empty:
        return {
            "duration": 0.0,
            "patients": [],
            "staff": _staff_entities(layout),
            "seats": [as_seat_dict(seat) for seat in layout.seats],
            "colours": dict(layout.colour_settings),
            "resource_capacity": _resource_capacity(layout),
            "resource_intervals": {"doctors": [], "triage_nurses": []},
        }
    ordered["_order"] = range(len(ordered))
    ordered = ordered.sort_values(["time", "_order"], kind="stable")
    patient_rows = {str(row.patient_id): row._asdict() for row in patients.itertuples(index=False)}
    keyframes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    queues: dict[str, list[str]] = defaultdict(list)
    patient_queue: dict[str, str] = {}
    assigned_seats: dict[str, str] = {}
    seat_users: dict[str, str] = {}
    return_phase: set[str] = set()

    def add_keyframe(patient_id: str, time: float, state: str, x_m: float, y_m: float, department_id: str | None, **extra: Any) -> None:
        previous = keyframes[patient_id][-1] if keyframes[patient_id] else None
        score = float(extra.pop("satisfaction", previous.get("satisfaction", 80) if previous else 80))
        travel_duration = extra.pop("travel_duration_min", None)
        keyframe = {
            "time": float(time),
            "x_m": round(float(x_m), 5),
            "y_m": round(float(y_m), 5),
            "state": state,
            "department_id": department_id,
            "satisfaction": score,
            "seat_id": extra.pop("seat_id", assigned_seats.get(patient_id)),
            "travel_duration_min": round(
                _travel_minutes(previous, x_m, y_m, walking_speed_m_s)
                if travel_duration is None
                else float(travel_duration),
                6,
            ),
            **extra,
        }
        keyframes[patient_id].append(keyframe)

    def remove_from_queue(patient_id: str, queue_type: str, time: float) -> None:
        if patient_id in queues[queue_type]:
            queues[queue_type].remove(patient_id)
        patient_queue.pop(patient_id, None)
        for index, queued_patient in enumerate(queues[queue_type]):
            if not keyframes[queued_patient]:
                continue
            x_m, y_m = stable_queue_position(layout, queue_type, index)
            previous = keyframes[queued_patient][-1]
            add_keyframe(queued_patient, time, previous["state"], x_m, y_m, previous.get("department_id"), queue_position=index)

    for event in ordered.itertuples(index=False):
        patient_id = str(event.patient_id)
        event_type = str(event.event_type)
        if patient_id not in patient_rows or event_type == "no_show":
            continue
        time = float(event.time)
        satisfaction = float(getattr(event, "patient_satisfaction", 80) or 80)
        if event_type == "patient_returned":
            return_phase.add(patient_id)

        start_queue = QUEUE_START_EVENTS.get(event_type)
        if event_type == "examination_started":
            start_queue = str(event.department)
        if start_queue:
            remove_from_queue(patient_id, start_queue, time)

        join_queue = QUEUE_JOIN_EVENTS.get(event_type)
        if event_type == "examination_queue_joined":
            join_queue = str(event.department)
        if join_queue:
            if patient_id not in queues[join_queue]:
                queues[join_queue].append(patient_id)
            patient_queue[patient_id] = join_queue

        previous_state = keyframes[patient_id][-1]["state"] if keyframes[patient_id] else "arrived_check_in"
        state = EVENT_STATES.get(event_type, previous_state)

        if event_type == "seat_acquired":
            waiting_id = "return_wait" if patient_id in return_phase else "initial_wait"
            candidates = [seat for seat in layout.seats if seat.waiting_area_id == waiting_id and seat.available and seat.id not in seat_users]
            if candidates:
                selected = candidates[0]
                assigned_seats[patient_id] = selected.id
                seat_users[selected.id] = patient_id
                state = "waiting_return_consultation" if patient_id in return_phase else "waiting_initial_consultation"
                add_keyframe(patient_id, time, state, selected.x_m, selected.y_m, selected.waiting_area_id, satisfaction=satisfaction, seat_id=selected.id)
            continue
        if event_type == "seat_released":
            seat_id = assigned_seats.pop(patient_id, None)
            if seat_id:
                seat_users.pop(seat_id, None)
            if keyframes[patient_id]:
                previous = keyframes[patient_id][-1]
                add_keyframe(patient_id, time, previous["state"], previous["x_m"], previous["y_m"], previous.get("department_id"), satisfaction=satisfaction, seat_id=None)
            continue
        if event_type in {"no_seat_available", "satisfaction_changed"}:
            if keyframes[patient_id]:
                previous = keyframes[patient_id][-1]
                add_keyframe(patient_id, time, previous["state"], previous["x_m"], previous["y_m"], previous.get("department_id"), satisfaction=satisfaction, label=event_type)
            continue

        department_id: str | None = None
        if join_queue:
            x_m, y_m = stable_queue_position(layout, join_queue, queues[join_queue].index(patient_id))
            point = next((point for point in layout.queue_points if point.point_type == join_queue), None)
            department_id = point.department_id if point else None
        elif event_type == "patient_arrived":
            x_m, y_m, department_id = _point_position(layout.entry_points, (0.5, layout.canvas_height_m / 2))
        elif event_type in {"first_check_in_started", "return_check_in_started"}:
            station = _station(layout, "check-in", patient_id)
            x_m, y_m, department_id = (station.x_m, station.y_m, station.department_id) if station else _department_position(layout, "check-in", patient_id)
        elif event_type == "triage_started":
            station = _station(layout, "triage", patient_id)
            x_m, y_m, department_id = (station.x_m, station.y_m, station.department_id) if station else _department_position(layout, "triage", patient_id)
        elif event_type in {"initial_consultation_started", "initial_consultation_completed", "return_consultation_started", "return_consultation_completed"}:
            station = _station(layout, "doctor", patient_id)
            x_m, y_m, department_id = (station.x_m, station.y_m, station.department_id) if station else _department_position(layout, "consultation room", patient_id)
        elif event_type in {"examination_started", "examination_completed"}:
            station_type = str(event.department)
            station = _station(layout, station_type, patient_id)
            x_m, y_m, department_id = (station.x_m, station.y_m, station.department_id) if station else _department_position(layout, station_type, patient_id)
        elif event_type == "patient_returned":
            x_m, y_m = stable_queue_position(layout, "return_check_in", queues["return_check_in"].index(patient_id))
            point = next((point for point in layout.queue_points if point.point_type == "return_check_in"), None)
            department_id = point.department_id if point else None
        elif event_type == "patient_discharged":
            x_m, y_m, department_id = _point_position(layout.exit_points, (layout.canvas_width_m - 0.5, layout.canvas_height_m / 2))
        elif keyframes[patient_id]:
            previous = keyframes[patient_id][-1]
            x_m, y_m, department_id = previous["x_m"], previous["y_m"], previous.get("department_id")
        else:
            x_m, y_m, department_id = _point_position(layout.entry_points, (0.5, layout.canvas_height_m / 2))

        add_keyframe(patient_id, time, state, x_m, y_m, department_id, satisfaction=satisfaction, queue_position=(queues[join_queue].index(patient_id) if join_queue else None))

    for patient_id, row in patient_rows.items():
        patient_keyframes = keyframes.get(patient_id)
        if not patient_keyframes:
            continue
        satisfaction_events = sorted(_normalise_satisfaction_events(row.get("satisfaction_events")), key=lambda item: float(item.get("time", 0)))
        running_score = float(row.get("initial_satisfaction_score", 80) or 80)
        for satisfaction_event in satisfaction_events:
            event_time = float(satisfaction_event.get("time", 0))
            running_score = max(0.0, min(100.0, running_score + float(satisfaction_event.get("score_change", 0))))
            matching = next(
                (keyframe for keyframe in reversed(patient_keyframes) if abs(float(keyframe["time"]) - event_time) < 1e-6),
                None,
            )
            if matching is not None:
                matching["satisfaction_event"] = deepcopy(satisfaction_event)
                matching.setdefault("satisfaction_events_at_time", []).append(deepcopy(satisfaction_event))
                matching["satisfaction"] = running_score
                continue
            prior = max(
                (keyframe for keyframe in patient_keyframes if keyframe["time"] <= event_time),
                key=lambda item: item["time"],
                default=patient_keyframes[0],
            )
            add_keyframe(
                patient_id,
                event_time,
                prior["state"],
                prior["x_m"],
                prior["y_m"],
                prior.get("department_id"),
                satisfaction=running_score,
                seat_id=prior.get("seat_id"),
                satisfaction_event=deepcopy(satisfaction_event),
                satisfaction_events_at_time=[deepcopy(satisfaction_event)],
                travel_duration_min=0.0,
            )
        patient_keyframes.sort(key=lambda item: item["time"])
        event_index = 0
        running_score = float(row.get("initial_satisfaction_score", 80) or 80)
        for keyframe in patient_keyframes:
            while event_index < len(satisfaction_events) and float(satisfaction_events[event_index].get("time", 0)) <= float(keyframe["time"]) + 1e-6:
                running_score = max(
                    0.0,
                    min(100.0, running_score + float(satisfaction_events[event_index].get("score_change", 0))),
                )
                event_index += 1
            keyframe["satisfaction"] = running_score

    patient_entities = []
    for patient_id in sorted(keyframes):
        row = patient_rows[patient_id]
        patient_entities.append({
            "id": patient_id,
            "role": "patient",
            "shape": PATIENT_SHAPE,
            "keyframes": keyframes[patient_id],
            "details": {
                "appointment_time": row.get("appointment_time"),
                "first_waiting_time": row.get("total_first_waiting_time", 0),
                "return_waiting_time": row.get("total_return_waiting_time", 0),
                "total_waiting_time": row.get("total_waiting_time", 0),
                "examination_type": row.get("examination_type", "none"),
                "satisfaction_events": _normalise_satisfaction_events(row.get("satisfaction_events")),
            },
        })
    return {
        "schema_version": 1,
        "duration": float(ordered["time"].max()),
        "walking_speed_m_s": float(walking_speed_m_s),
        "patients": patient_entities,
        "staff": _staff_entities(layout, ordered),
        "seats": [as_seat_dict(seat) for seat in layout.seats],
        "colours": {**DEFAULT_PATIENT_COLOURS, **layout.colour_settings},
        "shape_rules": {"patient": PATIENT_SHAPE, "nurse": NURSE_SHAPE, "doctor": DOCTOR_SHAPE},
        "resource_capacity": _resource_capacity(layout),
        "resource_intervals": _resource_intervals(ordered),
    }


def _resource_capacity(layout: HospitalLayout) -> dict[str, int]:
    return {
        "doctors": sum(station.station_type == "doctor" for station in layout.resource_stations),
        "triage_nurses": sum(station.station_type == "triage" for station in layout.resource_stations),
    }


def _resource_intervals(events: pd.DataFrame) -> dict[str, list[list[float]]]:
    event_groups = {
        "doctors": {
            "initial_consultation_started": "initial",
            "initial_consultation_completed": "initial",
            "return_consultation_started": "return",
            "return_consultation_completed": "return",
        },
        "triage_nurses": {"triage_started": "triage", "triage_completed": "triage"},
    }
    intervals: dict[str, list[list[float]]] = {name: [] for name in event_groups}
    for resource_name, mapping in event_groups.items():
        starts: dict[tuple[str, str], float] = {}
        for event in events.itertuples(index=False):
            event_type = str(event.event_type)
            if event_type not in mapping:
                continue
            key = (str(event.patient_id), mapping[event_type])
            if event_type.endswith("_started"):
                starts[key] = float(event.time)
            elif key in starts:
                intervals[resource_name].append([starts.pop(key), float(event.time)])
    return intervals


def _staff_entities(layout: HospitalLayout, events: pd.DataFrame | None = None) -> list[dict[str, Any]]:
    staff: list[dict[str, Any]] = []
    for station in layout.resource_stations:
        if station.station_type == "triage":
            role, shape, prefix = "nurse", NURSE_SHAPE, "N"
        elif station.station_type == "doctor":
            role, shape, prefix = "doctor", DOCTOR_SHAPE, "D"
        else:
            continue
        staff.append({
            "id": f"{prefix}{station.resource_index + 1:02d}",
            "role": role,
            "shape": shape,
            "station_id": station.id,
            "keyframes": [{"time": 0.0, "x_m": station.x_m, "y_m": station.y_m, "state": "available", "department_id": station.department_id, "travel_duration_min": 0.0}],
            "details": {"assigned_station": station.id, "status": "available", "current_patient": None, "utilisation_so_far": 0.0},
        })
    if events is None or events.empty:
        return staff
    by_role = {
        "nurse": [entity for entity in staff if entity["role"] == "nurse"],
        "doctor": [entity for entity in staff if entity["role"] == "doctor"],
    }
    start_roles = {
        "triage_started": "nurse",
        "initial_consultation_started": "doctor",
        "return_consultation_started": "doctor",
    }
    complete_roles = {
        "triage_completed": "nurse",
        "initial_consultation_completed": "doctor",
        "return_consultation_completed": "doctor",
    }
    active: dict[tuple[str, str], tuple[dict[str, Any], float]] = {}
    busy_minutes = {entity["id"]: 0.0 for entity in staff}
    for event in events.itertuples(index=False):
        event_type = str(event.event_type)
        patient_id = str(event.patient_id)
        time = float(event.time)
        if event_type in start_roles:
            role = start_roles[event_type]
            used_ids = {entity["id"] for (active_role, _), (entity, _) in active.items() if active_role == role}
            available = next((entity for entity in by_role[role] if entity["id"] not in used_ids), None)
            if available is None:
                continue
            active[(role, patient_id)] = (available, time)
            available["keyframes"].append({
                "time": time,
                "x_m": available["keyframes"][0]["x_m"],
                "y_m": available["keyframes"][0]["y_m"],
                "state": "busy",
                "department_id": available["keyframes"][0]["department_id"],
                "current_patient": patient_id,
                "utilisation_so_far": busy_minutes[available["id"]] / max(time, 1e-9),
                "travel_duration_min": 0.0,
            })
        elif event_type in complete_roles:
            role = complete_roles[event_type]
            assignment = active.pop((role, patient_id), None)
            if assignment is None:
                continue
            available, started = assignment
            busy_minutes[available["id"]] += max(0.0, time - started)
            available["keyframes"].append({
                "time": time,
                "x_m": available["keyframes"][0]["x_m"],
                "y_m": available["keyframes"][0]["y_m"],
                "state": "available",
                "department_id": available["keyframes"][0]["department_id"],
                "current_patient": None,
                "utilisation_so_far": busy_minutes[available["id"]] / max(time, 1e-9),
                "travel_duration_min": 0.0,
            })
    return staff


def as_seat_dict(seat: Any) -> dict[str, Any]:
    """Return the frontend seat representation without mutating the layout."""
    return {
        "id": seat.id,
        "x_m": float(seat.x_m),
        "y_m": float(seat.y_m),
        "rotation_deg": float(seat.rotation_deg),
        "waiting_area_id": seat.waiting_area_id,
        "available": bool(seat.available),
        "occupied": bool(seat.occupied),
        "patient_id": seat.patient_id,
    }
