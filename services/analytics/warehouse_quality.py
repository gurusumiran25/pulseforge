"""Read-only semantic quality gates for PulseForge DuckDB marts."""
import argparse
import json
from pathlib import Path


def check_quality(warehouse_path):
    import duckdb

    path = Path(warehouse_path)
    if not path.is_file():
        raise FileNotFoundError(f"Warehouse does not exist: {path}")
    issues = []
    con = duckdb.connect(str(path), read_only=True)
    try:
        checks = {
            "duplicate_event_ids": """
                SELECT count(*) - count(distinct event_id) FROM stg_events
            """,
            "null_required_event_fields": """
                SELECT count(*) FROM stg_events
                WHERE event_id IS NULL OR event_name IS NULL
                   OR session_id IS NULL OR user_id IS NULL OR event_time IS NULL
            """,
            "duplicate_session_rows": """
                SELECT count(*) - count(distinct session_id) FROM fct_session_funnel
            """,
            "invalid_session_flags": """
                SELECT count(*) FROM fct_session_funnel
                WHERE event_count < 1
                   OR viewed_product NOT IN (0,1) OR added_to_cart NOT IN (0,1)
                   OR started_checkout NOT IN (0,1)
                   OR completed_payment NOT IN (0,1)
            """,
            "session_event_count_mismatch": """
                SELECT CASE WHEN
                    (SELECT coalesce(sum(event_count),0) FROM fct_session_funnel)
                    = (SELECT count(*) FROM stg_events)
                    THEN 0 ELSE 1 END
            """,
            "daily_session_count_mismatch": """
                SELECT CASE WHEN
                    (SELECT coalesce(sum(sessions),0) FROM agg_daily_funnel)
                    = (SELECT count(*) FROM fct_session_funnel)
                    THEN 0 ELSE 1 END
            """,
            "invalid_daily_funnel_counts": """
                SELECT count(*) FROM agg_daily_funnel
                WHERE sessions < 0
                   OR sessions_with_product_view < 0
                   OR sessions_with_cart < 0
                   OR sessions_with_checkout < 0
                   OR sessions_with_payment < 0
                   OR sessions_with_product_view > sessions
                   OR sessions_with_cart > sessions
                   OR sessions_with_checkout > sessions
                   OR sessions_with_payment > sessions
            """,
            "daily_aggregate_mismatch": """
                WITH expected AS (
                    SELECT cast(first_event_time as date) AS cohort_date_utc,
                        count(*) AS sessions,
                        sum(viewed_product) AS sessions_with_product_view,
                        sum(added_to_cart) AS sessions_with_cart,
                        sum(started_checkout) AS sessions_with_checkout,
                        sum(completed_payment) AS sessions_with_payment
                    FROM fct_session_funnel GROUP BY 1
                )
                SELECT count(*) FROM (
                    (SELECT * FROM expected EXCEPT SELECT * FROM agg_daily_funnel)
                    UNION ALL
                    (SELECT * FROM agg_daily_funnel EXCEPT SELECT * FROM expected)
                )
            """,
        }
        for name, sql in checks.items():
            try:
                count = con.execute(sql).fetchone()[0]
                if count:
                    issues.append(f"{name}: {count}")
            except Exception as exc:
                issues.append(f"{name}: query failed ({type(exc).__name__})")
    finally:
        con.close()
    return {"healthy": not issues, "issues": issues, "checks": len(checks)}


def main():
    parser = argparse.ArgumentParser(description="Validate warehouse semantic data quality")
    parser.add_argument("--warehouse", required=True)
    args = parser.parse_args()
    result = check_quality(args.warehouse)
    print(json.dumps(result, indent=2))
    if not result["healthy"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
