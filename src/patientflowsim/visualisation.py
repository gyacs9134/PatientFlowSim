"""Plotly charts built from simulation result tables."""
import plotly.express as px
def queue_chart(result):
    """Return interactive queue-length chart."""
    return px.line(result.queue_history,x='time',y='length',color='queue',title='Queue lengths over time')
def utilisation_chart(result):
    """Return resource utilisation bar chart."""
    data=[{'resource':k.replace('_utilisation',''),'utilisation':v} for k,v in result.metrics.items() if k.endswith('_utilisation')]; return px.bar(data,x='resource',y='utilisation',range_y=[0,1],title='Resource utilisation')
def satisfaction_chart(result):
    """Return satisfaction distribution."""
    return px.histogram(result.patients.query('not no_show'),x='final_satisfaction_score',title='Final satisfaction distribution')
def timeline_chart(result, patient_id):
    """Return selected patient journey timeline."""
    p=result.patients.query('patient_id == @patient_id').iloc[0]; stages=[('Check-in','first_check_in_start','first_check_in_end'),('Triage','triage_start','triage_end'),('Initial consultation','initial_consultation_start','initial_consultation_end'),('Examination','examination_start','examination_end'),('Return check-in','second_check_in_start','second_check_in_end'),('Return consultation','return_consultation_start','return_consultation_end')]; rows=[{'stage':n,'start':p[a],'end':p[b]} for n,a,b in stages if p[a] is not None and p[b] is not None]; return px.timeline(rows,x_start='start',x_end='end',y='stage',title=f'Journey: {patient_id}')
