from patientflowsim.config import config_from_dict
from patientflowsim.simulation import run_simulation
def test_no_seat_is_recorded():
    r=run_simulation(config_from_dict({'resources':{'waiting_area_seats':0},'patients':{'scheduled_count':3,'no_show_rate':0}})); assert (r.patients.first_seat_available==False).any()
