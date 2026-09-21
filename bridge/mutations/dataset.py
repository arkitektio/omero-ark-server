from ezomero import post_dataset
from kante.types import Info

from bridge import inputs, types
from bridge.conn import get_conn
from bridge.gateway import delete_objects, get_object, update_object


def create_dataset(info: Info, input: inputs.CreateDatasetInput) -> types.Dataset:
    """Create a dataset, optionally linked into a project."""
    conn = get_conn()
    id = post_dataset(
        conn,
        dataset_name=input.name,
        project_id=int(input.project_id) if input.project_id is not None else None,
        description=input.description,
    )
    return types.Dataset(value=get_object("Dataset", id, conn=conn))


def update_dataset(info: Info, input: inputs.UpdateObjectInput) -> types.Dataset:
    """Rename and/or re-describe a dataset."""
    return types.Dataset(value=update_object("Dataset", input.id, name=input.name, description=input.description))


def delete_dataset(info: Info, input: inputs.DeleteContainerInput) -> types.DeleteResult:
    """Delete a dataset. Its images are deleted too only when deleteChildren is true; otherwise they become orphans."""
    delete_objects("Dataset", [input.id], delete_children=input.delete_children)
    return types.DeleteResult(id=input.id)
