from ezomero import post_project
from kante.types import Info

from bridge import inputs, types
from bridge.conn import get_conn
from bridge.gateway import delete_objects, get_object, update_object


def create_project(info: Info, input: inputs.CreateProjectInput) -> types.Project:
    """Create a project."""
    conn = get_conn()
    id = post_project(conn, project_name=input.name, description=input.description)
    return types.Project(value=get_object("Project", id, conn=conn))


def update_project(info: Info, input: inputs.UpdateObjectInput) -> types.Project:
    """Rename and/or re-describe a project."""
    return types.Project(value=update_object("Project", input.id, name=input.name, description=input.description))


def delete_project(info: Info, input: inputs.DeleteContainerInput) -> types.DeleteResult:
    """Delete a project. Its datasets (and their images) are deleted too only when deleteChildren is true."""
    delete_objects("Project", [input.id], delete_children=input.delete_children)
    return types.DeleteResult(id=input.id)
