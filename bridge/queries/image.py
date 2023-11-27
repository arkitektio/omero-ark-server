from bridge.conn import get_conn
from bridge import types, filters
from strawberry_django import pagination
import strawberry


def images(filters: filters.ImageFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> types.Image:
    x = get_conn().listImages()
    return [types.Project(value=y) for y in x]


def image(id: strawberry.ID) -> types.Image:
    x = get_conn().getObject("Image", id)
    return types.Image(value=x)