from patientflowsim.config import config_from_dict
from patientflowsim.simulation import run_simulation
def test_no_exam_patients_discharge_after_first_consultation():
    r=run_simulation(config_from_dict({'patients':{'scheduled_count':3,'no_show_rate':0},'examinations':{'laboratory_probability':0,'imaging_probability':0}}))
    assert r.patients.initial_consultation_end.notna().all() and r.patients.discharge_time.notna().all()
