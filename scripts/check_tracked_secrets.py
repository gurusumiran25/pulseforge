"""Conservative content-based secret detection for tracked source files.

This complements filename hygiene, not full Git history or external secret scanning.
Only checks tracked regular files, avoids printing matched secret values.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

MAX_FILE_BYTES = 1_000_000
TOKEN_PATTERNS = (
    re.compile(rb"gh[pousr]_[A-Za-z0-9_]{30,}"),
    re.compile(rb"github_pat_[A-Za-z0-9_]{30,}"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
)
ASSIGNMENT = re.compile(
    rb"(?im)^\s*(?:export\s+)?(?:API_KEY|SECRET_KEY|ACCESS_TOKEN|AUTH_TOKEN|PASSWORD|PRIVATE_KEY)\s*[:=]\s*['\"]?([^\s'\"#]{12,})"
)
EXAMPLE_VALUES = {b"your_api_key_here", b"replace_me_here", b"example_token"}


def suspicious_content(raw: bytes) -> bool:
    if any(pattern.search(raw) for pattern in TOKEN_PATTERNS):
        return True
    return any(
        match.group(1).lower() not in EXAMPLE_VALUES
        and not match.group(1).startswith((b"${", b"{{", b"YOUR_", b"EXAMPLE_"))
        for match in ASSIGNMENT.finditer(raw)
    )


def scan_tracked(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=root, capture_output=True, check=True
    )
    failures = []
    for name in result.stdout.split(b"\0"):
        if not name:
            continue
        rel = name.decode("utf-8", errors="replace")
        # Synthetic test vectors intentionally contain credential-shaped strings.
        if rel == "tests/release/test_m83_secret_content.py":
            continue
        path = root / rel
        if not path.is_file() or path.is_symlink():
            continue
        if path.stat().st_size > MAX_FILE_BYTES:
            continue
        if suspicious_content(path.read_bytes()):
            failures.append(rel)
    return sorted(failures)


def main() -> None:
    failures = scan_tracked(Path.cwd())
    if failures:
        raise SystemExit("Potential secrets in tracked files (values redacted):\n" + "\n".join(failures))
    print("Tracked content secret patterns: no matches; history and advanced scanning still required.")


if __name__ == "__main__":
    main()
