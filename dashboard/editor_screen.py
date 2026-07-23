"""Dedicated floor-plan editing screen, separate from live playback."""

from __future__ import annotations

from typing import Any

import streamlit as st

from .floorplan_tab import current_layout, render_editor, render_layout_management


def render(result: Any = None) -> str | None:
    """Render the editor and return ``back`` when the user closes it."""
    title, action = st.columns([5, 1])
    with title:
        st.markdown('<div class="pfs-kicker">Layout workspace</div>', unsafe_allow_html=True)
        st.title("Floor Plan Editor")
        st.caption("Edit real-world metre coordinates. The saved JSON remains the source for simulation playback and GIF exports.")
    if action.button("← Back", width="stretch"):
        return "back"
    layout = current_layout()
    render_editor(layout, result)
    with st.expander("Layout files · import, export, save and reset", expanded=False):
        render_layout_management(current_layout())
    return None
