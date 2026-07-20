import pytest
from patientflowsim.config import load_config, config_from_dict
def test_exam_probability_validation():
    with pytest.raises(ValueError): config_from_dict({'examinations':{'laboratory_probability':.8,'imaging_probability':.3}})
def test_default_config_valid(): assert load_config().resources.doctors == 5
