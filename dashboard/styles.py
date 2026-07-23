"""Shared Streamlit styling for the management-simulation interface."""

from __future__ import annotations

import streamlit as st


APP_CSS = """
<style>
  :root {
    --pfs-ink: #172033;
    --pfs-muted: #64748b;
    --pfs-panel: #ffffff;
    --pfs-line: #dbe3ec;
    --pfs-accent: #2563eb;
    --pfs-accent-dark: #1d4ed8;
  }
  .stApp { background: #f4f7fb; color: var(--pfs-ink); }
  .block-container { max-width: 1600px; padding-top: 1.2rem; padding-bottom: 2rem; }
  header[data-testid="stHeader"] { background: transparent; }
  section[data-testid="stSidebar"] { display: none; }
  .pfs-kicker { color: #2563eb; font-size: .78rem; font-weight: 800; letter-spacing: .12em; text-transform: uppercase; }
  .pfs-title { font-size: clamp(2rem, 4vw, 3.6rem); line-height: 1; font-weight: 850; letter-spacing: -.04em; margin: .35rem 0 .6rem; }
  .pfs-subtitle { color: var(--pfs-muted); max-width: 760px; font-size: 1.02rem; }
  .pfs-panel { background: var(--pfs-panel); border: 1px solid var(--pfs-line); border-radius: 18px; padding: 1rem 1.1rem; box-shadow: 0 10px 30px rgba(30, 41, 59, .055); }
  .pfs-state-chip { display: inline-flex; align-items: center; gap: .4rem; background: #eaf1ff; color: #1d4ed8; border-radius: 999px; padding: .35rem .7rem; font-weight: 750; font-size: .82rem; }
  .pfs-run-meta { color: var(--pfs-muted); margin-top: -.35rem; margin-bottom: 1rem; }
  .pfs-rank { font-size: 1.1rem; font-weight: 800; color: #1e3a8a; }
  div[data-testid="stMetric"] { background: #fff; border: 1px solid var(--pfs-line); border-radius: 14px; padding: .85rem 1rem; min-height: 102px; }
  div[data-testid="stMetricLabel"] { color: #526178; }
  div[data-testid="stMetricValue"] { color: var(--pfs-ink); }
  div[data-testid="stForm"] { background: #fff; border: 1px solid var(--pfs-line); border-radius: 18px; padding: 1rem 1.15rem; box-shadow: 0 10px 30px rgba(30, 41, 59, .055); }
  div[data-testid="stFormSubmitButton"] button[kind="primary"] {
    min-height: 3.35rem; font-size: 1.08rem; font-weight: 850; border-radius: 12px;
    background: linear-gradient(135deg, var(--pfs-accent), var(--pfs-accent-dark));
    border: none; box-shadow: 0 9px 22px rgba(37, 99, 235, .28);
  }
  div[data-testid="stFormSubmitButton"] button[kind="primary"]:hover { filter: brightness(1.06); }
  .stTabs [data-baseweb="tab-list"] { gap: .25rem; border-bottom: 1px solid var(--pfs-line); }
  .stTabs [data-baseweb="tab"] { padding: .65rem .85rem; }
  @media (max-width: 1000px) {
    .block-container { padding-left: 1rem; padding-right: 1rem; }
    .pfs-title { font-size: 2.3rem; }
  }
</style>
"""


def apply_app_styles() -> None:
    """Inject the small global style layer used by every application state."""
    st.markdown(APP_CSS, unsafe_allow_html=True)
