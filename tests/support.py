"""The types the suite's fixtures hand to tests (their values are built in ``conftest.py``)."""

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, TypeAlias

from kante.context import HttpContext
from strawberry.types import ExecutionResult

from bridge.models import OmeroUser

#: ``seed``: the ids of what the module seeded into OMERO, by kind.
Seeded: TypeAlias = dict[str, int | None]

#: ``omero_root_user``: store root's OMERO credentials for the authed user.
OmeroRootUser: TypeAlias = Callable[[], Awaitable[OmeroUser]]


class AExecute(Protocol):
    """``aexecute``: run a GraphQL document against the schema, as the authed context by default."""

    def __call__(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
        context: HttpContext | None = None,
    ) -> Awaitable[ExecutionResult]: ...
