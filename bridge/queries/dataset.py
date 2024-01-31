from bridge.conn import get_conn
from bridge import types, filters
from strawberry_django import pagination
import strawberry

def datasets(filters: filters.DatasetFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> types.Dataset:
    
    x = get_conn().listDatasets()

    if filters:
        if filters.ids:
            x = [y for y in x if str(y.getId()) in filters.ids]
            print(x.getID() for x in x)
        if filters.search:
            x = [y for y in x if filters.search in y.getName()]

    if pagination:
        x = x[pagination.offset : pagination.offset + pagination.limit]


    return [types.Dataset(value=y) for y in x]


def dataset(id: strawberry.ID) -> types.Dataset:
    x = get_conn().getObject("Dataset", id)
    return types.Dataset(value=x)