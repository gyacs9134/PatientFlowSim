import streamlit as st
def render(result): st.dataframe(result.patients,use_container_width=True)
