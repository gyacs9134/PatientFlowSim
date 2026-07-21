"""Server-side GIF rendering for spatial patient-flow timelines."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from io import BytesIO
from math import ceil
from typing import Any, Callable

from PIL import Image, ImageDraw, ImageFont

try:
    import imageio.v2 as imageio
except ModuleNotFoundError:  # Pillow remains a complete encoder fallback on minimal deployments.
    imageio = None

from .animation import frame_at_time
from .layout import HospitalLayout


@dataclass(slots=True)
class GifExportConfig:
    """Validated options for a bounded simulation GIF export."""

    start_time: float = 0.0
    end_time: float | None = None
    playback_speed: float = 10.0
    fps: int = 10
    width: int = 960
    height: int = 640
    include_patient_ids: bool = False
    include_dimension_labels: bool = False
    include_legend: bool = True
    include_metrics_overlay: bool = True
    include_satisfaction_labels: bool = True
    loop: bool = True
    max_frames: int = 300

    def validate(self, duration: float) -> None:
        """Validate time range, rendering size, and memory guardrails."""
        end = duration if self.end_time is None else self.end_time
        if self.start_time < 0 or end <= self.start_time or end > duration + 1e-6:
            raise ValueError(f"GIF time range must be within 0–{duration:.1f} minutes")
        if self.playback_speed <= 0:
            raise ValueError("GIF playback speed must be greater than zero")
        if self.fps not in {10, 15, 20}:
            raise ValueError("GIF FPS must be 10, 15, or 20")
        if not 320 <= self.width <= 1920 or not 240 <= self.height <= 1080:
            raise ValueError("GIF dimensions must be between 320×240 and 1920×1080")
        if not 2 <= self.max_frames <= 1000:
            raise ValueError("GIF maximum frame count must be between 2 and 1000")


def sampled_frame_times(duration: float, config: GifExportConfig) -> list[float]:
    """Return evenly sampled simulation minutes that obey the frame limit."""
    config.validate(duration)
    end = duration if config.end_time is None else float(config.end_time)
    real_seconds = (end - config.start_time) * 60.0 / config.playback_speed
    requested = max(2, ceil(real_seconds * config.fps))
    count = min(requested, config.max_frames)
    if count * config.width * config.height > 120_000_000:
        raise ValueError(
            "Requested GIF is too large for safe in-memory rendering; reduce dimensions or the maximum frame count"
        )
    step = (end - config.start_time) / (count - 1)
    return [config.start_time + index * step for index in range(count)]


@lru_cache(maxsize=16)
def _font(size: int = 12) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _hex(value: str, fallback: str = "#64748b") -> str:
    return value if isinstance(value, str) and len(value) in {4, 7} and value.startswith("#") else fallback


def _geometry(layout: HospitalLayout, config: GifExportConfig) -> tuple[float, float, float, float]:
    right_panel = 220 if config.include_legend else 0
    top = 12
    available_width = max(1, config.width - right_panel - 24)
    available_height = max(1, config.height - 24)
    scale = min(available_width / layout.canvas_width_m, available_height / layout.canvas_height_m)
    offset_x = 12 + (available_width - layout.canvas_width_m * scale) / 2
    offset_y = top + (available_height - layout.canvas_height_m * scale) / 2
    return scale, offset_x, offset_y, float(right_panel)


def _world(x_m: float, y_m: float, scale: float, offset_x: float, offset_y: float) -> tuple[float, float]:
    return offset_x + x_m * scale, offset_y + y_m * scale


def _draw_layout(draw: ImageDraw.ImageDraw, layout: HospitalLayout, config: GifExportConfig, scale: float, ox: float, oy: float) -> None:
    canvas = (*_world(0, 0, scale, ox, oy), *_world(layout.canvas_width_m, layout.canvas_height_m, scale, ox, oy))
    draw.rectangle(canvas, fill="#f8fafc", outline="#0f172a", width=2)
    for department in layout.departments:
        x1, y1 = _world(department.x_m, department.y_m, scale, ox, oy)
        x2, y2 = _world(department.x_m + department.width_m, department.y_m + department.height_m, scale, ox, oy)
        draw.rectangle((x1, y1, x2, y2), fill=_hex(department.fill, "#e2e8f0"), outline=_hex(department.border, "#475569"), width=2)
        draw.text((x1 + 4, y1 + 3), department.name, fill="#0f172a", font=_font(11))
        if config.include_dimension_labels:
            draw.text((x1 + 4, y2 - 15), f"{department.width_m:g}×{department.height_m:g} m", fill="#334155", font=_font(10))


def _draw_seats(draw: ImageDraw.ImageDraw, seats: list[dict[str, Any]], scale: float, ox: float, oy: float) -> None:
    radius = max(3, min(7, scale * 0.14))
    for seat in seats:
        x, y = _world(float(seat["x_m"]), float(seat["y_m"]), scale, ox, oy)
        fill = "#94a3b8" if not seat.get("available", True) else "#fb7185" if seat.get("occupied") else "#ffffff"
        draw.rectangle((x - radius, y - radius, x + radius, y + radius), fill=fill, outline="#475569", width=1)


def _draw_marker(draw: ImageDraw.ImageDraw, entity: dict[str, Any], colours: dict[str, str], scale: float, ox: float, oy: float, show_id: bool) -> None:
    x, y = _world(float(entity.get("x_m", 0)), float(entity.get("y_m", 0)), scale, ox, oy)
    radius = max(4, min(9, scale * 0.18))
    role = entity.get("role", "patient")
    if role == "patient":
        fill = _hex(colours.get(str(entity.get("state")), "#64748b"))
        outline = _hex(entity.get("border", "#334155"), "#334155")
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=fill, outline=outline, width=3)
    elif role == "nurse":
        draw.polygon(((x, y - radius), (x - radius, y + radius), (x + radius, y + radius)), fill="#22c55e", outline="#14532d")
    else:
        draw.rectangle((x - radius, y - radius, x + radius, y + radius), fill="#1e3a8a", outline="#0f172a", width=2)
    if show_id:
        draw.text((x + radius + 2, y - radius), str(entity.get("id", "")), fill="#0f172a", font=_font(9))


def _draw_legend(draw: ImageDraw.ImageDraw, frame: dict[str, Any], colours: dict[str, str], config: GifExportConfig) -> None:
    if not config.include_legend:
        return
    x = config.width - 210
    draw.rounded_rectangle((x, 12, config.width - 10, config.height - 12), radius=8, fill="#ffffff", outline="#cbd5e1")
    draw.text((x + 12, 22), "Legend", fill="#0f172a", font=_font(16))
    labels = {
        "arrived_check_in": "Arrived / check-in",
        "waiting_triage": "Waiting triage",
        "waiting_initial_consultation": "Waiting initial",
        "consultation": "In consultation",
        "travelling_examination": "To examination",
        "examination": "At examination",
        "returning_examination": "Returning",
        "waiting_return_consultation": "Waiting return",
        "discharged": "Discharged",
    }
    y = 50
    for state, label in labels.items():
        draw.ellipse((x + 12, y, x + 24, y + 12), fill=_hex(colours.get(state, "#64748b")), outline="#334155")
        draw.text((x + 30, y - 2), f"{label}: {frame['counts'].get(state, 0)}", fill="#334155", font=_font(10))
        y += 20
    y += 4
    draw.text((x + 12, y), "○ patient   △ nurse   □ doctor", fill="#334155", font=_font(10))
    y += 22
    draw.text((x + 12, y), "Borders: normal / yellow / red", fill="#334155", font=_font(10))
    y += 22
    draw.text((x + 12, y), "Seats: empty / occupied / unavailable", fill="#334155", font=_font(9))


def _draw_metrics(draw: ImageDraw.ImageDraw, frame: dict[str, Any]) -> None:
    metrics = frame["metrics"]
    text = (
        f"Time {metrics['time']:.1f} min   Inside {metrics['patients_inside']}   "
        f"Initial wait {metrics['waiting_initial_consultation']}   Return wait {metrics['waiting_return_consultation']}   "
        f"Seats {metrics['available_seats']}   Satisfaction {metrics['average_satisfaction']:.1f}   "
        f"Doctors {metrics['doctor_utilisation']:.0%}"
    )
    left, top, right, bottom = draw.textbbox((0, 0), text, font=_font(11))
    draw.rounded_rectangle((14, 14, 26 + right - left, 24 + bottom - top), radius=5, fill="#ffffffdd", outline="#cbd5e1")
    draw.text((20, 18), text, fill="#0f172a", font=_font(11))


def render_frame(layout: HospitalLayout, timeline: dict[str, Any], time_min: float, config: GifExportConfig) -> Image.Image:
    """Render one RGB frame with immutable shape and satisfaction rules."""
    image = Image.new("RGB", (config.width, config.height), "#e2e8f0")
    draw = ImageDraw.Draw(image)
    scale, ox, oy, _ = _geometry(layout, config)
    frame = frame_at_time(timeline, time_min)
    _draw_layout(draw, layout, config, scale, ox, oy)
    _draw_seats(draw, frame["seats"], scale, ox, oy)
    colours = timeline.get("colours", layout.colour_settings)
    for staff in frame["staff"]:
        _draw_marker(draw, staff, colours, scale, ox, oy, config.include_patient_ids)
    for patient in frame["patients"]:
        _draw_marker(draw, patient, colours, scale, ox, oy, config.include_patient_ids)
        event = patient.get("satisfaction_event")
        if config.include_satisfaction_labels and event and time_min - float(event.get("time", 0)) <= 2.0:
            x, y = _world(float(patient["x_m"]), float(patient["y_m"]), scale, ox, oy)
            draw.text((x + 8, y + 8), f"{event.get('score_change', 0):+g} {event.get('event', '')}", fill="#b91c1c", font=_font(9))
    if config.include_metrics_overlay:
        _draw_metrics(draw, frame)
    _draw_legend(draw, frame, colours, config)
    return image


def render_gif(
    layout: HospitalLayout,
    timeline: dict[str, Any],
    config: GifExportConfig | None = None,
    progress_callback: Callable[[float], None] | None = None,
) -> bytes:
    """Render a bounded, non-empty animated GIF and return its bytes."""
    layout.validate()
    options = config or GifExportConfig()
    duration = float(timeline.get("duration", 0))
    times = sampled_frame_times(duration, options)
    frames: list[Image.Image] = []
    for index, time_min in enumerate(times):
        frames.append(render_frame(layout, timeline, time_min, options))
        if progress_callback:
            progress_callback((index + 1) / len(times))
    output = BytesIO()
    palette_frames = [frame.convert("P", palette=Image.Palette.ADAPTIVE) for frame in frames]
    if imageio is not None:
        imageio.mimsave(
            output,
            palette_frames,
            format="GIF",
            duration=1 / options.fps,
            loop=0 if options.loop else 1,
        )
    else:
        save_options: dict[str, Any] = {
            "format": "GIF",
            "save_all": True,
            "append_images": palette_frames[1:],
            "duration": round(1000 / options.fps),
            "disposal": 2,
        }
        if options.loop:
            save_options["loop"] = 0
        palette_frames[0].save(output, **save_options)
    return output.getvalue()
