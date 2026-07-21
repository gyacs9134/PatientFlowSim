"""Streamlit entry point; simulation logic remains in the package."""
import streamlit as st
from patientflowsim.config import load_config, config_from_dict
from patientflowsim.simulation import run_simulation
from dashboard.controls import controls
from dashboard import overview,queue_charts,resource_charts,return_flow_charts,satisfaction_charts,patient_table,floorplan_tab
st.set_page_config(page_title='PatientFlowSim',layout='wide'); st.title('PatientFlowSim'); st.caption('Synthetic outpatient operational model — not clinical decision support.')
base=load_config(); overrides=controls(base)
if st.sidebar.button('Run Simulation',type='primary'):
    try: st.session_state.result=run_simulation(config_from_dict(overrides))
    except ValueError as exc: st.error(str(exc))
tabs=st.tabs(['Overview','Queues','Resources','Examination return flow','Patient satisfaction','Scenario comparison','Patient-level results','2D Floor Plan']); result=st.session_state.get('result')
if result is not None:
    with tabs[0]: overview.render(result)
    with tabs[1]: queue_charts.render(result)
    with tabs[2]: resource_charts.render(result)
    with tabs[3]: return_flow_charts.render(result)
    with tabs[4]: satisfaction_charts.render(result)
    with tabs[5]: st.info('Use patientflowsim.scenarios.run_scenarios for YAML scenario comparisons.')
    with tabs[6]: patient_table.render(result)
else:
    with tabs[0]: st.info('Configure the clinic and click Run Simulation. The 2D layout editor is available now.')
with tabs[7]: floorplan_tab.render(result)
