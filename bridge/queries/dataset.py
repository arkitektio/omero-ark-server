from bridge.conn import get_conn
from bridge import types, filters
from strawberry_django import pagination
import strawberry
import omero 
import omero.clients
from typing import List

def datasets(filters: filters.DatasetFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> List[types.Dataset]:
    
    params = omero.sys.ParametersI()

    query = ("select d from Dataset d ")

    datasets = get_conn().getQueryService().findAllByQuery(query, params)
    
    datasets_info = []
    for dataset in datasets:
        dataset_info = {
            "ID": dataset.id.val,
            "Name": dataset.name.val,
        }
        datasets_info.append(dataset_info)


    if filters:
        if filters.ids:
            # Ids are strings
            datasets_info = [y for y in datasets_info if str(y.get("ID", -1)) in filters.ids]
        if filters.search:
            datasets_info = [y for y in datasets_info if y.get("Name", "").startswith(filters.search)]

    if pagination:
        datasets_info = datasets_info[pagination.offset : pagination.offset + pagination.limit]


    datasets = [get_conn().getObject("Dataset", y["ID"]) for y in datasets_info]
    return  [types.Dataset(value=dataset) for dataset in datasets]


def dataset(id: strawberry.ID) -> types.Dataset:
    x = get_conn().getObject("Dataset", id)
    return types.Dataset(value=x)