"""Regression tests for Streamlit Cloud secrets and local overrides."""
from apps.dashboard.config import public_feed_enabled


class MissingSecrets:
    def get(self, key, default=None):
        raise FileNotFoundError("No secrets.toml")


def test_streamlit_cloud_secret_enables_public_feed():
    assert public_feed_enabled({"PULSEFORGE_PUBLIC_FEED": "1"}, environ={})


def test_environment_precedence_disables_cloud_secret():
    assert not public_feed_enabled(
        {"PULSEFORGE_PUBLIC_FEED": "1"},
        environ={"PULSEFORGE_PUBLIC_FEED": "0"},
    )


def test_environment_precedence_enables_without_secrets():
    assert public_feed_enabled(
        MissingSecrets(), environ={"PULSEFORGE_PUBLIC_FEED": "true"}
    )


def test_missing_secrets_fail_closed():
    assert not public_feed_enabled(MissingSecrets(), environ={})


def test_false_values_and_whitespace():
    assert public_feed_enabled(
        {"PULSEFORGE_PUBLIC_FEED": " YES "}, environ={}
    )
    assert not public_feed_enabled(
        {"PULSEFORGE_PUBLIC_FEED": "off"}, environ={}
    )
