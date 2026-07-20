from patientflowsim.config import config_from_dict
from patientflowsim.simulation import run_simulation
def test_exam_patients_return_for_second_checkin_and_consultation():
    r=run_simulation(config_from_dict({'patients':{'scheduled_count':3,'no_show_rate':0},'examinations':{'laboratory_probability':1,'imaging_probability':0}}))
    assert r.patients.second_check_in_end.notna().all() and r.patients.return_consultation_end.notna().all()
