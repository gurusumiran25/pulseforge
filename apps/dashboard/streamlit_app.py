"""PulseForge M21 — product analytics portfolio dashboard.

Run with: streamlit run apps/dashboard/streamlit_app.py
The initial release reads the synthetic M20 Bronze CSV only.
"""
import streamlit as st

from apps.dashboard.metrics import STAGES, load_events, summarize


st.set_page_config(page_title="PulseForge | Product Intelligence", page_icon="📊", layout="wide")
st.title("PulseForge")
st.caption("Product intelligence • M21 demo • synthetic events, not production data")

@st.cache_data
def get_events():
    return load_events()

events = get_events()
dates = sorted({event["event_time"].date().isoformat() for event in events})
if dates:
    selected = st.sidebar.multiselect("UTC event dates", dates, default=dates)
    events = [event for event in events if event["event_time"].date().isoformat() in selected]

summary = summarize(events)
st.info("Session-stage participation is not an ordered conversion funnel. Filtering by event date can create partial sessions.")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Events", summary["events"])
c2.metric("Sessions", summary["sessions"])
c3.metric("Users", summary["users"])
c4.metric("Sessions with payment", summary["paid_sessions"])

st.subheader("Observed session stages")
stage_counts = {stage.replace("_", " ").title(): sum(row[stage] for row in summary["session_rows"]) for stage in STAGES}
st.bar_chart(stage_counts, horizontal=True)
st.caption("Counts represent sessions containing each event, regardless of event order.")

st.subheader("Daily session-start cohorts (UTC)")
st.dataframe(summary["daily_funnel"], use_container_width=True, hide_index=True)

st.subheader("Daily event activity (UTC)")
st.line_chart(summary["daily_activity"], x="date", y=["events", "active_users"])

with st.expander("Inspect sessions"):
    st.dataframe(summary["session_rows"], use_container_width=True, hide_index=True)

st.caption("Source: warehouse/dbt/seeds/bronze_events.csv • Demo dataset • M20 definitions")
