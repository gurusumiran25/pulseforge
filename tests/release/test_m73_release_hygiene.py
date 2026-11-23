"""Regression coverage for M73 tracked-artifact hygiene."""
from scripts.check_release_hygiene import unsafe_paths


def test_blocks_private_credentials_and_local_databases():
    assert unsafe_paths([
        ".env", ".env.production", "config/id_rsa",
        "secrets/service-account.json", "data/storage/events.sqlite",
        "warehouse/local.duckdb", "data/generated/events.jsonl",
    ]) == sorted([
        ".env", ".env.production", "config/id_rsa",
        "secrets/service-account.json", "data/storage/events.sqlite",
        "warehouse/local.duckdb", "data/generated/events.jsonl",
    ])


def test_allows_public_synthetic_feed_and_source_files():
    assert unsafe_paths([
        "data/public/latest_bronze.csv",
        "data/public/latest_payments.csv",
        "scripts/check_release_hygiene.py",
        ".env.example",
        "tests/release/test_m73_release_hygiene.py",
    ]) == []
