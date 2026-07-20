import streamlit as st
from patientflowsim.visualisation import queue_chart
def render(result): st.plotly_chart(queue_chart(result),use_container_width=True)
