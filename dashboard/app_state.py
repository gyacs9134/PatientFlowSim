"""Explicit application-state transitions for the three-screen workflow."""

from __future__ import annotations

from enum import StrEnum


class AppState(StrEnum):
    """Top-level interface states shown one at a time."""

    SETUP = "setup"
    LIVE = "live"
    RESULTS = "results"


VALID_TRANSITIONS = {
    AppState.SETUP: {AppState.LIVE},
    AppState.LIVE: {AppState.SETUP, AppState.RESULTS},
    AppState.RESULTS: {AppState.SETUP, AppState.LIVE},
}


def transition(current: str | AppState, target: str | AppState) -> AppState:
    """Validate and return a top-level state transition."""
    current_state = AppState(current)
    target_state = AppState(target)
    if target_state == current_state:
        return current_state
    if target_state not in VALID_TRANSITIONS[current_state]:
        raise ValueError(f"Cannot transition directly from {current_state.value} to {target_state.value}")
    return target_state
