"""Screen and plate mutations. Plates are created by import, not over the API, so only update/delete exist for them."""

from ezomero import post_screen
from kante.types import Info

from bridge import inputs, types
from bridge.conn import get_conn
from bridge.gateway import delete_objects, get_object, update_object


def create_screen(info: Info, input: inputs.CreateScreenInput) -> types.Screen:
    """Create a screen."""
    conn = get_conn()
    id = post_screen(conn, screen_name=input.name, description=input.description)
    return types.Screen(value=get_object("Screen", id, conn=conn))


def update_screen(info: Info, input: inputs.UpdateObjectInput) -> types.Screen:
    """Rename and/or re-describe a screen."""
    return types.Screen(value=update_object("Screen", input.id, name=input.name, description=input.description))


def delete_screen(info: Info, input: inputs.DeleteContainerInput) -> types.DeleteResult:
    """Delete a screen. Its plates are deleted too only when deleteChildren is true."""
    delete_objects("Screen", [input.id], delete_children=input.delete_children)
    return types.DeleteResult(id=input.id)


def update_plate(info: Info, input: inputs.UpdateObjectInput) -> types.Plate:
    """Rename and/or re-describe a plate."""
    return types.Plate(value=update_object("Plate", input.id, name=input.name, description=input.description))


def delete_plate(info: Info, input: inputs.DeleteContainerInput) -> types.DeleteResult:
    """Delete a plate. Its wells' images are deleted too only when deleteChildren is true."""
    delete_objects("Plate", [input.id], delete_children=input.delete_children)
    return types.DeleteResult(id=input.id)
