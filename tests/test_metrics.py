from patientflowsim.config import load_config
from patientflowsim.simulation import run_simulation
def test_arrivals_are_completed_or_counted_after_closing():
    r=run_simulation(load_config()); assert r.metrics['completed_patients'] + r.metrics['no_show_patients'] == r.metrics['total_patients_scheduled']
