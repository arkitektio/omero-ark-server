from typing import List

import strawberry
from strawberry_django import pagination

from bridge import filters, types
from bridge.gateway import get_object, list_objects


def rois(filters: filters.RoiFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> List[types.Roi]:
    """List regions of interest, usually of one image."""
    opts = {"load_shapes": True}
    if filters and filters.image is not None:
        opts["image"] = int(filters.image)
    return [
        types.Roi(value=r)
        for r in list_objects(
            "Roi",
            ids=filters.ids if filters else None,
            opts=opts,
            offset=pagination.offset if pagination else None,
            limit=pagination.limit if pagination else None,
        )
    ]


def roi(id: strawberry.ID) -> types.Roi:
    """Fetch one ROI by id, with its shapes."""
    return types.Roi(value=get_object("Roi", id))
