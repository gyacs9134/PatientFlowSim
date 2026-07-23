"""Scenario loading and comparable execution with common random numbers."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import yaml

from .config import SimulationConfig, config_from_dict, load_config
from .simulation import run_simulation


COMPARISON_COLUMNS = [
    "scenario",
    "completed_patients",
    "patients_unfinished_at_closing",
    "average_total_waiting_time",
    "p90_total_waiting_time",
    "maximum_combined_doctor_queue",
    "overtime_duration",
    "average_final_satisfaction",
    "percentage_below_60",
    "doctors_utilisation",
    "percentage_waiting_periods_without_seat",
]


def load_scenario_definitions(path: str | Path = "config/scenarios.yaml") -> dict[str, dict[str, Any]]:
    """Load named scenario overrides from YAML."""
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _merge(target: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _merge(target[key], value)
        else:
            target[key] = deepcopy(value)
    return target


def run_scenarios(
    names: Iterable[str],
    path: str | Path = "config/scenarios.yaml",
    base_config: SimulationConfig | None = None,
) -> pd.DataFrame:
    """Run named scenarios against one base population seed and return stable columns."""
    definitions = load_scenario_definitions(path)
    base = (base_config or load_config()).to_dict()
    rows: list[dict[str, Any]] = []
    for name in names:
        if name not in definitions:
            raise ValueError(f"Unknown scenario: {name}")
        candidate = _merge(deepcopy(base), definitions[name])
        result = run_simulation(config_from_dict(candidate))
        rows.append({"scenario": name, **result.metrics})
    frame = pd.DataFrame(rows)
    for column in COMPARISON_COLUMNS:
        if column not in frame:
            frame[column] = 0
    return frame[COMPARISON_COLUMNS]
