"""PulseForge M21 — product analytics portfolio dashboard.

Run with: streamlit run apps/dashboard/streamlit_app.py
Reads a configurable Bronze-format CSV; not a direct DuckDB connection.
"""
import os
from pathlib import Path
from datetime import datetime, timezone

import streamlit as st
try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:
    # Minimal dev-only CI installs Streamlit without the optional dashboard extra.
    st_autorefresh = None

from apps.dashboard.metrics import SEED_PATH, STAGES, filter_complete_sessions, load_events, summarize
from apps.dashboard.public_feed import load_verified_public_feed
from apps.dashboard.payment_feed import load_verified_payment_feed
from services.analytics.rfm import calculate_rfm
from services.analytics.customer_value import calculate_observed_customer_value
from services.analytics.retention import calculate_retention
from apps.dashboard.retention_view import mask_immature_retention


st.set_page_config(page_title="PulseForge | Product Intelligence", page_icon="📊", layout="wide")
st.title("PulseForge")
if st_autorefresh is not None:
    st_autorefresh(interval=3_600_000, key="pulseforge-hourly-feed-refresh")
st.caption("Product intelligence • synthetic events, not production data")
# Streamlit Cloud stores app configuration in st.secrets; local deployments may
# supply the same non-sensitive flag through the process environment.
# Explicit environment settings take precedence when present.
def public_feed_enabled():
    configured = os.environ.get("PULSEFORGE_PUBLIC_FEED")
    if configured is None:
        try:
            configured = st.secrets.get("PULSEFORGE_PUBLIC_FEED", "0")
        except FileNotFoundError:
            configured = "0"
    return str(configured).strip().lower() in {"1", "true", "yes", "on"}


remote_enabled = public_feed_enabled()
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
    if remote_enabled:
        st.error(f"Dashboard feed unavailable: {type(exc).__name__}. Try refreshing later.")
    else:
        st.error(f"Unable to load event CSV: {exc}")
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

st.subheader("User activity retention by first observed UTC date")
retention = calculate_retention(events)
if retention["cohorts"]:
    st.dataframe(mask_immature_retention(
        retention["cohorts"], observation_end_date=max(event["event_time"].date() for event in events)
    ), use_container_width=True, hide_index=True)
else:
    st.caption("No observed user activity in the selected period.")
st.caption("D1/D7/D14/D30 count activity on exactly that UTC day after first observation. Unobservable follow-up days display blank rather than zero. Date filtering limits the observation window, so these are not lifetime acquisition cohorts.")


st.subheader("Synthetic customer purchase analytics")
st.caption("Gross RFM and observed net value are historical measures, not predictive CLV. Values are isolated by currency. Payment records are filtered by UTC activity dates and selected users; they are not exact session-start cohorts.")
if remote_enabled:
    try:
        @st.cache_data(ttl=3600, show_spinner=False)
        def get_payment_events(bronze_sha, generated_at_utc):
            return load_verified_payment_feed({"sha256": bronze_sha, "generated_at_utc": generated_at_utc})

        payment_events = get_payment_events(feed_manifest["sha256"], feed_manifest["generated_at_utc"])
        selected_users = {event["user_id"] for event in events}
        selected_dates = {event["event_time"].date() for event in events}
        payment_events = [
            event for event in payment_events
            if event["user_id"] in selected_users
            and datetime.fromisoformat(event["event_time"].replace("Z", "+00:00")).date() in selected_dates
        ]
        if payment_events:
            as_of = max(selected_dates)
            rfm = calculate_rfm(payment_events, as_of_date=as_of)
            values = calculate_observed_customer_value(payment_events)
            st.markdown("**RFM segments (gross successful orders)**")
            st.dataframe(rfm["customers"], use_container_width=True, hide_index=True)
            st.markdown("**Observed payment value (per currency)**")
            st.dataframe(values["customers"], use_container_width=True, hide_index=True)
        else:
            st.caption("No payments on the selected UTC activity dates for the selected users.")
    except Exception as exc:
        st.warning(f"Payment analytics temporarily unavailable ({type(exc).__name__}); main verified dashboard remains available.")
else:
    st.caption("Payment analytics require the verified public synthetic payment sidecar.")

st.subheader("Daily event activity (UTC)")
st.line_chart(summary["daily_activity"], x="date", y=["events", "active_users"])

with st.expander("Inspect sessions"):
    st.dataframe(summary["session_rows"], use_container_width=True, hide_index=True)

st.caption("Source: configured Bronze-format CSV • Synthetic data only • UTC session-start cohort definitions")
