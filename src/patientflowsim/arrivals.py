"""Appointment and synthetic arrival generation."""
import numpy as np
from .config import SimulationConfig
from .patient import Patient
def generate_patients(config: SimulationConfig, rng: np.random.Generator) -> list[Patient]:
    """Generate reproducible scheduled synthetic patients."""
    p=config.patients; appointments=np.arange(p.scheduled_count)*p.appointment_interval_minutes
    if p.appointment_distribution == 'morning_heavy': appointments=np.sort(appointments * np.linspace(.55,1.25,p.scheduled_count))
    patients=[]
    for i, appointment in enumerate(appointments):
        late=rng.random()<p.lateness_rate; delta=float(rng.uniform(*(p.late_arrival_range if late else p.early_arrival_range))) * (1 if late else -1); exam='laboratory' if rng.random()<config.examinations.laboratory_probability else ('imaging' if rng.random()<config.examinations.imaging_probability/(1-config.examinations.laboratory_probability) else 'none')
        patients.append(Patient(f'P{i+1:04d}',float(appointment),max(0,float(appointment+delta)),delta,rng.random()<p.no_show_rate,exam))
    return patients
