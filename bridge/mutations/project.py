from bridge.conn import get_conn
from bridge import types, filters, inputs
from strawberry_django import pagination
import strawberry
from kante.types import Info
from ezomero import post_project

def create_project(info: Info, input: inputs.CreateProjectInput) -> types.Project:
    con = get_conn()
    id = post_project(con, project_name=input.name, description=input.description)
    project = get_conn().getObject("Project", id)
    return types.Project(value=project)