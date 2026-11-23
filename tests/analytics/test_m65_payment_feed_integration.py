"""M65 integration: sidecar and Bronze are produced from one synthetic snapshot."""
import json
import os
from datetime import date

import pytest

from services.analytics.daily_public_feed import build_public_feed
from services.analytics.payment_sidecar import load_payment_sidecar
from services.analytics.bronze_manifest import inspect_bronze


@pytest.mark.skipif(os.getenv("PULSEFORGE_RUN_M53_DAILY") != "1", reason="Real dbt integration opt-in")
def test_daily_public_feed_publishes_verified_payment_sidecar(tmp_path):
    output = tmp_path / "public"
    status = build_public_feed(output, as_of=date(2026, 11, 23), days=2, sessions_per_day=3)
    metadata = status["payment_sidecar"]
    assert metadata["schema_version"] == 1
    assert metadata["bronze_sha256"] == inspect_bronze(output / "latest_bronze.csv")["sha256"]
    events = load_payment_sidecar(
        output / "latest_payments.csv",
        expected_sha256=metadata["sha256"],
        expected_rows=metadata["rows"],
    )
    assert len(events) == metadata["rows"]
    assert json.loads((output / "status.json").read_text())["payment_sidecar"] == metadata
