from bridge.conn import get_conn
from bridge import types, filters
from strawberry_django import pagination
import strawberry


def images(filters: filters.ImageFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> types.Image:
    x = get_conn().listImages()

    if filters:
        if filters.ids:
            x = [y for y in x if str(y.getId()) in filters.ids]
            print(x.getID() for x in x)
        if filters.search:
            x = [y for y in x if filters.search in y.getName()]

    if pagination:
        x = x[pagination.offset : pagination.offset + pagination.limit]

        
    return [types.Image(value=y) for y in x]


def image(id: strawberry.ID) -> types.Image:
    x = get_conn().getObject("Image", id)
    return types.Image(value=x)