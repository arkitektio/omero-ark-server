from typing import List

import strawberry
from strawberry_django import pagination

from bridge import filters, types
from bridge.gateway import get_object, list_objects


def datasets(filters: filters.DatasetFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> List[types.Dataset]:
    """List datasets, optionally restricted to one project or to orphans."""
    opts = {}
    if filters and filters.project is not None:
        opts["project"] = int(filters.project)
    if filters and filters.orphaned:
        opts["orphaned"] = True
    return [
        types.Dataset(value=d)
        for d in list_objects(
            "Dataset",
            ids=filters.ids if filters else None,
            search=filters.search if filters else None,
            owner=filters.owner if filters else None,
            opts=opts,
            offset=pagination.offset if pagination else None,
            limit=pagination.limit if pagination else None,
        )
    ]


def dataset(id: strawberry.ID) -> types.Dataset:
    """Fetch one dataset by id."""
    return types.Dataset(value=get_object("Dataset", id))
