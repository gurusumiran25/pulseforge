"""Offline warehouse health checks for a completed, reported batch.

Read-only checks of report, manifest, CSV and DuckDB mart presence.
"""
import argparse
import json
from pathlib import Path

from services.analytics.bronze_manifest import verify_manifest
from services.analytics.warehouse_quality import check_quality


REQUIRED_MARTS = ("stg_events", "fct_session_funnel", "agg_daily_funnel")


def check_warehouse(report_path):
    report_path = Path(report_path).resolve()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    issues = []
    if report.get("schema_version") != 1 or report.get("status") != "success":
        issues.append("Run report does not describe a successful schema-v1 batch")
    result = report.get("result") or {}
    warehouse_value = result.get("warehouse")
    manifest_value = result.get("manifest")
    if not warehouse_value or not manifest_value:
        issues.append("Missing warehouse or manifest path in run report")
        return {"healthy": False, "issues": issues}
    warehouse = Path(warehouse_value).resolve()
    manifest = Path(manifest_value).resolve()
    bronze = warehouse.parent / "dbt/seeds/bronze_events.csv"
    try:
        stats = verify_manifest(bronze, manifest)
        if stats["rows"] != result.get("events_exported"):
            issues.append("Reported event count differs from Bronze manifest")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        issues.append(f"Bronze integrity check failed: {type(exc).__name__}")
    if not warehouse.is_file():
        issues.append("DuckDB warehouse file is missing")
    else:
        try:
            import duckdb
        except ImportError:
            issues.append("duckdb is not installed; cannot verify marts")
        else:
            try:
                connection = duckdb.connect(str(warehouse), read_only=True)
                try:
                    names = {row[0] for row in connection.execute(
                        "SELECT table_name FROM information_schema.tables"
                    ).fetchall()}
                    for name in REQUIRED_MARTS:
                        if name not in names:
                            issues.append(f"Missing warehouse model: {name}")
                finally:
                    connection.close()
            except Exception as exc:
                issues.append(f"DuckDB inspection failed: {type(exc).__name__}")
    if warehouse.is_file():
        try:
            quality = check_quality(warehouse)
            if not quality["healthy"]:
                issues.extend(f"Semantic quality: {issue}" for issue in quality["issues"])
        except (OSError, ImportError, ValueError, RuntimeError) as exc:
            issues.append(f"Semantic quality inspection failed: {type(exc).__name__}")
    return {"healthy": not issues, "issues": issues}


def main():
    parser = argparse.ArgumentParser(description="Check a completed warehouse batch")
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    result = check_warehouse(args.report)
    print(json.dumps(result, indent=2))
    if not result["healthy"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
