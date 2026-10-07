"""What this image answers a hub's installer: ``arkitekt-service <verb>`` (see ``arkitekt_service.contract``).

The installer knows the hub; how this release spells its config is written here, with the
settings it is read by. A key renamed in ``configuration.py`` is renamed in :func:`render` in
the same commit, and no installer has to learn of it.

Where the OMERO server is (``omero_host``, ``omero_port``) is not one of a hub's facts: it
is somebody's own server. It keeps its defaults here and is set per deployment, as an
override.
"""

from __future__ import annotations

from arkitekt_service.contract import JSON, Contract, Description, Facts, Needs, Offers, Start, blocks

from omero_ark.configuration import Settings


def render(facts: Facts) -> dict[str, JSON]:
    """This release's config for the hub ``facts`` describes."""
    return blocks.server(facts)


contract = Contract(
    description=Description(
        name="omero_ark",
        identifier="live.arkitekt.omero_ark",
        summary="A bridge to an OMERO server: its projects, datasets and images.",
        needs=Needs(),
        offers=Offers(),
    ),
    settings=Settings,
    render=render,
    # How this service is started: there is no script beside it. `arkitekt-service serve`
    # (and `debug`) become these, so they get the container's signals themselves.
    serve=Start(("daphne", "-b", "0.0.0.0", "-p", "80", "--websocket_timeout", "-1", "omero_ark.asgi:application")),
    debug=Start(("python", "manage.py", "runserver", "0.0.0.0:80")),
)
