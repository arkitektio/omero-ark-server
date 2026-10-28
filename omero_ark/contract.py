"""What this image answers a hub's installer: ``arkitekt-service <verb>`` (see ``arkitekt_service.contract``).

The installer knows the hub; how this release spells its config is written here, with the
settings it is read by. A key renamed in ``configuration.py`` is renamed in :func:`render` in
the same commit, and no installer has to learn of it.

Where the OMERO server is (``omero_host``, ``omero_port``) is not one of a hub's facts: it
is somebody's own server. It keeps its defaults here and is set per deployment, as an
override.
"""

from __future__ import annotations

from arkitekt_service.contract import JSON, Contract, Description, Facts, Job, Needs, Offers, Role, Scope, Start, blocks

from omero_ark.configuration import Settings

#: What an app may do here on a user's behalf: defined at the coordination server when the hub
#: enrols. Every root field of the schema asks for one of them (`AuthExtension(scopes=...)`).
SCOPES = [
    Scope(key="omero_ark_read", description="Browse your OMERO projects, datasets, screens, plates, images and annotations."),
    Scope(key="omero_ark_write", description="Create, change, link and delete OMERO projects, datasets, screens, plates, images, annotations and ROIs."),
    Scope(key="omero_ark_all", description="Do everything in OMERO on your behalf.", is_all_scope=True),
]

#: What a member of an organization may do here.
ROLES = [
    Role(key="omero_ark_admin", description="Full control of the OMERO bridge in this organization.", is_admin_role=True),
    Role(key="omero_ark_editor", description="Change OMERO data.", is_default_role=True),
]

#: The role every write asks for.
EDITOR = "omero_ark_editor"
ADMIN = "omero_ark_admin"


def render(facts: Facts) -> dict[str, JSON]:
    """This release's config for the hub ``facts`` describes."""
    return blocks.server(facts)


contract = Contract(
    description=Description(
        name="omero_ark",
        identifier="live.arkitekt.omero_ark",
        summary="A bridge to an OMERO server: its projects, datasets and images.",
        needs=Needs(scopes=SCOPES, roles=ROLES),
        offers=Offers(),
    ),
    settings=Settings,
    render=render,
    # How this service is started: there is no script beside it. `arkitekt-service serve`
    # (and `debug`) become these, so they get the container's signals themselves.
    serve=Start(("daphne", "-b", "0.0.0.0", "-p", "80", "--websocket_timeout", "-1", "omero_ark.asgi:application")),
    debug=Start(("python", "manage.py", "runserver", "0.0.0.0:80")),
    jobs={
        "ensureadmin": Job(("ensureadmin",), "Create the operator account the config names"),
    },
    setup=("ensureadmin",),
)
