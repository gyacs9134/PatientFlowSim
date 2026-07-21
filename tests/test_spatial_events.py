"""Tests for deterministic event-log-to-animation conversion."""

import json

import pytest

from patientflowsim.animation import (
    DOCTOR_SHAPE,
    NURSE_SHAPE,
    PATIENT_SHAPE,
    frame_at_time,
    satisfaction_border,
    shape_for_role,
)
from patientflowsim.config import load_config
from patientflowsim.layout import load_layout
from patientflowsim.simulation import run_simulation
from patientflowsim.spatial_events import prepare_spatial_timeline, stable_queue_position


@pytest.fixture(scope="module")
def timeline():
    result = run_simulation(load_config("config/default_config.yaml"))
    layout = load_layout("config/default_layout.json")
    return prepare_spatial_timeline(result.events, result.patients, layout)


def test_character_shapes_are_immutable(timeline):
    assert shape_for_role("patient") == PATIENT_SHAPE == "circle"
    assert shape_for_role("nurse") == NURSE_SHAPE == "triangle"
    assert shape_for_role("doctor") == DOCTOR_SHAPE == "square"
    assert {patient["shape"] for patient in timeline["patients"]} == {"circle"}
    assert {staff["shape"] for staff in timeline["staff"] if staff["role"] == "nurse"} == {"triangle"}
    assert {staff["shape"] for staff in timeline["staff"] if staff["role"] == "doctor"} == {"square"}


def test_patient_state_changes_colour_mapping_not_shape(timeline):
    patient = timeline["patients"][0]
    assert all(patient["shape"] == "circle" for _ in patient["keyframes"])
    assert timeline["colours"]["arrived_check_in"] != timeline["colours"]["discharged"]


def test_satisfaction_changes_border_not_fill_mapping(timeline):
    assert satisfaction_border(80) == "#334155"
    assert satisfaction_border(50) == "#eab308"
    assert satisfaction_border(20) == "#dc2626"
    original_colours = dict(timeline["colours"])
    frame_at_time(timeline, timeline["duration"])
    assert timeline["colours"] == original_colours


def test_stable_queue_positions_are_ordered_and_repeatable():
    layout = load_layout("config/default_layout.json")
    positions = [stable_queue_position(layout, "check_in", index) for index in range(5)]
    assert positions == [stable_queue_position(layout, "check_in", index) for index in range(5)]
    assert len(set(positions)) == 5


def test_conversion_is_reproducible_for_same_seed():
    config = load_config("config/default_config.yaml")
    layout = load_layout("config/default_layout.json")
    first = run_simulation(config)
    second = run_simulation(config)
    first_timeline = prepare_spatial_timeline(first.events, first.patients, layout)
    second_timeline = prepare_spatial_timeline(second.events, second.patients, layout)
    assert json.dumps(first_timeline, sort_keys=True) == json.dumps(second_timeline, sort_keys=True)


def test_live_counts_and_seat_release_match_frame_state(timeline):
    final = frame_at_time(timeline, timeline["duration"])
    assert sum(final["counts"].values()) == len(timeline["patients"])
    assert final["counts"]["discharged"] == len(timeline["patients"])
    assert not final["occupied_seats"]
    assert all(not seat["occupied"] for seat in final["seats"])
    assert 0 <= final["metrics"]["doctor_utilisation"] <= 1


def test_staff_keyframes_track_busy_status_and_patient(timeline):
    doctor_frames = [frame for staff in timeline["staff"] if staff["role"] == "doctor" for frame in staff["keyframes"]]
    assert any(frame["state"] == "busy" and frame["current_patient"] for frame in doctor_frames)
    assert any(frame["state"] == "available" and frame.get("current_patient") is None for frame in doctor_frames[1:])


def test_no_patients_are_visible_before_their_arrival(timeline):
    first_arrival = min(patient["keyframes"][0]["time"] for patient in timeline["patients"])
    if first_arrival > 0:
        assert not frame_at_time(timeline, first_arrival - 0.001)["patients"]
