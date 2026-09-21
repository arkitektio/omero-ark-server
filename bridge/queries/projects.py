from typing import List

import strawberry
from strawberry_django import pagination

from bridge import filters, types
from bridge.gateway import get_object, list_objects


def projects(filters: filters.ProjectFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> List[types.Project]:
    """List the projects visible to the current OMERO user."""
    return [
        types.Project(value=p)
        for p in list_objects(
            "Project",
            ids=filters.ids if filters else None,
            search=filters.search if filters else None,
            owner=filters.owner if filters else None,
            offset=pagination.offset if pagination else None,
            limit=pagination.limit if pagination else None,
        )
    ]


def project(id: strawberry.ID) -> types.Project:
    """Fetch one project by id."""
    return types.Project(value=get_object("Project", id))
