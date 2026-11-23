"""Check temporal evidence of postpublisher monitor runs.

This cannot establish exact triggering run IDs from workflow-run listings alone.
"""
import argparse
import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.audit_scheduled_refresh import scheduled_evidence

REPO = "gurusumiran25/pulseforge"
WORKFLOWS = {
    "publisher": "daily-public-feed.yml",
    "health": "m55-public-feed-health.yml",
    "remote": "m74-remote-publication-smoke.yml",
}


def timestamp(run):
    return datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")).astimezone(timezone.utc)


def monitor_evidence(publisher_runs, health_runs, remote_runs, *, required=2):
    scheduled = sorted(
        (r for r in publisher_runs if r.get("event") == "schedule"),
        key=timestamp, reverse=True,
    )[:required]
    evidence = []
    for publish in scheduled:
        monitors = {}
        for name, candidates in (("health", health_runs), ("remote", remote_runs)):
            matches = sorted(
                (
                    r for r in candidates
                    if r.get("event") == "workflow_run"
                    and r.get("status") == "completed"
                    and timestamp(r) >= timestamp(publish)
                ),
                key=timestamp,
            )
            # Time-window association is not proof of exact triggering run ID.
            matches = [r for r in matches if (timestamp(r) - timestamp(publish)).total_seconds() <= 5400]
            monitors[name] = {
                "verified": bool(matches and matches[0].get("conclusion") == "success"),
                "run_url": matches[0].get("html_url") if matches else None,
            }
        evidence.append({
            "publisher_url": publish.get("html_url"),
            "publisher_success": publish.get("status") == "completed" and publish.get("conclusion") == "success",
            "health": monitors["health"],
            "remote": monitors["remote"],
        })
    scheduled_ok = scheduled_evidence(publisher_runs, required=required)["verified"]
    return {
        "association": "temporal_only_not_exact_trigger_proof",
        "verified": scheduled_ok and len(evidence) == required and all(
            row["publisher_success"] and row["health"]["verified"] and row["remote"]["verified"]
            for row in evidence
        ),
        "observed": evidence,
    }


def fetch(token, workflow):
    params = urlencode({"per_page": 100})
    url = f"https://api.github.com/repos/{REPO}/actions/workflows/{workflow}/runs?{params}"
    request = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "PulseForge-monitor-evidence",
    })
    with urlopen(request, timeout=20) as response:
        return json.load(response)["workflow_runs"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--required", type=int, default=2)
    args = parser.parse_args()
    if args.required < 2:
        parser.error("required must be >= 2")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN required")
    runs = {name: fetch(token, path) for name, path in WORKFLOWS.items()}
    result = monitor_evidence(runs["publisher"], runs["health"], runs["remote"], required=args.required)
    print(json.dumps(result, indent=2))
    if not result["verified"]:
        raise SystemExit("Independent monitoring evidence NOT verified")


if __name__ == "__main__":
    main()
