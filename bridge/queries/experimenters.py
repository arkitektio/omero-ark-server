"""Experimenter (user) and group queries."""

from typing import List

import strawberry
from strawberry_django import pagination

from bridge import filters, types
from bridge.conn import get_conn
from bridge.gateway import get_object, list_objects


def _matches(exp, needle: str) -> bool:
    haystack = " ".join(filter(None, [exp.getName(), exp.getFirstName(), exp.getLastName(), exp.getEmail()])).lower()
    return needle in haystack


def experimenters(filters: filters.ExperimenterFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> List[types.Experimenter]:
    """List OMERO experimenters. ``search`` matches login, first/last name and email."""
    objects = list_objects("Experimenter", ids=filters.ids if filters else None)
    if filters and filters.search:
        needle = filters.search.lower()
        objects = [e for e in objects if _matches(e, needle)]
    if pagination:
        start = pagination.offset or 0
        end = None if pagination.limit is None else start + pagination.limit
        objects = objects[start:end]
    return [types.Experimenter(value=e) for e in objects]


def experimenter(id: strawberry.ID) -> types.Experimenter:
    """Fetch one experimenter by id."""
    return types.Experimenter(value=get_object("Experimenter", id))


def current_experimenter() -> types.Experimenter:
    """The OMERO experimenter the current session is logged in as."""
    return types.Experimenter(value=get_conn().getUser())


def groups(filters: filters.ExperimenterGroupFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> List[types.ExperimenterGroup]:
    """List OMERO groups."""
    return [
        types.ExperimenterGroup(value=g)
        for g in list_objects(
            "ExperimenterGroup",
            ids=filters.ids if filters else None,
            search=filters.search if filters else None,
            offset=pagination.offset if pagination else None,
            limit=pagination.limit if pagination else None,
        )
    ]


def group(id: strawberry.ID) -> types.ExperimenterGroup:
    """Fetch one group by id."""
    return types.ExperimenterGroup(value=get_object("ExperimenterGroup", id))
