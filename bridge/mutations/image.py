from kante.types import Info

from bridge import inputs, types
from bridge.gateway import delete_objects, update_object


def delete_image(info: Info, input: inputs.DeleteImageInput) -> types.DeleteResult:
    """Delete an image (and its pixels, ROIs and non-shared annotations)."""
    delete_objects("Image", [input.id], delete_children=True)
    return types.DeleteResult(id=input.id)


def update_image(info: Info, input: inputs.UpdateObjectInput) -> types.Image:
    """Rename and/or re-describe an image."""
    return types.Image(value=update_object("Image", input.id, name=input.name, description=input.description))
