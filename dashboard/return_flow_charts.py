import streamlit as st
def render(result): st.bar_chart(result.patients[['first_doctor_wait','return_consultation_wait']])
