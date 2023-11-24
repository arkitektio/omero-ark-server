from omero.gateway import BlitzGateway
from .models import OmeroUser
from contextlib import contextmanager
from django.conf import settings
from contextvars import ContextVar
from strawberry.extensions import SchemaExtension
from asgiref.sync import sync_to_async

current_conn: ContextVar[any] = ContextVar("current_conn")

@contextmanager
def omerocon(user: OmeroUser):
    conn = BlitzGateway(user.omero_username, user.omero_password, host=settings.OMERO_HOST, port=settings.OMERO_PORT)
    conn.connect()

    try:
        yield conn
    finally:
        conn.close()

@sync_to_async
def get_omero_user(context):
    if not context.request.user.is_authenticated:
        raise Exception("User is not authenticated")

    user = OmeroUser.objects.filter(user=context.request.user).first()
    return user


def get_conn():
    try:
        return current_conn.get()
    except LookupError:
        raise Exception("No OMERO connection found")

class OmeroExtension(SchemaExtension):
    async def on_operation(self):
        print("Starting operation")
        try:
            user = await get_omero_user(self.execution_context.context)
            print(user)

            conn = BlitzGateway(user.omero_username, user.omero_password, host=settings.OMERO_HOST, port=settings.OMERO_PORT)
            conn.connect()
            token = current_conn.set(conn)

            try:
                yield
            finally:
                current_conn.reset(token)
                conn.close()
        except Exception as e:
            print(e)
            yield
