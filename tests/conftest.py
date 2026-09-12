"""Pytest fixtures for omero-ark-server.

Two tiers of tests share this file:

* **unit** — pure logic (inputs, filters, config). No services; run on every
  ``pytest``.
* **integration** (``@pytest.mark.integration``) — boot a docker-compose stack
  (app postgres + redis + a dedicated PostgreSQL 12 + a real OMERO server) via
  ``dokker`` and exercise the GraphQL schema end-to-end. Opt-in: skipped unless
  you pass ``-m integration`` or ``--integration``.

The structure mirrors the sibling ``elektro`` mount's harness.
"""

import os
import socket
import time

import pytest


# ---------------------------------------------------------------------------
# Opt-in gating for the heavy OMERO integration tests.
# ---------------------------------------------------------------------------
def pytest_addoption(parser):
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="run the (slow) integration tests that boot the OMERO docker stack",
    )


def pytest_collection_modifyitems(config, items):
    markexpr = config.getoption("markexpr", default="") or ""
    # Run integration tests only when explicitly selected, either via the
    # --integration flag or a `-m` expression that mentions `integration`.
    if config.getoption("--integration") or "integration" in markexpr:
        return
    skip = pytest.mark.skip(
        reason="integration test: pass -m integration or --integration to run"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


# ---------------------------------------------------------------------------
# Backend stack (docker-compose via dokker).
# ---------------------------------------------------------------------------
def _wait_for_postgres(host, port, *, deadline_s=30):
    import psycopg

    deadline = time.monotonic() + deadline_s
    while True:
        try:
            with psycopg.connect(
                dbname="testdb",
                user="test",
                password="test",
                host=host,
                port=port,
                connect_timeout=1,
            ) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
            return
        except psycopg.OperationalError:
            if time.monotonic() >= deadline:
                raise
            time.sleep(0.2)


def _port_open(host, port, timeout=1.0):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((host, port))
        return True
    except OSError:
        return False
    finally:
        s.close()


def _wait_for_omero(host, port, *, deadline_s=600):
    """Wait until OMERO accepts an ICE root login.

    OMERO is notoriously slow to come up (image import, schema bootstrap), so
    this polls with a generous deadline: first the TCP port, then an actual
    BlitzGateway root connection (the port opens well before login works).
    """
    from omero.gateway import BlitzGateway

    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        if _port_open(host, port, timeout=2):
            conn = BlitzGateway("root", "omero", host=host, port=port)
            try:
                if conn.connect():
                    return
            except Exception:
                pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
        time.sleep(5)
    raise TimeoutError(f"OMERO server at {host}:{port} did not become ready in {deadline_s}s")


@pytest.fixture(scope="session")
def backend_stack():
    from dokker import testing

    docker_compose_path = os.path.join(
        os.path.dirname(__file__), "integration", "docker-compose.yaml"
    )

    with testing(docker_compose_path) as e:
        e.inspect()
        e.down()
        e.up()

        _wait_for_postgres("localhost", 5556)
        _wait_for_omero("localhost", 4064)

        yield


@pytest.fixture(scope="session")
def django_db_modify_db_settings(backend_stack):
    """Start the backend services before pytest-django configures the test DB."""
    yield


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    # Snapshot contenttypes/permissions once and restore them on each flush
    # instead of letting post_migrate rebuild them per transaction=True test.
    from django.contrib.auth.models import Permission
    from django.contrib.contenttypes.management import create_contenttypes
    from django.contrib.contenttypes.models import ContentType
    from django.db.models.signals import post_migrate

    with django_db_blocker.unblock():
        contenttypes = list(ContentType.objects.all())
        permissions = list(Permission.objects.all())

    post_migrate.disconnect(
        dispatch_uid="django.contrib.auth.management.create_permissions"
    )
    post_migrate.disconnect(create_contenttypes)

    def restore(sender, **kwargs):
        if getattr(sender, "label", None) != "contenttypes":
            return
        ContentType.objects.bulk_create(contenttypes, ignore_conflicts=True)
        Permission.objects.bulk_create(permissions, ignore_conflicts=True)

    post_migrate.connect(restore, dispatch_uid="tests.restore_contenttypes_and_permissions")
    yield

    # Async tests run sync ORM in asgiref executor threads whose connections
    # outlive the test and block dropping the test DB; terminate them first.
    from django.db import connections

    with django_db_blocker.unblock():
        with connections["default"].cursor() as cursor:
            cursor.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = current_database() AND pid <> pg_backend_pid()"
            )
        connections.close_all()


# ---------------------------------------------------------------------------
# Auth context + schema execution (mirrors elektro).
# ---------------------------------------------------------------------------
@pytest.fixture(scope="function")
def authenticated_context(db, backend_stack):
    """An HttpContext carrying the static "test" bearer token (sub="1")."""
    from authentikate.models import Client, User
    from kante.context import HttpContext, UniversalRequest
    from strawberry.http.temporal_response import TemporalResponse

    user, _ = User.objects.get_or_create(
        sub="1", iss="static_issuer", defaults={"username": "static_issuer_1"}
    )
    client, _ = Client.objects.get_or_create(client_id="omero-ark-test")

    request = UniversalRequest(
        _extensions={"token": "test"},
        _client=client,  # type: ignore
        _user=user,  # type: ignore
    )

    return HttpContext(
        request=request,
        response=TemporalResponse(),
        headers={"Authorization": "Bearer test"},
        type="http",
    )


@pytest.fixture
def aexecute(authenticated_context):
    """Run a GraphQL document against the schema with the authed context."""
    from omero_ark.schema import schema

    async def _run(query, variables=None, context=None):
        return await schema.execute(
            query,
            variable_values=variables or {},
            context_value=context or authenticated_context,
        )

    return _run


@pytest.fixture
def omero_root_user(authenticated_context):
    """Create an OmeroUser row for the authed user, pointing at the live OMERO.

    With this present, OmeroExtension.on_operation (bridge/conn.py) opens a real
    BlitzGateway as root for every GraphQL operation in the test.
    """
    from asgiref.sync import sync_to_async

    from bridge import models

    @sync_to_async
    def _make():
        user = authenticated_context.request.user
        obj, _ = models.OmeroUser.objects.update_or_create(
            user=user,
            defaults=dict(
                omero_username="root",
                omero_password="omero",
                omero_host="localhost",
                omero_port=4064,
            ),
        )
        return obj

    return _make
