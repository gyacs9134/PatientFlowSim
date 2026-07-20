import streamlit as st
def render(result):
    """Render headline operational metrics."""
    m=result.metrics; cols=st.columns(5)
    for col,(label,key) in zip(cols,[('Arrived','total_patients_arriving'),('Completed','completed_patients'),('First doctor wait','average_first_doctor_wait'),('Satisfaction','average_final_satisfaction'),('Doctor utilisation','doctors_utilisation')]): col.metric(label,f"{m[key]:.1f}" if isinstance(m[key],float) else m[key])
