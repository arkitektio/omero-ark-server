"""Small helpers on top of the per-request BlitzGateway.

Everything here is resolver-agnostic plumbing: object lookup with clear
errors, list/filter/paginate over ``conn.getObjects``, rtype unwrapping, and
colour conversions. Resolvers in ``bridge/queries`` and ``bridge/mutations``
build on these so the GraphQL layer stays thin and uniform.
"""

from __future__ import annotations

from typing import Any, Iterable, Sequence

import omero
from omero.gateway import BlitzGateway, BlitzObjectWrapper
from omero.rtypes import unwrap as _rtype_unwrap

from bridge.conn import get_conn


class OmeroNotFound(Exception):
    """Raised when an OMERO object the client asked for does not exist (or is not visible)."""


def unwrap(value: Any) -> Any:
    """Turn an OMERO rtype (rstring, rlong, ...) into a plain Python value; pass through everything else."""
    if value is None:
        return None
    return _rtype_unwrap(value)


def get_object(kind: str, id: str | int, conn: BlitzGateway | None = None) -> BlitzObjectWrapper:
    """Fetch a single wrapped OMERO object or raise a clear error.

    ``kind`` is an OMERO type name as understood by ``BlitzGateway.getObject``
    (``"Image"``, ``"Dataset"``, ``"TagAnnotation"``, ...).
    """
    conn = conn or get_conn()
    try:
        numeric = int(id)
    except (TypeError, ValueError):
        raise OmeroNotFound(f"{kind} id must be an integer, got {id!r}")
    obj = conn.getObject(kind, numeric)
    if obj is None:
        raise OmeroNotFound(f"{kind} {numeric} not found (or not visible to the current OMERO user)")
    return obj


def list_objects(
    kind: str,
    *,
    ids: Sequence[str | int] | None = None,
    search: str | None = None,
    owner: str | int | None = None,
    opts: dict[str, Any] | None = None,
    offset: int | None = None,
    limit: int | None = None,
    conn: BlitzGateway | None = None,
) -> list[BlitzObjectWrapper]:
    """List OMERO objects of ``kind`` with the filters the GraphQL layer offers.

    ``ids``/``owner``/``opts`` are pushed down into the HQL query that
    ``getObjects`` builds; ``search`` (case-insensitive substring match on the
    name) and the offset/limit slice are applied in Python because OMERO's
    ``getObjects`` has no name filter. Ordering is by id so pagination is stable.
    """
    conn = conn or get_conn()
    query_opts: dict[str, Any] = dict(opts or {})
    query_opts.setdefault("order_by", "obj.id")
    if owner is not None:
        query_opts["owner"] = int(owner)

    numeric_ids = [int(i) for i in ids] if ids is not None else None
    if numeric_ids is not None and not numeric_ids:
        return []

    objects: Iterable[BlitzObjectWrapper] = conn.getObjects(kind, ids=numeric_ids, opts=query_opts)

    if search:
        needle = search.lower()
        objects = [o for o in objects if needle in (o.getName() or "").lower()]
    else:
        objects = list(objects)

    if offset or limit is not None:
        start = offset or 0
        end = None if limit is None else start + limit
        objects = objects[start:end]

    return objects


def delete_objects(kind: str, ids: Sequence[str | int], *, delete_children: bool = False, delete_annotations: bool = False, conn: BlitzGateway | None = None) -> None:
    """Delete objects through OMERO's delete queue and wait for the result.

    Raises ``omero.CmdError`` (surfacing as a GraphQL error) if the server
    rejects the delete, e.g. because of permissions.
    """
    conn = conn or get_conn()
    handle = conn.deleteObjects(
        kind,
        [int(i) for i in ids],
        deleteAnns=delete_annotations,
        deleteChildren=delete_children,
        wait=True,
    )
    try:
        handle.close()
    except Exception:  # the handle may already be closed by waitOnCmd
        pass


def rgba_int_to_hex(value: int | None) -> str | None:
    """Convert OMERO's packed signed-int RGBA colour to ``#rrggbbaa``."""
    if value is None:
        return None
    packed = int(value) & 0xFFFFFFFF
    r = (packed >> 24) & 0xFF
    g = (packed >> 16) & 0xFF
    b = (packed >> 8) & 0xFF
    a = packed & 0xFF
    return f"#{r:02x}{g:02x}{b:02x}{a:02x}"


def hex_to_rgba_tuple(value: str | None) -> tuple[int, int, int, int] | None:
    """Parse ``#rrggbb`` or ``#rrggbbaa`` into the ``(r, g, b, a)`` tuple ezomero expects."""
    if value is None:
        return None
    text = value.strip().lstrip("#")
    if len(text) == 6:
        text += "ff"
    if len(text) != 8:
        raise ValueError(f"Colour must be #rrggbb or #rrggbbaa, got {value!r}")
    r, g, b, a = (int(text[i : i + 2], 16) for i in range(0, 8, 2))
    return (r, g, b, a)


def parse_points(points: str | None) -> list[tuple[float, float]]:
    """Parse OMERO's polygon/polyline ``points`` string (``"x,y x,y ..."``) into coordinate pairs.

    OMERO has historically stored points in a few dialects (plain
    ``"x,y x,y"``, or the legacy ``"points[x,y ...] points1[...]"`` form);
    the first pair list is what matters.
    """
    if not points:
        return []
    text = points.strip()
    if "[" in text:
        text = text[text.index("[") + 1 : text.index("]")]
    out: list[tuple[float, float]] = []
    for pair in text.replace(";", " ").split():
        if "," not in pair:
            continue
        x, y = pair.split(",", 1)
        out.append((float(x), float(y)))
    return out


def find_link_ids(link_type: str, parent_id: str | int, child_id: str | int, conn: BlitzGateway | None = None) -> list[int]:
    """Return the ids of ``link_type`` rows (e.g. ``DatasetImageLink``) joining a parent and a child."""
    conn = conn or get_conn()
    params = omero.sys.ParametersI()
    params.addLong("pid", int(parent_id))
    params.addLong("cid", int(child_id))
    query = f"select l from {link_type} l where l.parent.id = :pid and l.child.id = :cid"
    links = conn.getQueryService().findAllByQuery(query, params, conn.SERVICE_OPTS)
    return [unwrap(link.id) for link in links]


def update_object(kind: str, id: str | int, *, name: str | None = None, description: str | None = None, conn: BlitzGateway | None = None) -> BlitzObjectWrapper:
    """Set name and/or description on an object and save it. ``None`` leaves a field untouched."""
    conn = conn or get_conn()
    obj = get_object(kind, id, conn=conn)
    if name is not None:
        obj.setName(name)
    if description is not None:
        obj.setDescription(description)
    if name is not None or description is not None:
        obj.save()
    return get_object(kind, id, conn=conn)
