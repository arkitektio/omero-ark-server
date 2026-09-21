"""Link / unlink mutations for the container hierarchies.

OMERO containers are many-to-many: a dataset can sit in several projects, an
image in several datasets, a plate in several screens. Linking never moves or
copies data; unlinking never deletes it.
"""

from ezomero import link_datasets_to_project, link_images_to_dataset, link_plates_to_screen
from kante.types import Info

from bridge import inputs, types
from bridge.conn import get_conn
from bridge.gateway import delete_objects, find_link_ids, get_object


def _unlink(link_type: str, parent_id: str, child_ids: list[str], conn) -> None:
    link_ids = [lid for cid in child_ids for lid in find_link_ids(link_type, parent_id, cid, conn=conn)]
    if link_ids:
        delete_objects(link_type, link_ids, delete_children=True, conn=conn)


def link_datasets(info: Info, input: inputs.ProjectDatasetsInput) -> types.Project:
    """Link datasets into a project."""
    conn = get_conn()
    link_datasets_to_project(conn, [int(i) for i in input.dataset_ids], int(input.project_id))
    return types.Project(value=get_object("Project", input.project_id, conn=conn))


def unlink_datasets(info: Info, input: inputs.ProjectDatasetsInput) -> types.Project:
    """Remove datasets from a project without deleting them."""
    conn = get_conn()
    _unlink("ProjectDatasetLink", input.project_id, input.dataset_ids, conn)
    return types.Project(value=get_object("Project", input.project_id, conn=conn))


def link_images(info: Info, input: inputs.DatasetImagesInput) -> types.Dataset:
    """Link images into a dataset."""
    conn = get_conn()
    link_images_to_dataset(conn, [int(i) for i in input.image_ids], int(input.dataset_id))
    return types.Dataset(value=get_object("Dataset", input.dataset_id, conn=conn))


def unlink_images(info: Info, input: inputs.DatasetImagesInput) -> types.Dataset:
    """Remove images from a dataset without deleting them."""
    conn = get_conn()
    _unlink("DatasetImageLink", input.dataset_id, input.image_ids, conn)
    return types.Dataset(value=get_object("Dataset", input.dataset_id, conn=conn))


def link_plates(info: Info, input: inputs.ScreenPlatesInput) -> types.Screen:
    """Link plates into a screen."""
    conn = get_conn()
    link_plates_to_screen(conn, [int(i) for i in input.plate_ids], int(input.screen_id))
    return types.Screen(value=get_object("Screen", input.screen_id, conn=conn))


def unlink_plates(info: Info, input: inputs.ScreenPlatesInput) -> types.Screen:
    """Remove plates from a screen without deleting them."""
    conn = get_conn()
    _unlink("ScreenPlateLink", input.screen_id, input.plate_ids, conn)
    return types.Screen(value=get_object("Screen", input.screen_id, conn=conn))
