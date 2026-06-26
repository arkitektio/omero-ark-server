"""Validate the omero-ark-server service's config.yaml against its bespoke schema.

Standalone — needs no database; run with ``uv run pytest tests/test_config.py``.
"""

from omero_ark.configuration import Settings


def test_config_yaml_validates():
    """The service's own config.yaml parses into the typed schema."""
    s = Settings()
    assert s.postgres.db_name
    assert s.redis.host


def test_env_override(monkeypatch):
    """Env vars override the YAML file (nested via ``__``)."""
    monkeypatch.setenv("POSTGRES__PASSWORD", "from-env-test")
    assert Settings().postgres.password == "from-env-test"


def test_omero_defaults():
    """omero_host/omero_port fall back to their schema defaults.

    config.yaml carries a nested ``omero:`` block, but the schema declares flat
    ``omero_host``/``omero_port`` scalars, so the defaults apply unless an env
    var (OMERO_HOST / OMERO_PORT) overrides them.
    """
    s = Settings()
    assert s.omero_host == "omero"
    assert s.omero_port == 4064


def test_omero_host_env_override(monkeypatch):
    """OMERO_HOST env var overrides the omero_host default."""
    monkeypatch.setenv("OMERO_HOST", "from-env-omero")
    assert Settings().omero_host == "from-env-omero"
