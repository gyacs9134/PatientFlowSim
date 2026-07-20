"""Structured event logging."""
import pandas as pd
class EventLog:
    def __init__(self): self.events=[]
    def add(self,time,patient,event_type,department,queue_length=0,resource_in_use=0,metadata=None): self.events.append({'time':time,'patient_id':patient.patient_id,'event_type':event_type,'department':department,'queue_length':queue_length,'resource_in_use':resource_in_use,'patient_satisfaction':patient.final_satisfaction_score,'metadata':metadata or {}})
    def dataframe(self): return pd.DataFrame(self.events)
