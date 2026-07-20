import numpy as np
from patientflowsim.config import load_config
from patientflowsim.arrivals import generate_patients
def test_seeded_arrivals_repeat():
    c=load_config(); assert [p.actual_arrival_time for p in generate_patients(c,np.random.default_rng(1))] == [p.actual_arrival_time for p in generate_patients(c,np.random.default_rng(1))]
