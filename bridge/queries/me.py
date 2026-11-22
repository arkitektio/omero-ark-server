from kante.types import Info

from bridge import types


def me(info: Info) -> types.User:
    return info.context.request.user
