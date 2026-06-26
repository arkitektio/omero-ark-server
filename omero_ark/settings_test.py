from .settings import *  # noqa
from .settings import DATABASES, AUTHENTIKATE
import logging

# Point Django at the test postgres from tests/integration/docker-compose.yaml
# (service `db`, published on 5556). Unit tests that only need the schema/models
# imported never open a connection, so this is harmless when no stack is running.
DATABASES["default"] = {
    "ENGINE": "django.db.backends.postgresql",
    "NAME": "testdb",
    "USER": "test",
    "PASSWORD": "test",
    "HOST": "localhost",
    "PORT": "5556",
}

# A fixed bearer token "test" authenticates as the user with sub="1" (see
# authentikate static-token expansion). Mirrors elektro's settings_test.
AUTHENTIKATE = {
    **AUTHENTIKATE,
    "static_tokens": {
        "test": {"sub": "1"},
    },
}


# Disable migrations for faster test-DB setup.
class DisableMigrations:
    """Disable migrations during testing for faster test execution."""

    def __contains__(self, item: str) -> bool:
        return True

    def __getitem__(self, item: str) -> None:
        return None


MIGRATION_MODULES = DisableMigrations()

# Quieten logging during tests.
logging.disable(logging.CRITICAL)

# In-memory channel layer instead of Redis.
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}

# Local-memory cache instead of django_redis, so the thumbnail/download views'
# @cache_page does not require a running Redis.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "omero-ark-test",
    }
}

# The OMERO server published by tests/integration/docker-compose.yaml. Per-user
# BlitzGateway connections (bridge/conn.py) and ensure_omero_user default to this.
OMERO_HOST = "localhost"
OMERO_PORT = 4064
