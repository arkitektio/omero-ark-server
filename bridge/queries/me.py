from bridge import models, types
from koherent.types import Info


def me(info: Info) -> types.User:
    return info.context.request.user
    