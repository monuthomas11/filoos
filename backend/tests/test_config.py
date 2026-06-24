"""Tests for application configuration loading."""

from __future__ import annotations

import os
from unittest.mock import patch


def test_settings_load_with_defaults():
    """Settings should load with sensible defaults."""
    from app.config import Settings

    # Clear any FF_ env vars that might be set
    env_clean = {k: v for k, v in os.environ.items() if not k.startswith("FF_")}
    with patch.dict(os.environ, env_clean, clear=True):
        settings = Settings()
        assert settings.app_name == "Filoos"
        assert settings.app_env == "development"
        assert settings.debug is True
        assert settings.default_currency == "INR"
        assert settings.currency_symbol == "₹"
        assert settings.forecast_history_days == 180
        assert settings.forecast_cache_ttl_seconds == 300


def test_settings_load_with_ff_prefix():
    """FF_ prefixed env vars should be read correctly."""
    from app.config import Settings

    env_with_prefix = {
        "FF_APP_NAME": "TestApp",
        "FF_APP_ENV": "production",
        "FF_DEBUG": "false",
        "FF_DEFAULT_CURRENCY": "USD",
        "FF_CURRENCY_SYMBOL": "$",
        "FF_FORECAST_HISTORY_DAYS": "365",
        "FF_FORECAST_CACHE_TTL_SECONDS": "600",
    }
    with patch.dict(os.environ, env_with_prefix, clear=False):
        settings = Settings()
        assert settings.app_name == "TestApp"
        assert settings.app_env == "production"
        assert settings.debug is False
        assert settings.default_currency == "USD"
        assert settings.currency_symbol == "$"
        assert settings.forecast_history_days == 365
        assert settings.forecast_cache_ttl_seconds == 600


def test_settings_legacy_env_vars_backward_compatibility():
    """Legacy unprefixed env vars should still work for backward compatibility."""
    from app.config import Settings

    # Clear FF_ vars and set legacy vars
    env_clean = {k: v for k, v in os.environ.items() if not k.startswith("FF_")}
    env_legacy = {
        "APP_NAME": "LegacyApp",
        "APP_ENV": "production",
        "DEBUG": "false",
        "DEFAULT_CURRENCY": "EUR",
        "CURRENCY_SYMBOL": "€",
    }
    env_clean.update(env_legacy)

    with patch.dict(os.environ, env_clean, clear=True):
        # Disable .env loading so the test is isolated from the project's
        # checked-in configuration. The legacy migration only fires when the
        # FF_-prefixed counterpart is unset in the environment AND not pulled
        # in from the .env file.
        settings = Settings(_env_file=None)
        assert settings.app_name == "LegacyApp"
        assert settings.app_env == "production"
        assert settings.debug is False
        assert settings.default_currency == "EUR"
        assert settings.currency_symbol == "€"


def test_settings_ff_prefix_takes_precedence_over_legacy():
    """FF_ prefixed vars should take precedence over legacy unprefixed vars."""
    from app.config import Settings

    env_mixed = {
        "FF_APP_NAME": "NewApp",
        "APP_NAME": "OldApp",
        "FF_APP_ENV": "production",
        "APP_ENV": "development",
    }
    with patch.dict(os.environ, env_mixed, clear=False):
        # Clear any other FF_ or legacy vars that might interfere
        env_clean = {
            k: v
            for k, v in os.environ.items()
            if k in env_mixed or not k.startswith(("FF_", "APP_"))
        }
        env_clean.update(env_mixed)
        with patch.dict(os.environ, env_clean, clear=True):
            settings = Settings()
            # FF_ prefixed should take precedence
            assert settings.app_name == "NewApp"
            assert settings.app_env == "production"


def test_settings_unrelated_env_vars_ignored():
    """Unrelated env vars should not affect settings loading."""
    from app.config import Settings

    env_with_unrelated = {
        "FF_APP_NAME": "TestApp",
        "RANDOM_VAR": "should_be_ignored",
        "ANOTHER_VAR": "12345",
        "DATABASE_URL_UNRELATED": "should_not_affect",
        "PATH": "/usr/bin:/usr/local/bin",  # System env var
    }
    with patch.dict(os.environ, env_with_unrelated, clear=False):
        settings = Settings()
        assert settings.app_name == "TestApp"
        # Should still have default values for other fields
        assert settings.app_env == "development"
        assert settings.debug is True


def test_settings_is_development_property():
    """is_development property should work correctly."""
    from app.config import Settings

    with patch.dict(os.environ, {"FF_APP_ENV": "development"}, clear=False):
        settings = Settings()
        assert settings.is_development is True

    with patch.dict(os.environ, {"FF_APP_ENV": "production"}, clear=False):
        settings = Settings()
        assert settings.is_development is False


def test_settings_database_url_default():
    """Database URL should have a sensible default."""
    from app.config import Settings

    settings = Settings()
    assert "sqlite:///" in settings.database_url
    assert "expenses.db" in settings.database_url


def test_database_url_translates_bare_postgresql_to_psycopg():
    """A bare ``postgresql://`` URL must be rewritten to ``postgresql+psycopg://``.

    Managed-database dashboards (Neon, Supabase, RDS) hand out
    connection strings with the bare ``postgresql://`` scheme, which
    SQLAlchemy defaults to the psycopg2 driver. We only ship
    ``psycopg`` v3, so the Settings class auto-translates the scheme
    so the user can paste the connection string verbatim.
    """
    from app.config import Settings

    with patch.dict(os.environ, {}, clear=True):
        url = Settings(
            _env_file=None,
            database_url="postgresql://u:p@ep-foo-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require",
        ).database_url
        assert url.startswith("postgresql+psycopg://")
        assert "sslmode=require" in url
        assert "ep-foo-pooler" in url


def test_database_url_translates_postgres_short_scheme():
    """The ``postgres://`` short form must also be rewritten."""
    from app.config import Settings

    with patch.dict(os.environ, {}, clear=True):
        url = Settings(
            _env_file=None,
            database_url="postgres://u:p@host/db",
        ).database_url
        assert url == "postgresql+psycopg://u:p@host/db"


def test_database_url_preserves_explicit_driver():
    """An explicit driver prefix must NOT be overwritten."""
    from app.config import Settings

    with patch.dict(os.environ, {}, clear=True):
        psycopg_url = Settings(
            _env_file=None,
            database_url="postgresql+psycopg://u:p@host/db",
        ).database_url
        psycopg2_url = Settings(
            _env_file=None,
            database_url="postgresql+psycopg2://u:p@host/db",
        ).database_url
        assert psycopg_url == "postgresql+psycopg://u:p@host/db"
        assert psycopg2_url == "postgresql+psycopg2://u:p@host/db"


def test_database_url_leaves_sqlite_alone():
    """SQLite URLs must pass through untouched."""
    from app.config import Settings

    with patch.dict(os.environ, {}, clear=True):
        url = Settings(
            _env_file=None,
            database_url="sqlite:///./data/dev.db",
        ).database_url
        assert url == "sqlite:///./data/dev.db"


def test_database_url_normalizes_when_set_via_env():
    """Normalization must fire when ``FF_DATABASE_URL`` comes from the env (Render)."""
    from app.config import Settings

    env_clean = {k: v for k, v in os.environ.items() if not k.startswith("FF_")}
    env_clean["FF_DATABASE_URL"] = "postgresql://u:p@ep-foo-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require"
    with patch.dict(os.environ, env_clean, clear=True):
        settings = Settings(_env_file=None)
        assert settings.database_url.startswith("postgresql+psycopg://")
        assert "sslmode=require" in settings.database_url
