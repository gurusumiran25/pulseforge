"""M80 hosted dashboard acceptance text regression tests."""
from scripts.verify_hosted_dashboard import check_text, REQUIRED


def test_complete_public_dashboard_passes():
    assert check_text(" ".join(REQUIRED))["passed"]


def test_local_seed_mode_rejected():
    assert not check_text(" ".join(REQUIRED) + " Local CSV source: seed.csv")["passed"]


def test_payment_warning_rejected():
    assert not check_text(" ".join(REQUIRED) + " Payment analytics temporarily unavailable")["passed"]


def test_missing_customer_table_rejected():
    assert not check_text(" ".join(REQUIRED[:-1]))["passed"]
