from kante.types import Info
from bridge import types, models, inputs
from django.conf import settings
from omero.gateway import BlitzGateway
import socket
import strawberry


def isOpen(ip, port, timeout=1.0):
    """Return True if TCP connect to (ip, port) succeeds within timeout seconds."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # set a timeout so connect() won't block indefinitely
    s.settimeout(timeout)
    try:
        s.connect((ip, int(port)))
        try:
            s.shutdown(socket.SHUT_RDWR)
        except OSError:
            # shutdown may fail if the socket is already closed on remote
            pass
        return True
    except (socket.timeout, socket.error, OSError):
        return False
    finally:
        try:
            s.close()
        except OSError:
            pass


def ensure_omero_user(info: Info, input: inputs.OmeroUserInput) -> types.OmeroUser:
    # lets try if we can reach the omero-server

    if not isOpen(input.host, input.port):
        raise Exception("Could nost connect to OMERO server. On the server, make sure that the OMERO server is running and that the port is open.")

    try:
        conn = BlitzGateway(input.username, input.password, host=input.host, port=input.port)
        conn.connect()

        # We are now logged in, conn.getUser() returns a User object
        for i in conn.listProjects():
            print(i.name)

        x, _ = models.OmeroUser.objects.update_or_create(
            user=info.context.request.user,
            defaults=dict(
                omero_password=input.password,
                omero_username=input.username,
                omero_host=input.host,
                omero_port=input.port,
            ),
        )

        return x
    except Exception as e:
        raise Exception("Could not connect to OMERO server with the user Credentials. The host and port are correct, but the username and password are probably not.")


@strawberry.input
class DeleteMeInput:
    reason: str | None = None


def delete_me(info: Info, input: DeleteMeInput) -> types.User:
    """Delete the current user"""

    x = models.OmeroUser.objects.get(
        user=info.context.request.user,
    )

    x.delete()

    return info.context.request.user
