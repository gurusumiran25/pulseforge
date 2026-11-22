"""Bounded retries for explicitly invoked warehouse builds.

Every attempt gets a fresh isolated workspace and a separate run report.
Only explicitly classified transient errors are retried.
"""
import argparse
import json
import subprocess
import time
from pathlib import Path

from services.analytics.warehouse_run_report import run_reported_batch


def is_retryable(error):
    """Retry only transient dbt subprocess failures (not integrity or input errors)."""
    # A dbt nonzero exit is not evidence of a transient failure: it can mean
    # invalid SQL, broken models, failing dbt tests, or malformed input.
    # Retrying such deterministic failures only repeats work.
    return isinstance(error, subprocess.TimeoutExpired)


def run_with_retries(db_path, output_root, *, max_attempts=3, delay_seconds=0, dbt_executable="dbt"):
    if not 1 <= max_attempts <= 5:
        raise ValueError("max_attempts must be between 1 and 5")
    if not 0 <= delay_seconds <= 60:
        raise ValueError("delay_seconds must be between 0 and 60")
    root = Path(output_root).resolve()
    source = Path(db_path).resolve()
    if source == root or root in source.parents:
        raise ValueError("Retry output root cannot contain the source database")
    if root.exists() and any(root.iterdir()):
        raise FileExistsError(f"Retry output root must be empty: {root}")
    root.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, max_attempts + 1):
        workspace = root / f"attempt-{attempt}"
        report = root / f"attempt-{attempt}.json"
        try:
            return run_reported_batch(
                source, workspace, report, dbt_executable=dbt_executable
            )
        except Exception as exc:
            if attempt == max_attempts or not is_retryable(exc):
                raise
            if delay_seconds:
                time.sleep(delay_seconds)
    raise RuntimeError("Unreachable retry state")


def main():
    parser = argparse.ArgumentParser(description="Run isolated warehouse batch with bounded retries")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--max-attempts", type=int, default=3)
    parser.add_argument("--delay-seconds", type=float, default=0)
    args = parser.parse_args()
    result = run_with_retries(
        args.db_path, args.output_root,
        max_attempts=args.max_attempts, delay_seconds=args.delay_seconds,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
