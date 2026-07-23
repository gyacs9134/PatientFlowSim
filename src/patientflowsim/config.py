"""Typed YAML configuration and validation."""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any
import yaml

@dataclass
class ServiceTime:
    kind: str = "fixed"; mean: float = 5; std: float = 0; minimum: float = 0
    def validate(self) -> None:
        if self.kind not in {"fixed", "normal", "lognormal"} or self.mean < 0 or self.std < 0 or self.minimum < 0: raise ValueError("Service times must be non-negative fixed, normal, or lognormal distributions")
@dataclass
class Clinic: opening_time: str = "08:00"; closing_time: str = "17:00"
@dataclass
class Patients: scheduled_count: int = 100; appointment_interval_minutes: float = 5; appointment_distribution: str = "evenly_spaced"; no_show_rate: float = .08; lateness_rate: float = .2; early_arrival_range: list[float] = field(default_factory=lambda:[0,15]); late_arrival_range: list[float] = field(default_factory=lambda:[1,30])
@dataclass
class Resources: check_in_staff: int = 1; triage_nurses: int = 2; doctors: int = 5; laboratory_capacity: int = 2; imaging_capacity: int = 1; waiting_area_seats: int = 30
@dataclass
class Examinations: laboratory_probability: float = .2; imaging_probability: float = .1
@dataclass
class QueuePolicy: consultation_policy: str = "shared_fifo"; reserved_return_doctors: int = 0
@dataclass
class Simulation: random_seed: int = 42
@dataclass
class SimulationConfig:
    clinic: Clinic = field(default_factory=Clinic); patients: Patients = field(default_factory=Patients); resources: Resources = field(default_factory=Resources); examinations: Examinations = field(default_factory=Examinations); queue_policy: QueuePolicy = field(default_factory=QueuePolicy); simulation: Simulation = field(default_factory=Simulation); service_times: dict[str, ServiceTime] = field(default_factory=dict); satisfaction_rules: dict[str, float] = field(default_factory=dict)
    def validate(self) -> None:
        if self.patients.scheduled_count < 0 or self.patients.appointment_interval_minutes <= 0: raise ValueError("Scheduled count must be non-negative and appointment interval must be positive")
        if any(not 0 <= x <= 1 for x in (self.patients.no_show_rate,self.patients.lateness_rate,self.examinations.laboratory_probability,self.examinations.imaging_probability)): raise ValueError("Probabilities must be between 0 and 1")
        if self.examinations.laboratory_probability + self.examinations.imaging_probability > 1: raise ValueError("Examination probabilities cannot exceed 100%")
        if any(getattr(self.resources,n) < 1 for n in ("check_in_staff","triage_nurses","doctors","laboratory_capacity","imaging_capacity")): raise ValueError("Required resource counts must be at least 1")
        if self.resources.waiting_area_seats < 0: raise ValueError("Waiting-area seats cannot be negative")
        if self.clinic.closing_time <= self.clinic.opening_time: raise ValueError("Clinic closing time must be later than opening time")
        if self.queue_policy.consultation_policy not in {"shared_fifo","return_priority","reserved_return"}: raise ValueError("Unknown consultation policy")
        if self.queue_policy.reserved_return_doctors < 0 or self.queue_policy.reserved_return_doctors >= self.resources.doctors:
            raise ValueError("Reserved return doctors must be between 0 and one less than total doctors")
        if self.queue_policy.consultation_policy == "reserved_return" and self.queue_policy.reserved_return_doctors < 1:
            raise ValueError("Reserved return policy requires at least one reserved return doctor")
        for value in self.service_times.values(): value.validate()
    def to_dict(self) -> dict[str, Any]: return asdict(self)
def load_config(path: str | Path = "config/default_config.yaml", satisfaction_path: str | Path = "config/satisfaction_rules.yaml") -> SimulationConfig:
    """Load configuration from YAML files."""
    data = yaml.safe_load(Path(path).read_text())
    cfg = SimulationConfig(**{k: ({"clinic":Clinic,"patients":Patients,"resources":Resources,"examinations":Examinations,"queue_policy":QueuePolicy,"simulation":Simulation}[k](**v) if k not in {"service_times"} else {n:ServiceTime(**s) for n,s in v.items()}) for k,v in data.items()})
    cfg.satisfaction_rules = yaml.safe_load(Path(satisfaction_path).read_text())
    cfg.validate(); return cfg
def config_from_dict(data: dict[str, Any]) -> SimulationConfig:
    """Create a typed configuration from a nested dictionary."""
    import tempfile
    base = load_config(); merged = base.to_dict()
    def merge(a: dict, b: dict) -> None:
        for k,v in b.items(): a[k] = merge(a[k],v) if isinstance(v,dict) and isinstance(a.get(k),dict) else v
        return a
    merged = merge(merged, data)
    cfg = SimulationConfig(Clinic(**merged['clinic']),Patients(**merged['patients']),Resources(**merged['resources']),Examinations(**merged['examinations']),QueuePolicy(**merged['queue_policy']),Simulation(**merged['simulation']),{k:ServiceTime(**v) for k,v in merged['service_times'].items()},merged['satisfaction_rules']); cfg.validate(); return cfg
