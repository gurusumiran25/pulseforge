"""M84 retry safety and bounded behavior."""
import pytest

from apps.dashboard.feed_retry import retry_verified_feed


def test_recovers_after_transient_digest_mismatch():
    calls = []
    def loader():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("digest mismatch")
        return {"verified": True}
    assert retry_verified_feed(loader, sleep=lambda _: None) == {"verified": True}
    assert len(calls) == 3


def test_permanent_integrity_failure_is_not_suppressed():
    calls = []
    def loader():
        calls.append(1)
        raise ValueError("integrity mismatch")
    with pytest.raises(ValueError, match="integrity mismatch"):
        retry_verified_feed(loader, attempts=2, sleep=lambda _: None)
    assert len(calls) == 2


def test_unexpected_programming_error_is_not_retried():
    calls = []
    def loader():
        calls.append(1)
        raise RuntimeError("bug")
    with pytest.raises(RuntimeError):
        retry_verified_feed(loader, sleep=lambda _: None)
    assert len(calls) == 1


def test_invalid_configuration():
    with pytest.raises(ValueError):
        retry_verified_feed(lambda: None, attempts=0)
