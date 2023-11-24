from bridge.conn import get_conn
from bridge import types


def projects():
    x = get_conn().listProjects()
    return [types.Project(value=y) for y in x]