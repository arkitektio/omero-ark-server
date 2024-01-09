from koherent.types import Info
from bridge import types, models, inputs
from django.conf import settings
from omero.gateway import BlitzGateway

def ensure_omero_user(info: Info, input: inputs.OmerUserInput) -> types.OmeroUser:


    try:
        conn = BlitzGateway(input.username, input.password, host=settings.OMERO_HOST, port=settings.OMERO_PORT)
        conn.connect()

        
        # We are now logged in, conn.getUser() returns a User object
        for i in conn.listProjects():
            print(i.name)

        x, _= models.OmeroUser.objects.update_or_create(
        user=info.context.request.user,
        defaults=dict(
            omero_password=input.password,
            omero_username=input.username,
        ),

        )

        return x
    except Exception as e:
        raise e



def delete_me(info: Info) -> types.OmeroUser:
    """Delete the current user"""


    x = models.OmeroUser.objects.get(
    user=info.context.request.user,
    )

    x.delete()

    return info.context.request.user