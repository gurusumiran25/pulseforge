"""M33 real broker -> SQLite -> atomic Bronze export -> dbt parity.

Dedicated CI starts Redpanda and prepares an isolated dbt warehouse.
"""
import os
import subprocess
import time
from pathlib import Path
from uuid import uuid4

import pytest
from confluent_kafka.admin import AdminClient, NewTopic
from fastapi.testclient import TestClient

from services.analytics.bronze_export import export_bronze
from services.generator.journey_generator import generate_customer_journey
from services.ingestion.main import app, get_event_producer
from services.streaming.consumer import PulseForgeConsumer
from services.streaming.producer import PulseForgeProducer


@pytest.mark.skipif(not os.environ.get("M33_KAFKA_BOOTSTRAP"), reason="Requires dedicated M33 real-broker CI")
def test_real_broker_to_dbt_marts(tmp_path):
    duckdb = pytest.importorskip("duckdb")
    bootstrap = os.environ["M33_KAFKA_BOOTSTRAP"]
    suffix = uuid4().hex[:10]
    topic = f"pulseforge.m33.{suffix}"
    dlq = f"pulseforge.m33.dlq.{suffix}"
    admin = AdminClient({"bootstrap.servers": bootstrap})
    for future in admin.create_topics([
        NewTopic(topic, num_partitions=1, replication_factor=1),
        NewTopic(dlq, num_partitions=1, replication_factor=1),
    ]).values():
        future.result(timeout=30)

    events = [event for seed in range(10) for event in generate_customer_journey(seed=seed)]
    producer = PulseForgeProducer(bootstrap_servers=bootstrap, topic=topic)
    app.dependency_overrides[get_event_producer] = lambda: producer
    try:
        with TestClient(app) as client:
            response = client.post(
                "/v1/events/batch",
                json=[event.model_dump(mode="json") for event in events],
            )
        assert response.status_code == 202, response.text
        assert response.json()["published"] == len(events)
    finally:
        app.dependency_overrides.clear()

    consumer = PulseForgeConsumer(
        bootstrap_servers=bootstrap,
        topic=topic,
        dlq_topic=dlq,
        group_id=f"m33-{suffix}",
        db_path=tmp_path / "events.db",
        offset_reset="earliest",
    )
    processed = 0
    deadline = time.monotonic() + 60
    try:
        consumer.consumer.subscribe([topic])
        while processed < len(events) and time.monotonic() < deadline:
            message = consumer.consumer.poll(timeout=1.0)
            if message is None:
                continue
            assert consumer.process_message(message) == "inserted"
            processed += 1
    finally:
        consumer.consumer.close()
        consumer.dlq_producer.flush(5)
    assert processed == len(events)
    assert consumer.store.count_events() == len(events)

    sql = Path(__file__).resolve().parents[2] / "warehouse/sql/m20_views.sql"
    with consumer.store.connect() as connection:
        connection.executescript(sql.read_text(encoding="utf-8"))
        expected_sessions, expected_paid = connection.execute(
            "select count(*), coalesce(sum(completed_payment),0) from gold_session_funnel"
        ).fetchone()
        expected_daily = [
            list(row) for row in connection.execute(
                "select cohort_date_utc, sessions, sessions_with_product_view, "
                "sessions_with_cart, sessions_with_checkout, sessions_with_payment "
                "from gold_daily_funnel order by cohort_date_utc"
            ).fetchall()
        ]

    project = tmp_path / "dbt"
    from shutil import copytree
    copytree(Path(__file__).resolve().parents[2] / "warehouse/dbt", project)
    from shutil import rmtree
    rmtree(project / "tests")
    assert export_bronze(consumer.store.db_path, project / "seeds/bronze_events.csv") == len(events)
    (project / "profiles.yml").write_text(
        "pulseforge_warehouse:\n  target: ci\n  outputs:\n    ci:\n"
        "      type: duckdb\n      path: " + str(tmp_path / "warehouse.duckdb") + "\n"
        "      threads: 1\n",
        encoding="utf-8",
    )
    subprocess.run(["dbt", "build", "--profiles-dir", "."], cwd=project, check=True, timeout=120)

    with duckdb.connect(str(tmp_path / "warehouse.duckdb"), read_only=True) as conn:
        assert conn.execute("select count(*) from stg_events").fetchone()[0] == len(events)
        assert conn.execute("select count(*) from fct_session_funnel").fetchone()[0] == expected_sessions
        assert conn.execute(
            "select coalesce(sum(completed_payment),0) from fct_session_funnel"
        ).fetchone()[0] == expected_paid
        actual_daily = conn.execute(
            "select cast(cohort_date_utc as varchar), sessions, "
            "sessions_with_product_view, sessions_with_cart, "
            "sessions_with_checkout, sessions_with_payment "
            "from agg_daily_funnel order by cohort_date_utc"
        ).fetchall()
    assert [list(row) for row in actual_daily] == expected_daily
