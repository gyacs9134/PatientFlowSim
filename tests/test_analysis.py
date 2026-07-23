"""Tests for deterministic end-of-run operational analysis."""

import pandas as pd

from patientflowsim.analysis import (
    calculate_bottleneck_ranking,
    congestion_status,
    identify_replay_periods,
    operational_findings,
    result_summary_frame,
)
from patientflowsim.config import load_config
from patientflowsim.simulation import run_simulation


def test_bottleneck_ranking_is_deterministic_and_explained():
    first = calculate_bottleneck_ranking(run_simulation(load_config()))
    second = calculate_bottleneck_ranking(run_simulation(load_config()))
    pd.testing.assert_frame_equal(first, second)
    assert first["rank"].tolist() == list(range(1, len(first) + 1))
    assert first["bottleneck_score"].is_monotonic_decreasing
    assert (
        first["queue_score"]
        + first["wait_score"]
        + first["utilisation_score"]
        + first["duration_score"]
    ).round(2).equals(first["bottleneck_score"])


def test_congestion_thresholds_are_monotonic():
    assert congestion_status(0, 0, 2, 0.2) == "normal"
    assert congestion_status(3, 5, 2, 0.2) == "busy"
    assert congestion_status(5, 5, 2, 0.2) == "congested"
    assert congestion_status(7, 5, 2, 0.2) == "critical"


def test_replay_periods_and_findings_stay_within_run():
    result = run_simulation(load_config())
    periods = identify_replay_periods(result)
    assert set(periods) == {
        "full_simulation",
        "peak_congestion",
        "examination_return_surge",
        "final_hour",
    }
    assert all(0 <= period["start"] < period["end"] <= result.metrics["simulation_end_time"] for period in periods.values())
    findings = operational_findings(result)
    assert findings
    assert all(isinstance(finding, str) and finding.endswith(".") for finding in findings)


def test_result_export_contains_primary_metrics():
    result = run_simulation(load_config())
    summary = result_summary_frame(result)
    assert list(summary.columns) == ["metric", "value"]
    assert {"Scheduled patients", "Average total waiting time (min)", "Overtime duration (min)"}.issubset(set(summary["metric"]))
