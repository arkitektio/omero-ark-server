from bridge.conn import get_conn
from bridge import types, filters, inputs
from strawberry_django import pagination
import strawberry
from kante.types import Info
from ezomero import post_project
import omero



def delete_image(info: Info, input: inputs.DeleteImageInput) -> types.DeleteResult:
    conn = get_conn()

    target = omero.cmd.Delete2(targetObjects={'Image': [int(input.id)]})
    # Execute the delete command
    response = conn.c.submit(target)
    if isinstance(response, omero.cmd.ERR):
        raise RuntimeError(f"Failed to delete image {int(input.id)}: {response}")
    else:
        print(f"Image {int(input.id)} deleted successfully.")
        return types.DeleteResult(id=input.id)