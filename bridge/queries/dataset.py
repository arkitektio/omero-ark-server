import strawberry
from strawberry_django import pagination

from bridge import filters, types
from bridge.filters import order_by as hql_order_by
from bridge.gateway import get_object, list_objects


def datasets(
    filters: filters.DatasetFilter | None = None,
    pagination: pagination.OffsetPaginationInput | None = None,
    ordering: list[filters.ContainerOrder] | None = None,
) -> list[types.Dataset]:
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
            order_by=hql_order_by(ordering),
        )
    ]


def dataset(id: strawberry.ID) -> types.Dataset:
    """Fetch one dataset by id."""
    return types.Dataset(value=get_object("Dataset", id))
