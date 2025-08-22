from kante.types import Info
from typing import AsyncGenerator
import strawberry
from strawberry_django.optimizer import DjangoOptimizerExtension
from bridge.channel import image_channel
from strawberry import ID
from strawberry.permission import BasePermission
from typing import Any, Type
from bridge import types, models
from bridge import mutations
from bridge import queries
from strawberry.field_extensions import InputMutationExtension
import strawberry_django
from authentikate.strawberry import AuthExtension, AuthSubscribeExtension
from authentikate.strawberry.extension import AuthentikateExtension
from bridge.conn import OmeroExtension
import kante
from strawberry import ID as StrawberryID
from typing import Annotated 
from koherent.strawberry.extension import KoherentExtension


ID = Annotated[StrawberryID, strawberry.argument(description="The unique identifier of an object")]


def field(permission_classes=None, **kwargs):
    "A wrapper for field that adds default permission classes and extensions."
    if permission_classes:
        pass
    else:
        permission_classes = []
    return kante.field(extensions=[AuthExtension()], **kwargs)


def mutation(roles: list[str] | None = None, **kwargs) -> strawberry.mutation:
    """A wrapper for mutation that adds default permission classes and extensions."""

    return kante.mutation(extensions=[AuthExtension(any_role_of=roles or ["admin", "bot"])], **kwargs)


def subscription(**kwargs) -> strawberry.subscription:
    """A wrapper for subscription that adds default permission classes and extensions."""
    return kante.subscription(extensions=[AuthSubscribeExtension()], **kwargs)


@strawberry.type
class Query:
    omero_users: list[types.OmeroUser] = strawberry.django.field(extensions=[])
    projects: list[types.Project] = strawberry.field(resolver=queries.projects)
    project = strawberry.field(resolver=queries.project)
    image = strawberry.field(resolver=queries.image)
    dataset = strawberry.field(resolver=queries.dataset)
    datasets = strawberry.field(resolver=queries.datasets)
    images = strawberry.field(resolver=queries.images)
    
    me: types.User = strawberry.field(resolver=queries.me)
    


@strawberry.type
class Mutation:
    ensure_omero_user: types.OmeroUser = strawberry_django.mutation(
        resolver=mutations.ensure_omero_user,
    )
    delete_me: types.User = strawberry_django.mutation(
        resolver=mutations.delete_me,
    )
    create_project: types.Project = strawberry_django.mutation(
        resolver=mutations.create_project,
    )
    create_dataset: types.Dataset = strawberry_django.mutation(
        resolver=mutations.create_dataset,
    )
    delete_image = strawberry.field(resolver=mutations.delete_image)
    
    


schema = kante.Schema(
    query=Query,
    mutation=Mutation,
    extensions=[
        AuthentikateExtension,
        DjangoOptimizerExtension,
        KoherentExtension,
        OmeroExtension
    ],
)
