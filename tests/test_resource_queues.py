from patientflowsim.config import config_from_dict
from patientflowsim.simulation import run_simulation
def test_utilisation_and_queues_are_bounded():
    r=run_simulation(config_from_dict({'patients':{'scheduled_count':5}})); assert (r.queue_history.length>=0).all() and all(0<=v<=1 for k,v in r.metrics.items() if k.endswith('_utilisation'))
