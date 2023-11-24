from bridge.conn import get_conn
from bridge import types
import strawberry

def image(id: strawberry.ID) -> types.Image:
    x = get_conn().getImage(id)
    return types.Image(value=x)