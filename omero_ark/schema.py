from kante.types import Info
from typing import AsyncGenerator
import strawberry
from strawberry_django.optimizer import DjangoOptimizerExtension
from bridge.channel import image_listen
from strawberry import ID
from kante.directives import upper, replace, relation
from strawberry.permission import BasePermission
from typing import Any, Type
from bridge import types, models
from bridge import mutations
from bridge import queries
from strawberry.field_extensions import InputMutationExtension
import strawberry_django
from koherent.strawberry.extension import KoherentExtension
from bridge.conn import OmeroExtension
from authentikate.strawberry.permissions import HasScopes, IsAuthenticated, NeedsScopes




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
    
    


schema = strawberry.Schema(
    query=Query,
    mutation=Mutation,
    directives=[upper, replace, relation],
    extensions=[
        DjangoOptimizerExtension,
        KoherentExtension,
        OmeroExtension
    ],
)
