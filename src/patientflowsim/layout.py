"""Typed, metre-based hospital floor-plan models and persistence helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Iterable


DEPARTMENT_TYPES = {
    "entrance",
    "check-in",
    "triage",
    "initial waiting area",
    "consultation room",
    "laboratory",
    "imaging",
    "return waiting area",
    "exit",
}
WAITING_AREA_TYPES = {"initial waiting area", "return waiting area"}
STATION_TYPES = {
    "check-in",
    "triage",
    "doctor",
    "laboratory",
    "imaging",
    "entry",
    "exit",
    "standing",
}
QUEUE_TYPES = {
    "check_in",
    "triage",
    "initial_consultation",
    "laboratory",
    "imaging",
    "return_check_in",
    "return_consultation",
}

DEFAULT_PATIENT_COLOURS = {
    "arrived_check_in": "#2563eb",
    "waiting_triage": "#eab308",
    "waiting_initial_consultation": "#f97316",
    "consultation": "#7c3aed",
    "travelling_examination": "#06b6d4",
    "examination": "#0e7490",
    "returning_examination": "#ef4444",
    "waiting_return_consultation": "#991b1b",
    "discharged": "#64748b",
}


class LayoutValidationError(ValueError):
    """Raised when an imported or edited floor plan is invalid."""


def _positive(value: float, label: str) -> None:
    if value <= 0:
        raise LayoutValidationError(f"{label} must be greater than zero")


def _inside_canvas(x_m: float, y_m: float, width_m: float, height_m: float, canvas_width_m: float, canvas_height_m: float, label: str) -> None:
    if x_m < 0 or y_m < 0:
        raise LayoutValidationError(f"{label} cannot use negative coordinates")
    if x_m + width_m > canvas_width_m or y_m + height_m > canvas_height_m:
        raise LayoutValidationError(f"{label} must remain inside the canvas")


@dataclass(slots=True)
class Department:
    """Editable rectangular department expressed entirely in metres."""

    id: str
    name: str
    department_type: str
    x_m: float
    y_m: float
    width_m: float
    height_m: float
    fill: str = "#e2e8f0"
    border: str = "#475569"

    def validate(self, canvas_width_m: float, canvas_height_m: float) -> None:
        """Validate type, dimensions, and canvas bounds."""
        if not self.id.strip() or not self.name.strip():
            raise LayoutValidationError("Departments require a non-empty ID and name")
        if self.department_type not in DEPARTMENT_TYPES:
            raise LayoutValidationError(f"Unsupported department type: {self.department_type}")
        _positive(self.width_m, f"Department {self.id} width")
        _positive(self.height_m, f"Department {self.id} height")
        _inside_canvas(self.x_m, self.y_m, self.width_m, self.height_m, canvas_width_m, canvas_height_m, f"Department {self.id}")

    @property
    def centre(self) -> tuple[float, float]:
        """Return the room centre in metres."""
        return self.x_m + self.width_m / 2, self.y_m + self.height_m / 2


@dataclass(slots=True)
class Seat:
    """An independently editable waiting-area seat."""

    id: str
    x_m: float
    y_m: float
    rotation_deg: float = 0.0
    waiting_area_id: str = ""
    available: bool = True
    occupied: bool = False
    patient_id: str | None = None

    def validate(self, layout: "HospitalLayout") -> None:
        """Validate position and waiting-area assignment."""
        if not self.id.strip():
            raise LayoutValidationError("Seats require a non-empty ID")
        _inside_canvas(self.x_m, self.y_m, 0, 0, layout.canvas_width_m, layout.canvas_height_m, f"Seat {self.id}")
        departments = {department.id: department for department in layout.departments}
        if self.waiting_area_id not in departments:
            raise LayoutValidationError(f"Seat {self.id} refers to unknown waiting area {self.waiting_area_id!r}")
        if departments[self.waiting_area_id].department_type not in WAITING_AREA_TYPES:
            raise LayoutValidationError(f"Seat {self.id} must be assigned to a waiting-area department")
        if self.occupied and not self.patient_id:
            raise LayoutValidationError(f"Occupied seat {self.id} requires a patient ID")


@dataclass(slots=True)
class ResourceStation:
    """A visible station mapped to a Python simulation resource."""

    id: str
    station_type: str
    x_m: float
    y_m: float
    department_id: str | None = None
    resource_index: int = 0
    label: str = ""

    def validate(self, layout: "HospitalLayout") -> None:
        """Validate station type, position, and optional department link."""
        if self.station_type not in STATION_TYPES:
            raise LayoutValidationError(f"Unsupported station type: {self.station_type}")
        _inside_canvas(self.x_m, self.y_m, 0, 0, layout.canvas_width_m, layout.canvas_height_m, f"Station {self.id}")
        if self.department_id and self.department_id not in {department.id for department in layout.departments}:
            raise LayoutValidationError(f"Station {self.id} refers to unknown department {self.department_id!r}")
        if self.resource_index < 0:
            raise LayoutValidationError(f"Station {self.id} resource index cannot be negative")


@dataclass(slots=True)
class LayoutPoint:
    """Entry, exit, or stable queue anchor in world coordinates."""

    id: str
    x_m: float
    y_m: float
    point_type: str
    department_id: str | None = None
    direction: str = "vertical"

    def validate(self, layout: "HospitalLayout", allowed_types: Iterable[str]) -> None:
        """Validate point type, bounds, and optional department link."""
        if self.point_type not in set(allowed_types):
            raise LayoutValidationError(f"Unsupported point type: {self.point_type}")
        _inside_canvas(self.x_m, self.y_m, 0, 0, layout.canvas_width_m, layout.canvas_height_m, f"Point {self.id}")
        if self.department_id and self.department_id not in {department.id for department in layout.departments}:
            raise LayoutValidationError(f"Point {self.id} refers to unknown department {self.department_id!r}")


@dataclass(slots=True)
class HospitalLayout:
    """Serializable floor-plan schema shared with the TypeScript component."""

    schema_version: int = 1
    name: str = "Default outpatient clinic"
    canvas_width_m: float = 30.0
    canvas_height_m: float = 20.0
    grid_spacing_m: float = 0.5
    departments: list[Department] = field(default_factory=list)
    seats: list[Seat] = field(default_factory=list)
    resource_stations: list[ResourceStation] = field(default_factory=list)
    entry_points: list[LayoutPoint] = field(default_factory=list)
    exit_points: list[LayoutPoint] = field(default_factory=list)
    queue_points: list[LayoutPoint] = field(default_factory=list)
    colour_settings: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_PATIENT_COLOURS))

    def validate(self) -> None:
        """Validate the complete layout and all cross references."""
        if self.schema_version != 1:
            raise LayoutValidationError(f"Unsupported layout schema version: {self.schema_version}")
        if not self.name.strip():
            raise LayoutValidationError("Layout name cannot be empty")
        _positive(self.canvas_width_m, "Canvas width")
        _positive(self.canvas_height_m, "Canvas height")
        if self.grid_spacing_m not in {0.25, 0.5, 1.0}:
            raise LayoutValidationError("Grid spacing must be 0.25, 0.5, or 1 metre")
        identifiers = [item.id for group in (self.departments, self.seats, self.resource_stations, self.entry_points, self.exit_points, self.queue_points) for item in group]
        if len(identifiers) != len(set(identifiers)):
            raise LayoutValidationError("Every layout object must have a unique ID")
        for department in self.departments:
            department.validate(self.canvas_width_m, self.canvas_height_m)
        for seat in self.seats:
            seat.validate(self)
        for station in self.resource_stations:
            station.validate(self)
        for point in self.entry_points:
            point.validate(self, {"entry"})
        for point in self.exit_points:
            point.validate(self, {"exit"})
        for point in self.queue_points:
            point.validate(self, QUEUE_TYPES)
        unknown_colours = set(self.colour_settings) - set(DEFAULT_PATIENT_COLOURS)
        if unknown_colours:
            raise LayoutValidationError(f"Unknown patient colour states: {', '.join(sorted(unknown_colours))}")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""
        data = asdict(self)
        data["colour_settings"] = {**DEFAULT_PATIENT_COLOURS, **self.colour_settings}
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HospitalLayout":
        """Create and validate a layout from decoded JSON data."""
        if not isinstance(data, dict):
            raise LayoutValidationError("Layout JSON must contain an object at the top level")
        try:
            layout = cls(
                schema_version=int(data.get("schema_version", 1)),
                name=str(data.get("name", "Unnamed layout")),
                canvas_width_m=float(data.get("canvas_width_m", 30)),
                canvas_height_m=float(data.get("canvas_height_m", 20)),
                grid_spacing_m=float(data.get("grid_spacing_m", 0.5)),
                departments=[Department(**item) for item in data.get("departments", [])],
                seats=[Seat(**item) for item in data.get("seats", [])],
                resource_stations=[ResourceStation(**item) for item in data.get("resource_stations", [])],
                entry_points=[LayoutPoint(**item) for item in data.get("entry_points", [])],
                exit_points=[LayoutPoint(**item) for item in data.get("exit_points", [])],
                queue_points=[LayoutPoint(**item) for item in data.get("queue_points", [])],
                colour_settings={**DEFAULT_PATIENT_COLOURS, **data.get("colour_settings", {})},
            )
        except (TypeError, ValueError) as exc:
            raise LayoutValidationError(f"Invalid layout field: {exc}") from exc
        layout.validate()
        return layout

    def overlap_warnings(self) -> list[str]:
        """Return readable department-overlap warnings without changing geometry."""
        warnings: list[str] = []
        for index, first in enumerate(self.departments):
            for second in self.departments[index + 1 :]:
                separated = (
                    first.x_m + first.width_m <= second.x_m
                    or second.x_m + second.width_m <= first.x_m
                    or first.y_m + first.height_m <= second.y_m
                    or second.y_m + second.height_m <= first.y_m
                )
                if not separated:
                    warnings.append(f"Departments {first.name!r} and {second.name!r} overlap")
        return warnings

    def station_capacity_warnings(self, resources: Any) -> list[str]:
        """Compare visible stations with configured simulation capacity."""
        mapping = {
            "doctor": ("doctors", "doctor workstations"),
            "triage": ("triage_nurses", "triage stations"),
            "check-in": ("check_in_staff", "check-in stations"),
            "laboratory": ("laboratory_capacity", "laboratory stations"),
            "imaging": ("imaging_capacity", "imaging stations"),
        }
        warnings: list[str] = []
        for station_type, (resource_name, label) in mapping.items():
            visible = sum(station.station_type == station_type for station in self.resource_stations)
            required = int(getattr(resources, resource_name))
            if visible < required:
                warnings.append(f"Layout has {visible} {label}, but the simulation is configured for {required}")
        return warnings


def default_layout_path() -> Path:
    """Return the repository's bundled default-layout path."""
    return Path(__file__).resolve().parents[2] / "config" / "default_layout.json"


def load_layout(path: str | Path | None = None) -> HospitalLayout:
    """Load and validate a layout JSON file."""
    source = Path(path) if path is not None else default_layout_path()
    try:
        data = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise LayoutValidationError(f"Unable to load layout {source}: {exc}") from exc
    return HospitalLayout.from_dict(data)


def save_layout(layout: HospitalLayout, path: str | Path) -> Path:
    """Validate and save a layout as indented JSON."""
    layout.validate()
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(layout.to_dict(), indent=2) + "\n", encoding="utf-8")
    return destination


def layout_from_json(raw: str | bytes) -> HospitalLayout:
    """Parse a layout from uploaded JSON and return readable validation errors."""
    try:
        data = json.loads(raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise LayoutValidationError(f"Invalid layout JSON: {exc}") from exc
    return HospitalLayout.from_dict(data)


def layout_to_json(layout: HospitalLayout) -> str:
    """Serialize a validated layout for downloads or component communication."""
    layout.validate()
    return json.dumps(layout.to_dict(), indent=2)
