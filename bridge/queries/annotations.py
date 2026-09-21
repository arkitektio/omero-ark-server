"""Annotation queries. Tags get their own list because they are the one kind that is browsed on its own."""

from typing import List

import strawberry
from strawberry_django import pagination

from bridge import filters, types
from bridge.gateway import OmeroNotFound, get_object, list_objects


def tags(filters: filters.TagFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> List[types.TagAnnotation]:
    """List tag annotations. ``search`` matches the tag text."""
    conn_objects = list_objects(
        "TagAnnotation",
        ids=filters.ids if filters else None,
        owner=filters.owner if filters else None,
    )
    if filters and filters.search:
        needle = filters.search.lower()
        conn_objects = [t for t in conn_objects if needle in (t.getValue() or "").lower()]
    if pagination:
        start = pagination.offset or 0
        end = None if pagination.limit is None else start + pagination.limit
        conn_objects = conn_objects[start:end]
    return [types.TagAnnotation(value=t) for t in conn_objects]


def tag(id: strawberry.ID) -> types.TagAnnotation:
    """Fetch one tag by id."""
    return types.TagAnnotation(value=get_object("TagAnnotation", id))


def annotation(id: strawberry.ID) -> types.Annotation:
    """Fetch any annotation by id; the concrete type is resolved from its OMERO kind."""
    wrapper = get_object("Annotation", id)
    wrapped = types.wrap_annotation(wrapper)
    if wrapped is None:
        raise OmeroNotFound(f"Annotation {id} is of a kind omero-ark does not expose ({type(wrapper).__name__})")
    return wrapped
