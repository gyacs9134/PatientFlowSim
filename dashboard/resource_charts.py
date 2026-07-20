import streamlit as st
from patientflowsim.visualisation import utilisation_chart
def render(result): st.plotly_chart(utilisation_chart(result),use_container_width=True)
