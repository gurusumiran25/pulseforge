"""PulseForge M21 — product analytics portfolio dashboard.

Run with: streamlit run apps/dashboard/streamlit_app.py
Reads a configurable Bronze-format CSV; not a direct DuckDB connection.
"""
import os
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from apps.dashboard.metrics import SEED_PATH, STAGES, filter_complete_sessions, load_events, summarize
from apps.dashboard.public_feed import load_verified_public_feed


st.set_page_config(page_title="PulseForge | Product Intelligence", page_icon="📊", layout="wide")
st.title("PulseForge")
st_autorefresh(interval=3_600_000, key="pulseforge-hourly-feed-refresh")
st.caption("Product intelligence • synthetic events, not production data")
remote_enabled = os.environ.get("PULSEFORGE_PUBLIC_FEED", "0") == "1"
source_path = Path(os.environ.get("PULSEFORGE_DASHBOARD_CSV", str(SEED_PATH))).expanduser()

@st.cache_data(ttl=3600, show_spinner=False)
def get_events(csv_path, remote):
    if remote:
        return load_verified_public_feed()
    return load_events(csv_path), None

try:
    events, feed_manifest = get_events(str(source_path), remote_enabled)
except Exception as exc:
    # Do not silently fall back to stale seed data when the live feed fails.
    st.error(f"Dashboard feed unavailable: {type(exc).__name__}. Try refreshing later.")
    st.stop()

if remote_enabled:
    st.caption("Source: public GitHub synthetic feed • hourly cache refresh • SHA-256 verified")
    generated_at = datetime.fromisoformat(feed_manifest["generated_at_utc"])
    age_hours = (datetime.now(timezone.utc) - generated_at.astimezone(timezone.utc)).total_seconds() / 3600
    st.caption(f"Last successful feed publication: {generated_at:%Y-%m-%d %H:%M} UTC")
    if age_hours > 36:
        st.warning(f"Data refresh overdue: last verified publication {age_hours:.0f} hours ago. Check GitHub Actions.")
    st.caption("Data refreshes when the scheduled publisher succeeds; GitHub Actions timing is not guaranteed.")
else:
    st.caption(f"Local CSV source: {source_path.name} • enable PULSEFORGE_PUBLIC_FEED=1 in Streamlit Cloud to use daily data")

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
