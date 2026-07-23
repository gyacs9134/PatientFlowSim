# Live simulation

The SimPy event log remains the source of truth. `prepare_spatial_timeline` attaches entity state, event time, visual time, source, destination, path, walking duration, queue position, seat, station, satisfaction, and metadata. React receives the complete prepared timeline once and advances it with `requestAnimationFrame`; it does not ask Streamlit to rerun on every frame.

## Symbols and legend

Patients are always circles, nurses triangles, and doctors squares. Patient fill is reserved for workflow state. Satisfaction changes only the patient border. The legend lives outside the transformed Konva stage, so map pan and zoom cannot move it. Clicking a state dims nonmatching patients.

## Queues and seats

Every queue anchor has a stable index-based position and direction. Positions wrap deterministically rather than clamping several people onto one coordinate. Patients assigned a seat render at that seat; otherwise they render at a standing queue position. The simulation releases a seat when the doctor accepts the patient and the waiting stage ends.

## Controls and overlays

Play, Pause, Restart, Next event, 1×/2×/5×/10×, Fit, timeline scrubbing, and Finish run share one control bar. Congestion and queue labels are enabled by default. Optional overlays include short flow trails, seat/department occupancy, wait, utilisation, satisfaction, and patient IDs.

The map uses direct waypoint interpolation at 1.2 m/s. Wall-aware routing, collision physics, and CAD navigation are outside the MVP.
