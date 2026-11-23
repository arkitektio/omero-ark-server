import logging
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from contextvars import ContextVar

from asgiref.sync import sync_to_async
from kante.context import HttpContext, WsContext
from omero.gateway import BlitzGateway
from strawberry.extensions import SchemaExtension

from .models import OmeroUser

logger = logging.getLogger(__name__)

current_conn: ContextVar[BlitzGateway] = ContextVar("current_conn")


@contextmanager
def omerocon(user: OmeroUser) -> Iterator[BlitzGateway]:
    conn = BlitzGateway(
        user.omero_username,
        user.omero_password,
        host=user.omero_host,
        port=user.omero_port,
    )
    conn.connect()

    try:
        yield conn
    finally:
        conn.close()


@sync_to_async
def get_omero_user(context: HttpContext | WsContext) -> OmeroUser | None:
    if not context.request.user.is_authenticated:
        raise Exception("User is not authenticated")

    user = OmeroUser.objects.filter(user=context.request.user).first()
    return user


def get_conn() -> BlitzGateway:
    try:
        return current_conn.get()
    except LookupError:
        raise Exception("No OMERO connection found") from None


class OmeroExtension(SchemaExtension):
    async def on_operation(self) -> AsyncIterator[None]:
        try:
            user = await get_omero_user(self.execution_context.context)

            conn = BlitzGateway(
                user.omero_username,
                user.omero_password,
                host=user.omero_host,
                port=user.omero_port,
            )
            conn.connect()
            token = current_conn.set(conn)

            try:
                yield
            finally:
                current_conn.reset(token)
                conn.close()
        except Exception:
            # No OMERO connection for this operation; resolvers needing one fail with "No OMERO connection found".
            logger.warning(
                "Could not open an OMERO connection for this operation", exc_info=True
            )
            yield
