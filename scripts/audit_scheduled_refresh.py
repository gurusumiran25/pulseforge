"""Audit consecutive scheduled publisher runs via read-only GitHub Actions API."""
import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

REPOSITORY = "gurusumiran25/pulseforge"
WORKFLOW = "daily-public-feed.yml"


def scheduled_evidence(runs, *, required=2):
    scheduled = sorted(
        (run for run in runs if run.get("event") == "schedule"),
        key=lambda run: run.get("created_at", ""),
        reverse=True,
    )
    recent = scheduled[:required]
    passed = len(recent) == required and all(
        run.get("status") == "completed" and run.get("conclusion") == "success"
        for run in recent
    )
    # Runs on different UTC calendar dates establish consecutive observed daily
    # executions only when dates are actually adjacent, not merely two successes.
    if passed:
        dates = [datetime.fromisoformat(run["created_at"].replace("Z", "+00:00")).date() for run in recent]
        passed = all(dates[i] - dates[i + 1] == timedelta(days=1) for i in range(len(dates) - 1))
    return {
        "verified": passed,
        "required_consecutive_days": required,
        "observed": [
            {
                "id": run.get("id"),
                "created_at": run.get("created_at"),
                "conclusion": run.get("conclusion"),
                "url": run.get("html_url"),
            }
            for run in recent
        ],
    }


def fetch_runs(token, *, per_page=50):
    params = urlencode({"event": "schedule", "per_page": per_page})
    url = f"https://api.github.com/repos/{REPOSITORY}/actions/workflows/{WORKFLOW}/runs?{params}"
    request = Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "PulseForge-release-evidence",
    })
    with urlopen(request, timeout=15) as response:
        return json.load(response)["workflow_runs"]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--required", type=int, default=2)
    args = parser.parse_args()
    if args.required < 2:
        parser.error("required must be at least two")
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise SystemExit("GITHUB_TOKEN is required for read-only workflow audit")
    result = scheduled_evidence(fetch_runs(token), required=args.required)
    print(json.dumps(result, indent=2))
    if not result["verified"]:
        raise SystemExit("Consecutive scheduled publisher evidence NOT verified")


if __name__ == "__main__":
    main()
