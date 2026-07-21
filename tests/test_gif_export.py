"""Tests for bounded server-side GIF generation."""

from io import BytesIO

from PIL import Image
import pytest

from patientflowsim.gif_export import GifExportConfig, render_gif, sampled_frame_times
from patientflowsim.layout import load_layout


def _timeline():
    return {
        "duration": 1.0,
        "colours": {"arrived_check_in": "#2563eb", "discharged": "#64748b"},
        "patients": [{
            "id": "P0001",
            "role": "patient",
            "shape": "circle",
            "details": {},
            "keyframes": [
                {"time": 0, "x_m": 1, "y_m": 1, "state": "arrived_check_in", "satisfaction": 80, "travel_duration_min": 0},
                {"time": 0.5, "x_m": 5, "y_m": 5, "state": "discharged", "satisfaction": 50, "travel_duration_min": 0.5},
            ],
        }],
        "staff": [],
        "seats": [],
    }


def test_gif_export_is_valid_non_empty_and_multiframe():
    config = GifExportConfig(end_time=1, playback_speed=60, fps=10, width=320, height=240, max_frames=4)
    data = render_gif(load_layout("config/default_layout.json"), _timeline(), config)
    assert data.startswith((b"GIF87a", b"GIF89a"))
    assert len(data) > 1000
    image = Image.open(BytesIO(data))
    assert image.n_frames > 1


def test_frame_sampling_obeys_configured_limit():
    config = GifExportConfig(end_time=1, playback_speed=1, fps=20, width=320, height=240, max_frames=7)
    assert len(sampled_frame_times(1, config)) == 7


def test_excessive_export_returns_clear_error():
    config = GifExportConfig(end_time=1, playback_speed=1, fps=20, width=1920, height=1080, max_frames=100)
    with pytest.raises(ValueError, match="too large"):
        sampled_frame_times(1, config)

