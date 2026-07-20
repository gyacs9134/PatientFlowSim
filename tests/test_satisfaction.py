from patientflowsim.patient import Patient
from patientflowsim.satisfaction import change
def test_scores_clamped_and_events_once():
    p=Patient('P',0,0,0); change(p,'x',-200,1); change(p,'x',-10,2)
    assert p.final_satisfaction_score == 0 and len(p.satisfaction_events)==1
