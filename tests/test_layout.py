"""Tests for the shared metre-based floor-plan schema."""

from dataclasses import replace
import json

import pytest

from patientflowsim.layout import (
    HospitalLayout,
    LayoutValidationError,
    Seat,
    layout_from_json,
    load_layout,
    save_layout,
)


def test_default_layout_round_trip_preserves_world_coordinates(tmp_path):
    layout = load_layout("config/default_layout.json")
    destination = save_layout(layout, tmp_path / "clinic.json")
    restored = load_layout(destination)
    assert restored.to_dict() == layout.to_dict()
    assert restored.departments[0].x_m == layout.departments[0].x_m
    assert restored.canvas_width_m == 30


def test_department_dimensions_cannot_be_negative():
    layout = load_layout("config/default_layout.json")
    layout.departments[0] = replace(layout.departments[0], width_m=-1)
    with pytest.raises(LayoutValidationError, match="width must be greater than zero"):
        layout.validate()


def test_seats_must_map_to_a_waiting_area():
    layout = load_layout("config/default_layout.json")
    layout.seats.append(Seat("bad-seat", 1, 1, waiting_area_id="triage"))
    with pytest.raises(LayoutValidationError, match="waiting-area department"):
        layout.validate()


@pytest.mark.parametrize(
    "raw, message",
    [
        ("{not-json", "Invalid layout JSON"),
        (json.dumps({"canvas_width_m": -1}), "Canvas width must be greater than zero"),
        (json.dumps({"schema_version": 99}), "Unsupported layout schema version"),
    ],
)
def test_invalid_imports_have_readable_errors(raw, message):
    with pytest.raises(LayoutValidationError, match=message):
        layout_from_json(raw)


def test_colour_schema_rejects_unknown_patient_state():
    layout = load_layout("config/default_layout.json")
    data = layout.to_dict()
    data["colour_settings"]["unknown"] = "#ffffff"
    with pytest.raises(LayoutValidationError, match="Unknown patient colour states"):
        HospitalLayout.from_dict(data)

