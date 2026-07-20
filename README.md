# PatientFlowSim

**An outpatient patient-flow simulator using SimPy to model check-in, triage, consultations, examinations, return visits, queues, resource use, and patient satisfaction.**

PatientFlowSim is an educational, synthetic-data discrete-event model for exploring whether clinic triage or doctors are bottlenecks, and how examination returns compete for doctors.

## Journey
`Appointment → arrival → check-in → triage → doctor → [laboratory/imaging → return check-in → doctor] → discharge`

## Features
* Reproducible SimPy simulation, typed YAML configuration, queue/event logs, seating and configurable satisfaction assumptions.
* Shared FIFO and return-priority doctor policies, scenario comparison, metrics and Plotly/Streamlit views.
* Synthetic data only; no patient records are accepted or generated.

## Install and run
```bash
python -m pip install -r requirements.txt
streamlit run app.py
pytest
```
The dashboard has a **Run Simulation** button and tabs for overview, queues, resources, examination return flow, satisfaction, comparison, and patient results. Configure `config/default_config.yaml`; scenario overrides are in `config/scenarios.yaml`.

## Satisfaction assumption
Arriving patients start at 80. Rules in `config/satisfaction_rules.yaml` apply threshold-based wait and seating deductions and timely-service bonuses, clamped to 0–100. It is a configurable simulation assumption, **not** a clinically validated patient-experience scale.

## Assumptions and limitations
One scheduled general outpatient department is represented with no emergencies, staff breaks, acuity, beds, pharmacy, or inpatient flow. Results are sensitive to synthetic arrivals and service-time assumptions. See `docs/` for methodology, policy trade-offs, assumptions, and limitations.

## Privacy
“This project uses synthetic patient data only and is intended for educational and operational-modelling purposes. It does not process identifiable health information and should not be used for clinical decision-making.”

## Repository layout
`src/patientflowsim/` contains the model; `dashboard/` contains presentation helpers; `config/` contains assumptions; `tests/` verifies core behaviors. Screenshots: _run the Streamlit dashboard locally to capture your scenario._
