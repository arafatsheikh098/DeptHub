import pytest

from app.config import Settings


def test_production_boot_refuses_default_secret_key():
    err_pattern = "Production refuses to start with default or insecure SECRET_KEY"
    with pytest.raises(ValueError, match=err_pattern):
        Settings(
            ENV="production",
            SECRET_KEY="insecure-dev-secret-key-change-in-production",
        )


def test_production_boot_refuses_empty_secret_key():
    err_pattern = "Production refuses to start with default or insecure SECRET_KEY"
    with pytest.raises(ValueError, match=err_pattern):
        Settings(
            ENV="production",
            SECRET_KEY="",
        )


def test_production_boot_allows_secure_secret_key():
    settings = Settings(
        ENV="production",
        SECRET_KEY="a-very-secure-random-32-byte-hex-string-for-prod",
    )
    assert settings.SECRET_KEY == "a-very-secure-random-32-byte-hex-string-for-prod"
