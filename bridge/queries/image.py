from bridge.conn import get_conn
from bridge import types, filters
from strawberry_django import pagination
import strawberry
from typing import List
import omero
import omero.clients


def images(filters: filters.ImageFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> List[types.Image]:


    params = omero.sys.ParametersI()

    query = ("select i from Image i ")

    images = get_conn().getQueryService().findAllByQuery(query, params)
    
    images_info = []
    for dataset in images:
        dataset_info = {
            "ID": dataset.id.val,
            "Name": dataset.name.val,
        }
        images_info.append(dataset_info)

    print(images_info)

    if filters:
        if filters.ids:
            # Ids are strings
            images_info = [y for y in images_info if str(y.get("ID", -1)) in filters.ids]
        if filters.search:
            images_info = [y for y in images_info if y.get("Name", "").startswith(filters.search)]

    if pagination:
        images_info = images_info[pagination.offset : pagination.offset + pagination.limit]


    images = [get_conn().getObject("Image", y["ID"]) for y in images_info]
    return  [types.Image(value=i) for i in images]


def image(id: strawberry.ID) -> types.Image:
    x = get_conn().getObject("Image", id)
    return types.Image(value=x)

