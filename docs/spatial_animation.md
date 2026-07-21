# Spatial animation

The existing SimPy event log remains the source of truth. `prepare_spatial_timeline` assigns each logged patient event to a department centre, resource station, seat, entry/exit point, or stable queue anchor. JavaScript receives this prepared timeline and performs only interpolation and playback; it never runs an independent care simulation.

Patients are always circles. Fill colour represents workflow state: arrival/check-in, triage wait, initial wait, consultation, examination travel/wait, examination, examination return, return-consultation wait, or discharge. Nurses are green triangles and doctors are dark-blue squares with visible borders. Satisfaction never replaces the workflow fill: it changes the patient border to normal for 60–100, yellow for 40–59, or red for 0–39. Recent satisfaction events may appear briefly as a score-change label.

Queue anchors and a fixed spacing produce repeatable, non-overlapping positions. Queue order changes only when an event joins or starts service; markers do not wander randomly. A visual seat is assigned on the corresponding `seat_acquired` event and released on `seat_released`. When no seat exists, the Python simulation remains responsible for the one-time satisfaction deduction.

Playback, pause, reset, 1×/2×/5×/10× speed, event stepping, scrubbing, selection, and fit-to-screen all run locally. Consequently a 200-patient animation does not trigger a Streamlit rerun for every frame. The fixed legend sits outside the Konva stage, stays visible while the stage pans or zooms, shows live counts, edits colours, and highlights matching states.

Movement is straight-line interpolation between defined points using a default speed of 1.2 metres per second. The architecture keeps destinations separate from interpolation so obstacle-aware routing can be added later, but this MVP does not understand walls or compute wall-aware paths. Walking time is visual by default and is not added back into the completed SimPy run.
