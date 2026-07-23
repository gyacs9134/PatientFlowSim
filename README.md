# PatientFlowSim

**An outpatient patient-flow simulator using SimPy to model check-in, triage, consultations, examinations, return visits, queues, resource use, and patient satisfaction.**

PatientFlowSim is a synthetic-data management simulation for exploring clinic congestion. It combines a reproducible Python discrete-event model with a top-down animated floor plan and a dedicated end-of-run analysis screen.

## Three-screen workflow

1. **Setup** — choose a scenario, review the floor plan, change essential staffing and demand assumptions, then press the prominent **Start Simulation** button. Service-time distributions, queue policies, satisfaction rules, and appointment assumptions remain collapsed under Advanced Settings.
2. **Live Simulation** — watch patient circles move through the clinic. Queues, seats, returning examination patients, staff, live counts, congestion borders, and the fixed legend update locally without a Streamlit rerun per frame.
3. **Results** — review primary metrics, a deterministic bottleneck ranking, measured operational findings, charts, records, scenario comparisons, replay periods, GIF export, and CSV/report downloads.

`Appointment → entrance → check-in → triage → initial waiting → doctor → [laboratory/imaging → return check-in → return waiting → doctor] → exit`

## Main features

- Reproducible SimPy simulation with typed YAML configuration and one NumPy random generator.
- Shared FIFO, return-priority, and dedicated return-capacity doctor policies.
- Explicit examination return flow competing with initial consultations.
- Limited seating with acquisition at a waiting stage and release when consultation begins.
- Configurable, threshold-based satisfaction assumptions clamped to 0–100.
- Editable JSON floor plan using metre-based coordinates, pan/zoom, snapping, rooms, seats, stations, entrances, exits, and queue anchors.
- Patient circles, nurse triangles, and doctor squares. Patient fill shows workflow state; the circle border shows satisfaction.
- Smooth waypoint interpolation at 1.2 m/s, visible queue positions, seat occupancy, short optional trails, and live congestion overlays.
- Fixed legend with live state counts, highlighting, colour editing, shape keys, satisfaction borders, and seat states.
- Results tabs for Summary, Bottlenecks, Patient flow, Resources, Satisfaction, and Patient records.
- Server-rendered, frame-limited GIF export with legend, metrics, IDs, dimensions, and satisfaction-event options.

## Install and run

Python 3.11 or newer is required.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Run tests:

```bash
pytest -q
cd frontend/floorplan_component
pnpm install
pnpm test
pnpm build
```

The production component build is committed, so users do not need Node.js merely to run Streamlit. During component development, run `pnpm dev` and set `PATIENTFLOWSIM_COMPONENT_URL=http://localhost:5173` before starting Streamlit.

## Floor-plan editor

Select **Edit Floor Plan** on Setup or Results. The editor has one toolbar, one canvas, and one properties panel. Wheel zoom and empty-canvas drag affect only the view. Saved X/Y coordinates, dimensions, seats, stations, entry/exit points, and queue anchors remain in metres. Layouts use the versioned JSON schema in `config/default_layout.json`; GIF recordings never contain editable layout state.

Department rectangles show live dimension labels while selected. Seats can be rotated or generated in grids with row/column spacing. Queue anchors define deterministic standing positions and direction. Overlap and station-capacity problems are reported without silently changing the layout.

## Live map rules

- **Patients:** circles. Blue is arrival/check-in, yellow is triage wait, orange is initial doctor wait, purple is consultation, cyan/dark cyan is examination flow, red is return travel, dark red is return wait, and grey is departure.
- **Staff:** green triangles are nurses; dark-blue squares are doctors.
- **Satisfaction:** normal border for 60–100, yellow for 40–59, red for 0–39. Satisfaction never replaces workflow fill colour.
- **Congestion:** restrained room borders progress from normal to busy, congested, and critical. Queue labels show count and longest current wait.

The frontend animates a prepared timeline derived from the Python event log; it does not implement a second simulation engine. Same configuration and seed therefore produce the same patient data and animation timeline.

## Bottleneck ranking

The results ranking is rule-based and inspectable. Each stage receives at most 100 points:

- peak queue relative to capacity: 30 points;
- 90th-percentile wait relative to 60 minutes: 30 points;
- utilisation relative to 95%: 25 points;
- sampled minutes with queue above capacity relative to two hours: 15 points.

Every displayed finding is derived from metrics or the ranking. No machine-learning or generative recommendation system is used.

## Configuration and scenarios

Defaults are in `config/default_config.yaml`, satisfaction rules in `config/satisfaction_rules.yaml`, and named scenario overrides in `config/scenarios.yaml`. Comparisons reuse the completed run's base configuration and random seed where practical, so changes primarily reflect scenario assumptions.

## GIF and data export

Results can export a full day, selected range, peak congestion period, examination-return surge, or final hour. GIF frame sampling obeys a maximum-frame and memory guardrail. Results, patient records, and a Markdown summary report are downloadable separately.

## Assumptions and limitations

The MVP models one scheduled general outpatient department with no emergencies, clinical acuity, staff breaks, inpatient beds, pharmacy, or wall-aware pathfinding. Movement follows direct waypoints and defined queue/station locations; it is not a CAD navigation model. Satisfaction is a configurable simulation assumption, not a validated patient-experience scale.

Real-world operational use requires calibration and validation using appropriately governed, anonymised hospital data. Synthetic assumptions alone are not evidence for changing actual clinical operations.

See [interface design](docs/interface_design.md), [live simulation](docs/live_simulation.md), [bottleneck detection](docs/bottleneck_detection.md), [results screen](docs/results_screen.md), [spatial animation](docs/spatial_animation.md), and [GIF export](docs/gif_export.md).

## Privacy

“This project uses synthetic patient data only and is intended for educational and operational-modelling purposes. It does not process identifiable health information and should not be used for clinical decision-making.”

## Repository layout

`src/patientflowsim/` contains simulation, analysis, layout, timeline, and GIF code. `frontend/floorplan_component/` contains React/Konva source and its committed build. `dashboard/` contains the three Streamlit screens. `config/` stores assumptions and layouts. `tests/` contains deterministic backend tests. Screenshot placeholder: add images from a locally run synthetic scenario.
