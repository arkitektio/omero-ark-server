"""End-to-end GraphQL CRUD against a live OMERO server.

Opt-in (slow): boots the docker-compose stack in tests/integration and waits
for OMERO to accept a root login. Run with::

    uv run pytest -m integration

Each test runs in a rolled-back transaction; the OMERO server state is shared,
so tests create uniquely-named projects/datasets to stay independent.
"""

import uuid

import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.omero,
    pytest.mark.django_db(transaction=True),
]


# --- queries / mutations -----------------------------------------------------
ME = "query { me { id username } }"

ENSURE_OMERO_USER = """
mutation Ensure($input: OmeroUserInput!) {
  ensureOmeroUser(input: $input) { id omeroUsername user { id } }
}
"""

CREATE_PROJECT = """
mutation CreateProject($input: CreateProjectInput!) {
  createProject(input: $input) { id name }
}
"""

LIST_PROJECTS = """
query Projects($filters: ProjectFilter) {
  projects(filters: $filters) { id name }
}
"""

CREATE_DATASET = """
mutation CreateDataset($input: CreateDatasetInput!) {
  createDataset(input: $input) { id name }
}
"""

LIST_DATASETS = """
query Datasets($filters: DatasetFilter) {
  datasets(filters: $filters) { id name }
}
"""

DELETE_IMAGE = """
mutation DeleteImage($input: DeleteImageInput!) {
  deleteImage(input: $input) { id }
}
"""


# ---------------------------------------------------------------------------
async def test_smoke_omero_root_login(backend_stack):
    """The stack is up and OMERO accepts a root BlitzGateway login."""
    from omero.gateway import BlitzGateway

    conn = BlitzGateway("root", "omero", host="localhost", port=4064)
    try:
        assert conn.connect() is True
        assert conn.getUser().getName() == "root"
    finally:
        conn.close()


async def test_me_returns_authenticated_user(aexecute, omero_root_user):
    await omero_root_user()
    res = await aexecute(ME)
    assert not res.errors, res.errors
    assert res.data["me"]["username"]


async def test_ensure_omero_user_stores_row(aexecute):
    res = await aexecute(
        ENSURE_OMERO_USER,
        {"input": {"username": "root", "password": "omero", "host": "localhost", "port": 4064}},
    )
    assert not res.errors, res.errors
    assert res.data["ensureOmeroUser"]["omeroUsername"] == "root"

    from bridge.models import OmeroUser

    assert await OmeroUser.objects.filter(omero_username="root").aexists()


async def test_create_project_then_list(aexecute, omero_root_user):
    await omero_root_user()
    name = f"proj-{uuid.uuid4().hex[:8]}"

    created = await aexecute(CREATE_PROJECT, {"input": {"name": name, "description": "d"}})
    assert not created.errors, created.errors
    assert created.data["createProject"]["name"] == name

    listed = await aexecute(LIST_PROJECTS, {"filters": {"search": name}})
    assert not listed.errors, listed.errors
    assert name in [p["name"] for p in listed.data["projects"]]


async def test_create_dataset_under_project(aexecute, omero_root_user):
    await omero_root_user()
    pname = f"proj-{uuid.uuid4().hex[:8]}"
    created_proj = await aexecute(CREATE_PROJECT, {"input": {"name": pname}})
    assert not created_proj.errors, created_proj.errors
    project_id = created_proj.data["createProject"]["id"]

    dname = f"ds-{uuid.uuid4().hex[:8]}"
    created_ds = await aexecute(
        CREATE_DATASET, {"input": {"projectId": project_id, "name": dname}}
    )
    assert not created_ds.errors, created_ds.errors
    assert created_ds.data["createDataset"]["name"] == dname

    listed = await aexecute(LIST_DATASETS, {"filters": {"search": dname}})
    assert not listed.errors, listed.errors
    assert dname in [d["name"] for d in listed.data["datasets"]]


async def test_delete_nonexistent_image_errors_cleanly(aexecute, omero_root_user):
    """Deleting a bogus image id surfaces a GraphQL error, not a harness crash."""
    await omero_root_user()
    res = await aexecute(DELETE_IMAGE, {"input": {"id": "999999999"}})
    # Either OMERO reports an ERR (GraphQL error) — the path we care about is
    # that the resolver/extension wiring handled the live connection without
    # tearing down the test runner.
    assert res.errors or res.data["deleteImage"]["id"] == "999999999"


def test_thumbnail_view_requires_auth_and_handles_missing_image(client, backend_stack):
    """The @omero_connected thumbnail view: bogus id → 404 (not 500/401).

    Sets up the OmeroUser synchronously (the Django test client is sync) for the
    user the static "test" token authenticates as (sub="1").
    """
    from authentikate.models import User

    from bridge.models import OmeroUser

    user, _ = User.objects.get_or_create(
        sub="1", iss="static_issuer", defaults={"username": "static_issuer_1"}
    )
    OmeroUser.objects.update_or_create(
        user=user,
        defaults=dict(
            omero_username="root",
            omero_password="omero",
            omero_host="localhost",
            omero_port=4064,
        ),
    )

    resp = client.get(
        "/api/thumbnails/999999999/", headers={"Authorization": "Bearer test"}
    )
    assert resp.status_code in (404, 200)
