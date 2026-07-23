# Interface design

PatientFlowSim uses three mutually exclusive application states: Setup, Live Simulation, and Results. The Python `AppState` transition table prevents Setup from skipping directly to Results. The floor-plan editor is a focused workspace opened from Setup or Results; it is not mixed into live playback.

## Setup

Setup contains the project identity, selected layout preview, scenario selector, essential inputs, a collapsed Advanced Settings area, and one primary **Start Simulation** form action. It contains no charts and uses no persistent sidebar. Advanced tabs group appointments, service times, queue policy, and satisfaction assumptions.

## Live Simulation

Live Simulation gives roughly three quarters of horizontal space to the top-down map. A compact fixed sidecar contains live metrics and the legend. Playback controls occupy one bottom bar. Configuration forms and detailed charts are absent.

## Results

Results opens automatically when playback reaches the requested end or the user selects Finish run. Primary cards are followed by six result tabs so detailed plots do not become one uncontrolled page. Run Again is the primary result action; setup, editing, replay, comparison, GIF, CSV, and report actions remain available.

The design targets common desktop resolutions, neutral surfaces, restrained congestion colours, consistent spacing, readable labels, and keyboard-accessible native controls.
