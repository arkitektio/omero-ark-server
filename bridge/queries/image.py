from typing import List

import strawberry
from strawberry_django import pagination

from bridge import filters, types
from bridge.gateway import get_object, list_objects


def images(filters: filters.ImageFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> List[types.Image]:
    """List images, optionally restricted to one dataset or to orphans."""
    opts = {}
    if filters and filters.dataset is not None:
        opts["dataset"] = int(filters.dataset)
    if filters and filters.orphaned:
        opts["orphaned"] = True
    return [
        types.Image(value=i)
        for i in list_objects(
            "Image",
            ids=filters.ids if filters else None,
            search=filters.search if filters else None,
            owner=filters.owner if filters else None,
            opts=opts,
            offset=pagination.offset if pagination else None,
            limit=pagination.limit if pagination else None,
        )
    ]


def image(id: strawberry.ID) -> types.Image:
    """Fetch one image by id."""
    return types.Image(value=get_object("Image", id))
