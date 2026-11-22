"""PulseForge M21 — product analytics portfolio dashboard.

Run with: streamlit run apps/dashboard/streamlit_app.py
Reads a configurable Bronze-format CSV; not a direct DuckDB connection.
"""
import os
from pathlib import Path

import streamlit as st

from apps.dashboard.metrics import SEED_PATH, STAGES, filter_complete_sessions, load_events, summarize


st.set_page_config(page_title="PulseForge | Product Intelligence", page_icon="📊", layout="wide")
st.title("PulseForge")
st.caption("Product intelligence • synthetic events, not production data")
source_path = Path(os.environ.get("PULSEFORGE_DASHBOARD_CSV", str(SEED_PATH))).expanduser()
st.caption(f"Configured CSV source: {source_path.name}")

@st.cache_data
def get_events(csv_path):
    return load_events(csv_path)

try:
    events = get_events(str(source_path))
except (OSError, ValueError) as exc:
    st.error(f"Unable to load event CSV: {exc}")
    st.stop()
dates = sorted({event["event_time"].date().isoformat() for event in events})
if dates:
    start, end = st.sidebar.select_slider(
        "Session-start cohort dates (UTC)",
        options=dates,
        value=(dates[0], dates[-1]),
    )
    events = filter_complete_sessions(events, start, end)

summary = summarize(events)
st.info("Session-stage participation is not an ordered conversion funnel. Date filtering selects complete sessions by first event UTC date.")
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

st.caption("Source: configured Bronze-format CSV • Synthetic data only • UTC session-start cohort definitions")
