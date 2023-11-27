from bridge.conn import get_conn
from bridge import types, filters
from strawberry_django import pagination
import strawberry

def projects(filters: filters.ProjectFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> types.Project:
    x = get_conn().listProjects()
    return [types.Project(value=y) for y in x]


def project(id: strawberry.ID) -> types.Project:
    x = get_conn().getObject("Project", id)
    return types.Project(value=x)