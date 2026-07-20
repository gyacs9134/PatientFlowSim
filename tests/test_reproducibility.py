from patientflowsim.config import load_config, config_from_dict
from patientflowsim.simulation import run_simulation
def test_same_seed_reproduces_results():
    c=load_config(); assert run_simulation(c).patients.to_csv(index=False)==run_simulation(c).patients.to_csv(index=False)
def test_different_seed_changes_population():
    c=load_config(); a=run_simulation(c); b=run_simulation(config_from_dict({'simulation':{'random_seed':43}})); assert not a.patients.actual_arrival_time.equals(b.patients.actual_arrival_time)
