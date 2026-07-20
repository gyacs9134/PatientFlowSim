"""Configurable, non-clinically-validated satisfaction assumptions."""
from .patient import Patient
def change(patient: Patient, event: str, amount: float, time: float) -> None:
    """Apply a named score event once and clamp to the 0--100 scale."""
    if any(x['event']==event for x in patient.satisfaction_events): return
    patient.final_satisfaction_score=max(0,min(100,patient.final_satisfaction_score+amount)); patient.satisfaction_events.append({'event':event,'score_change':amount,'time':time})
def evaluate(patient: Patient, rules: dict, now: float) -> None:
    """Apply end-of-journey wait, seat, and duration rules."""
    r=patient.row(); first=r['first_doctor_wait'] or 0; ret=r['return_consultation_wait'] or 0
    for label,wait in [('first_doctor',first),('return_doctor',ret)]:
        for threshold in range(int(rules['first_doctor_grace_minutes']+rules['wait_step_minutes']), int(wait)+1, int(rules['wait_step_minutes'])): change(patient,f'{label}_wait_step_{threshold}',-rules['wait_step_penalty'],now)
        if wait>=60: change(patient,f'{label}_wait_over_60_minutes',-rules['doctor_wait_60_penalty'],now)
    if (r['triage_wait'] or 0)>rules['triage_wait_threshold']: change(patient,'triage_wait_long',-rules['triage_wait_penalty'],now)
    if (r['examination_wait'] or 0)>rules['examination_wait_threshold']: change(patient,'examination_wait_long',-rules['examination_wait_penalty'],now)
    if ret>rules['return_wait_threshold']: change(patient,'return_wait_long',-rules['return_wait_penalty'],now)
    if (r['total_time_in_clinic'] or 0)>rules['visit_duration_threshold']: change(patient,'visit_long',-rules['visit_duration_penalty'],now)
    if patient.initial_consultation_start is not None and patient.initial_consultation_start-patient.appointment_time<=rules['on_time_threshold']: change(patient,'seen_on_time',rules['on_time_bonus'],now)
    if (r['total_time_in_clinic'] or 9999)<=rules['quick_visit_threshold']: change(patient,'quick_visit',rules['quick_visit_bonus'],now)
