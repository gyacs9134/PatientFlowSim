import streamlit as st
from patientflowsim.visualisation import satisfaction_chart
def render(result): st.plotly_chart(satisfaction_chart(result),use_container_width=True)
