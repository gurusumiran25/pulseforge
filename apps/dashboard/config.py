"""Resolve the public synthetic feed flag across Streamlit Cloud and local runs."""
import os


def public_feed_enabled(secrets=None, *, environ=None):
    """Explicit process environment takes precedence over Streamlit secrets."""
    env = os.environ if environ is None else environ
    value = env.get("PULSEFORGE_PUBLIC_FEED")
    if value is None and secrets is not None:
        try:
            value = secrets.get("PULSEFORGE_PUBLIC_FEED", "0")
        except (FileNotFoundError, KeyError):
            value = "0"
    return str(value if value is not None else "0").strip().lower() in {
        "1", "true", "yes", "on"
    }
