from koherent.types import Info
from bridge import types, models, inputs



def ensure_omero_user(info: Info, input: inputs.OmerUserInput) -> types.OmeroUser:

    x, _= models.OmeroUser.objects.update_or_create(
        user=info.context.request.user,
        defaults=dict(
            omero_password=input.password,
            omero_username=input.username,
        ),

    )

    return x