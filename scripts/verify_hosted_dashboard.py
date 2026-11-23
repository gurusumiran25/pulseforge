"""Read-only browser acceptance of the deployed public Streamlit dashboard.

Requires Playwright and a real Chromium browser. Does not mutate app data.
"""
import argparse
import json
from datetime import datetime, timezone

from playwright.sync_api import sync_playwright

APP_URL = "https://pulseforge-analytics.streamlit.app/"
REQUIRED = (
    "Source: public GitHub synthetic feed",
    "Last successful feed publication:",
    "Synthetic customer purchase analytics",
    "RFM segments (gross successful orders)",
    "Observed payment value (per currency)",
)


def check_text(text):
    missing = [item for item in REQUIRED if item not in text]
    forbidden = [
        phrase for phrase in (
            "Dashboard feed unavailable:",
            "Payment analytics temporarily unavailable",
            "Local CSV source:",
        ) if phrase in text
    ]
    return {"passed": not missing and not forbidden, "missing": missing, "errors": forbidden}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshot", default="dashboard-acceptance.png")
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        try:
            page.goto(APP_URL, wait_until="domcontentloaded", timeout=90000)
            page.get_by_text("Synthetic customer purchase analytics", exact=True).wait_for(timeout=120000)
            page.get_by_text("Observed payment value (per currency)", exact=True).wait_for(timeout=45000)
            page.screenshot(path=args.screenshot, full_page=True)
            outcome = check_text(page.locator("body").inner_text())
            outcome.update({
                "url": page.url,
                "checked_at_utc": datetime.now(timezone.utc).isoformat(),
                "screenshot": args.screenshot,
            })
            print(json.dumps(outcome, indent=2))
            if not outcome["passed"]:
                raise SystemExit("Hosted dashboard browser acceptance FAILED")
        finally:
            browser.close()


if __name__ == "__main__":
    main()
