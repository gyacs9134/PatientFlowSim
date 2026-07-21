# PatientFlowSim

**An outpatient patient-flow simulator using SimPy to model check-in, triage, consultations, examinations, return visits, queues, resource use, and patient satisfaction.**

PatientFlowSim is an educational, synthetic-data discrete-event model for exploring whether clinic triage or doctors are bottlenecks, and how examination returns compete for doctors.

## Journey
`Appointment → arrival → check-in → triage → doctor → [laboratory/imaging → return check-in → doctor] → discharge`

## Features
* Reproducible SimPy simulation, typed YAML configuration, queue/event logs, seating and configurable satisfaction assumptions.
* Shared FIFO and return-priority doctor policies, scenario comparison, metrics and Plotly/Streamlit views.
* Interactive 2D floor-plan editor with metre-based coordinates, snapping, pan/zoom, room resizing, seat generation, resource stations, and JSON persistence.
* Local animated replay of the Python event log with patient circles, nurse triangles, doctor squares, live queue counts, seat occupancy, fixed editable legend, and satisfaction borders.
* Bounded server-side GIF export with range, speed, FPS, dimensions, labels, legend, metrics, and loop controls.
* Synthetic data only; no patient records are accepted or generated.

## Install and run
```bash
python -m pip install -r requirements.txt
streamlit run app.py
pytest
```
The dashboard has a **Run Simulation** button and tabs for overview, queues, resources, examination return flow, satisfaction, comparison, patient results, and **2D Floor Plan**. Configure `config/default_config.yaml`; scenario overrides are in `config/scenarios.yaml`.

The committed custom-component build works immediately. To change its React/TypeScript source:

```bash
cd frontend/floorplan_component
pnpm install
pnpm test
pnpm build
```

During frontend development, run `pnpm dev` and set `PATIENTFLOWSIM_COMPONENT_URL=http://localhost:5173` before starting Streamlit.

## 2D floor plan

Open **2D Floor Plan → Layout Editor** to drag and resize rectangular departments, edit exact dimensions, place and rotate seats, generate seat grids, and map visual resource stations. Wheel zoom and empty-canvas drag do not change saved object coordinates. Layouts use world coordinates in metres and the versioned JSON schema in `config/default_layout.json`; editable state is never stored in a GIF.

After running a simulation, **Simulation View** converts its existing event log to spatial keyframes. Patients are always circles and change fill only with workflow state. Nurses remain green triangles; doctors remain dark-blue squares. A patient's border is normal, yellow, or red for satisfaction ranges 60–100, 40–59, and 0–39. The legend stays outside the transformed canvas, so it remains fixed during pan and zoom; clicking a state highlights matching patients.

Use **GIF Export** to render the complete day or a range. Long exports are evenly down-sampled to a configurable frame limit and rejected with a readable message if dimensions and frame count would exceed the memory guardrail.

The MVP uses direct interpolation between stations and queue anchors at a default walking speed of 1.2 m/s. It does not perform wall-aware or obstacle-aware pathfinding. See [floor-plan editing](docs/floorplan_editor.md), [spatial animation](docs/spatial_animation.md), and [GIF export](docs/gif_export.md).

## Satisfaction assumption
Arriving patients start at 80. Rules in `config/satisfaction_rules.yaml` apply threshold-based wait and seating deductions and timely-service bonuses, clamped to 0–100. It is a configurable simulation assumption, **not** a clinically validated patient-experience scale.

## Assumptions and limitations
One scheduled general outpatient department is represented with no emergencies, staff breaks, acuity, beds, pharmacy, or inpatient flow. Results are sensitive to synthetic arrivals and service-time assumptions. See `docs/` for methodology, policy trade-offs, assumptions, and limitations.

## Privacy
“This project uses synthetic patient data only and is intended for educational and operational-modelling purposes. It does not process identifiable health information and should not be used for clinical decision-making.”

## Repository layout
`src/patientflowsim/` contains the simulation, layout schema, timeline preparation, and GIF renderer; `frontend/floorplan_component/` contains React/Konva source and the committed production build; `dashboard/` contains presentation helpers; `config/` contains assumptions and the default layout; `tests/` verifies core behaviours. Screenshots: _run the Streamlit dashboard locally to capture your scenario._
