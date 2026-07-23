"""SimPy clinic model and result container."""
from __future__ import annotations
from dataclasses import dataclass
import simpy, numpy as np, pandas as pd
from .config import SimulationConfig
from .arrivals import generate_patients
from .event_log import EventLog
from .satisfaction import change, evaluate

@dataclass
class SimulationResult:
    patients: pd.DataFrame; events: pd.DataFrame; queue_history: pd.DataFrame; metrics: dict; config: SimulationConfig

def run_simulation(config: SimulationConfig) -> SimulationResult:
    """Run one complete synthetic clinic day, including post-closing work."""
    config.validate(); env=simpy.Environment(); rng=np.random.default_rng(config.simulation.random_seed); log=EventLog(); patients=generate_patients(config,rng); res=config.resources
    check=simpy.Resource(env,res.check_in_staff); triage=simpy.Resource(env,res.triage_nurses); lab=simpy.Resource(env,res.laboratory_capacity); imaging=simpy.Resource(env,res.imaging_capacity)
    if config.queue_policy.consultation_policy == 'reserved_return':
        initial_doctors=simpy.PriorityResource(env,res.doctors-config.queue_policy.reserved_return_doctors)
        return_doctors=simpy.PriorityResource(env,config.queue_policy.reserved_return_doctors)
    else:
        initial_doctors=return_doctors=simpy.PriorityResource(env,res.doctors)
    seats=simpy.Container(env,capacity=res.waiting_area_seats,init=res.waiting_area_seats) if res.waiting_area_seats else None
    history=[]; busy={x:0. for x in ['check_in','triage','doctors','laboratory','imaging']}
    def sample(stage):
        s=config.service_times[stage]; return max(s.minimum, s.mean if s.kind=='fixed' else (rng.normal(s.mean,s.std) if s.kind=='normal' else rng.lognormal(np.log(max(s.mean,.01)),s.std)))
    def record(name, resource): history.append({'time':env.now,'queue':name,'length':len(resource.queue)})
    def use(patient, resource, stage, start, end, event_prefix, department, priority=1):
        record(stage,resource)
        with resource.request(priority=priority) if isinstance(resource,simpy.PriorityResource) else resource.request() as req:
            yield req; setattr(patient,start,env.now); log.add(env.now,patient,event_prefix+'_started',department,len(resource.queue),resource.count); duration=sample(stage); busy[department]+=duration; yield env.timeout(duration); setattr(patient,end,env.now); log.add(env.now,patient,event_prefix+'_completed',department,len(resource.queue),resource.count)
    def seat(patient, which):
        if seats is not None and seats.level>=1:
            yield seats.get(1); setattr(patient,which,True); log.add(env.now,patient,'seat_acquired','waiting_area',resource_in_use=res.waiting_area_seats-seats.level)
            return True
        setattr(patient,which,False); change(patient,'no_seat_'+which,-config.satisfaction_rules['no_seat_penalty'],env.now); log.add(env.now,patient,'no_seat_available','waiting_area'); return False
    def release(patient, held):
        if held and seats is not None: yield seats.put(1); log.add(env.now,patient,'seat_released','waiting_area',resource_in_use=res.waiting_area_seats-seats.level)
    def consult(patient, resource, stage, start, end, event_prefix, held, priority=1):
        record(stage,resource)
        with resource.request(priority=priority) as req:
            yield req
            # A seat belongs to the waiting stage, so release it as soon as the
            # patient is called rather than holding it throughout consultation.
            yield from release(patient,held)
            setattr(patient,start,env.now); log.add(env.now,patient,event_prefix+'_started','doctors',len(resource.queue),resource.count)
            duration=sample(stage); busy['doctors']+=duration; yield env.timeout(duration)
            setattr(patient,end,env.now); log.add(env.now,patient,event_prefix+'_completed','doctors',len(resource.queue),resource.count)
    def journey(p):
        yield env.timeout(p.actual_arrival_time)
        if p.no_show: log.add(env.now,p,'no_show','clinic'); return
        log.add(env.now,p,'patient_arrived','clinic')
        yield from use(p,check,'first_check_in','first_check_in_start','first_check_in_end','first_check_in','check_in')
        yield from use(p,triage,'triage','triage_start','triage_end','triage','triage')
        p.first_doctor_queue_entry=env.now; held=yield from seat(p,'first_seat_available'); log.add(env.now,p,'first_doctor_queue_joined','doctors',len(initial_doctors.queue))
        yield from consult(p,initial_doctors,'initial_consultation','initial_consultation_start','initial_consultation_end','initial_consultation',held,1)
        if p.examination_type=='none': p.discharge_time=env.now; evaluate(p,config.satisfaction_rules,env.now); log.add(env.now,p,'patient_discharged','clinic'); return
        examres=lab if p.examination_type=='laboratory' else imaging; dept=p.examination_type; p.examination_queue_entry=env.now; log.add(env.now,p,'examination_queue_joined',dept,len(examres.queue)); yield from use(p,examres,dept,'examination_start','examination_end','examination',dept)
        p.return_to_clinic_time=env.now; log.add(env.now,p,'patient_returned','clinic')
        yield from use(p,check,'return_check_in','second_check_in_start','second_check_in_end','return_check_in','check_in')
        p.return_consultation_queue_entry=env.now; held=yield from seat(p,'return_seat_available'); log.add(env.now,p,'return_doctor_queue_joined','doctors',len(return_doctors.queue))
        priority=0 if config.queue_policy.consultation_policy=='return_priority' else 1
        yield from consult(p,return_doctors,'return_consultation','return_consultation_start','return_consultation_end','return_consultation',held,priority); p.discharge_time=env.now; evaluate(p,config.satisfaction_rules,env.now); log.add(env.now,p,'patient_discharged','clinic')
    for p in patients: env.process(journey(p))
    env.run(); frame=pd.DataFrame([p.row() for p in patients]); events=log.dataframe(); closing=(int(config.clinic.closing_time[:2])-int(config.clinic.opening_time[:2]))*60
    from .metrics import calculate_metrics
    metrics=calculate_metrics(frame,events,history,busy,res,env.now,closing)
    return SimulationResult(frame,events,pd.DataFrame(history),metrics,config)
