from bridge.conn import get_conn
from bridge import types, filters
from strawberry_django import pagination
import strawberry

def datasets(filters: filters.DatasetFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> types.Dataset:
    x = get_conn().listDatasets()
    return [types.Project(value=y) for y in x]


def dataset(id: strawberry.ID) -> types.Dataset:
    x = get_conn().getObject("Dataset", id)
    return types.Project(value=x)