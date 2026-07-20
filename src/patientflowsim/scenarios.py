"""Scenario loading and comparable execution."""
from pathlib import Path
import yaml, pandas as pd
from .config import config_from_dict
from .simulation import run_simulation
def run_scenarios(names, path='config/scenarios.yaml'):
    """Run named YAML scenarios with their declared shared seed."""
    definitions=yaml.safe_load(Path(path).read_text()); rows=[]
    for name in names:
        result=run_simulation(config_from_dict(definitions[name])); rows.append({'scenario':name,**result.metrics})
    return pd.DataFrame(rows)
