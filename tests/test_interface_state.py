"""Contract tests for the uncluttered three-screen workflow."""

import pytest

from dashboard.app_state import AppState, transition
from dashboard.setup_screen import ADVANCED_SETTINGS_EXPANDED, PRIMARY_ACTION_LABEL


def test_setup_has_one_clear_primary_action_and_collapsed_advanced_settings():
    assert PRIMARY_ACTION_LABEL == "Start Simulation"
    assert ADVANCED_SETTINGS_EXPANDED is False


def test_application_state_transitions_are_explicit():
    assert transition(AppState.SETUP, AppState.LIVE) == AppState.LIVE
    assert transition(AppState.LIVE, AppState.RESULTS) == AppState.RESULTS
    assert transition(AppState.RESULTS, AppState.LIVE) == AppState.LIVE
    with pytest.raises(ValueError, match="Cannot transition"):
        transition(AppState.SETUP, AppState.RESULTS)
