"""Explicit one-shot SQLite -> Bronze -> dbt DuckDB batch orchestration.

No scheduler, broker connection or operational database mutation.
"""
import argparse
import shutil
import subprocess
from pathlib import Path

from services.analytics.bronze_export import export_bronze
from services.analytics.bronze_manifest import write_manifest, verify_manifest
from services.analytics.warehouse_quality import check_quality


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DBT_TEMPLATE = PROJECT_ROOT / "warehouse/dbt"


def run_warehouse_batch(db_path, workspace, *, dbt_executable="dbt"):
    """Create an isolated dbt project and build marts from a SQLite snapshot."""
    workspace = Path(workspace).resolve()
    source = Path(db_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"SQLite event database does not exist: {source}")
    if source == workspace or workspace in source.parents:
        raise ValueError("Workspace must not contain the source database")
    if workspace.exists() and any(workspace.iterdir()):
        raise FileExistsError(f"Workspace must be empty: {workspace}")
    workspace.mkdir(parents=True, exist_ok=True)
    project = workspace / "dbt"
    shutil.copytree(DBT_TEMPLATE, project)
    # Fixed six-row demo tests are not appropriate for arbitrary event snapshots.
    tests = project / "tests"
    if tests.exists():
        shutil.rmtree(tests)
    exported = export_bronze(source, project / "seeds/bronze_events.csv")
    bronze = project / "seeds/bronze_events.csv"
    manifest_path = workspace / "bronze.manifest.json"
    manifest = write_manifest(bronze, manifest_path)
    assert manifest["rows"] == exported
    verify_manifest(bronze, manifest_path)
    warehouse = workspace / "warehouse.duckdb"
    (project / "profiles.yml").write_text(
        "pulseforge_warehouse:\n  target: ci\n  outputs:\n    ci:\n"
        "      type: duckdb\n      path: " + str(warehouse) + "\n"
        "      threads: 1\n",
        encoding="utf-8",
    )
    verify_manifest(bronze, manifest_path)
    subprocess.run(
        [dbt_executable, "build", "--profiles-dir", "."],
        cwd=project,
        check=True,
        timeout=180,
    )
    quality = check_quality(warehouse)
    if not quality["healthy"]:
        raise ValueError("Warehouse data quality gate failed: " + "; ".join(quality["issues"]))
    return {"events_exported": exported, "warehouse": str(warehouse), "manifest": str(manifest_path), "quality": quality}


def main():
    parser = argparse.ArgumentParser(description="Build isolated DuckDB marts from SQLite")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    print(run_warehouse_batch(args.db_path, args.workspace))


if __name__ == "__main__":
    main()
