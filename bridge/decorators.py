"""View decorators for the REST endpoints (thumbnails, downloads).

The GraphQL side gets its OMERO connection from ``bridge.conn.OmeroExtension``;
these sync Django views need the same thing from a bearer header, so
``omero_connected`` authenticates the header with authentikate, expands the
token to the Django user, and opens a BlitzGateway for the request.
"""

from asgiref.sync import async_to_sync
from authentikate.expand import expand_user_from_token
from authentikate.utils import authenticate_header_or_none
from django.http import HttpResponseForbidden
from omero.gateway import BlitzGateway

from bridge import models

from .conn import current_conn


def _user_from_request(request):
    token = async_to_sync(authenticate_header_or_none)(request.headers)
    if token is None:
        return None
    return expand_user_from_token(token)


def authentikated(func):
    """Reject the request unless a valid bearer token identifies a user."""

    def wrapper(request, *args, **kwargs):
        if _user_from_request(request) is None:
            return HttpResponseForbidden("User is not authenticated")
        return func(request, *args, **kwargs)

    return wrapper


def omero_connected(func):
    """Open a BlitzGateway for the calling user's stored OMERO credentials for the duration of the view."""

    def wrapper(request, *args, **kwargs):
        user = _user_from_request(request)
        if user is None:
            return HttpResponseForbidden("User is not authenticated")
        omero_user = models.OmeroUser.objects.filter(user=user).first()
        if omero_user is None:
            return HttpResponseForbidden("User has no OMERO credentials; call ensureOmeroUser first")

        conn = BlitzGateway(omero_user.omero_username, omero_user.omero_password, host=omero_user.omero_host, port=omero_user.omero_port)
        conn.connect()
        token = current_conn.set(conn)
        try:
            return func(request, *args, **kwargs)
        finally:
            current_conn.reset(token)
            conn.close()

    return wrapper
