"""Fail closed on obviously private or generated artifacts tracked by Git.

This is a tracked-filename hygiene gate, not a substitute for content secret
scanning, repository history review, or manual security assessment.
"""
from __future__ import annotations

import subprocess
from pathlib import PurePosixPath

BLOCKED_NAMES = {
    ".env", "id_rsa", "id_ed25519", "credentials.json",
    "service-account.json", "service_account.json",
}
BLOCKED_SUFFIXES = (
    ".pem", ".p12", ".pfx", ".key", ".sqlite", ".sqlite3",
    ".duckdb", ".db", ".duckdb.wal", ".sqlite-wal", ".sqlite-shm",
)
BLOCKED_DIRECTORIES = {
    ".venv", "__pycache__", ".pytest_cache", ".ruff_cache",
}
ALLOWED_PUBLIC_FILES = {
    "data/public/latest_bronze.csv",
    "data/public/latest_bronze.manifest.json",
    "data/public/latest_payments.csv",
    "data/public/status.json",
}


def unsafe_paths(paths: list[str]) -> list[str]:
    failures = []
    for raw in paths:
        path = PurePosixPath(raw)
        parts = path.parts
        name = path.name.lower()
        if not parts or raw == ".env.example" or raw in ALLOWED_PUBLIC_FILES:
            continue
        if (
            (len(parts) >= 2 and parts[0] == "data" and parts[1] == "public")
            or any(part in BLOCKED_DIRECTORIES for part in parts)
            or name in BLOCKED_NAMES
            or name.startswith(".env.")
            or name.endswith(BLOCKED_SUFFIXES)
            or name.startswith("id_rsa.")
            or name.startswith("id_ed25519.")
            or (len(parts) >= 2 and parts[0] == "data" and parts[1] in {"generated", "storage"})
        ):
            failures.append(raw)
    return sorted(failures)


def main() -> None:
    result = subprocess.run(
        ["git", "ls-files", "-z"], check=True, capture_output=True
    )
    paths = [p.decode("utf-8", errors="replace") for p in result.stdout.split(b"\0") if p]
    failures = unsafe_paths(paths)
    if failures:
        raise SystemExit("Blocked tracked artifacts:
" + "
".join(failures))
    print(f"Tracked artifact hygiene passed for {len(paths)} files; content/history scanning still required.")


if __name__ == "__main__":
    main()
