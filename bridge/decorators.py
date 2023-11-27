from authentikate.utils import authenticate_header_or_none
from bridge import models
from omero.gateway import BlitzGateway
from .models import OmeroUser
from contextlib import contextmanager
from django.conf import settings
from contextvars import ContextVar
from strawberry.extensions import SchemaExtension
from asgiref.sync import sync_to_async
from .conn import current_conn

def authentikated(func):



    def wrapper(request, *args, **kwargs):


        x = authenticate_header_or_none(request.headers)
        print(x)

        if x is None:
            raise Exception("User is not authenticated")
        return func(request, *args,  **kwargs)
    
    
    return wrapper



def omero_connected(func):


    def wrapper(request, *args, **kwargs):


        x = authenticate_header_or_none(request.headers)
        print(x)

        if not x: raise Exception("User is not authenticated")
        user = models.OmeroUser.objects.filter(user=x.user).first()

        conn = BlitzGateway(user.omero_username, user.omero_password, host=settings.OMERO_HOST, port=settings.OMERO_PORT)
        conn.connect()
        token = current_conn.set(conn)

        try:
            return func(request, *args,  **kwargs)
        finally:
            current_conn.reset(token)
            conn.close()
    
    
    return wrapper