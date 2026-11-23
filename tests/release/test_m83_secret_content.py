"""Content-based secret scanner regressions (synthetic fixtures only)."""
from scripts.check_tracked_secrets import suspicious_content


def test_rejects_github_classic_token_pattern():
    assert suspicious_content(b"ghp_" + b"A" * 36)


def test_rejects_github_fine_grained_token_pattern():
    assert suspicious_content(b"github_pat_" + b"B" * 60)


def test_rejects_aws_access_key_pattern():
    assert suspicious_content(b"AKIA" + b"Z" * 16)


def test_rejects_private_key_header():
    assert suspicious_content(b"-----BEGIN PRIVATE KEY-----")


def test_rejects_plaintext_password_assignment():
    assert suspicious_content(b"PASSWORD=long_synthetic_password_value")


def test_allows_placeholders_and_variable_names():
    assert not suspicious_content(b"PASSWORD=YOUR_PASSWORD_HERE\nAPI_KEY=${API_KEY}\n")
    assert not suspicious_content(b"SECRET_KEY=example_token\n")


def test_does_not_flag_descriptive_documentation():
    assert not suspicious_content(b"Do not commit credentials, private keys or passwords.")
