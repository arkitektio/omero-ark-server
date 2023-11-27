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

class IsAuthenticated(BasePermission):
    message = "User is not authenticated"

    # This method can also be async!
    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        if info.context.request.user is not None:
            return info.context.request.user.is_authenticated
        return False


class HasScopes(BasePermission):
    message = "User is not authenticated"
    checked_scopes = []

    # This method can also be async!
    def has_permission(self, source: Any, info: Info, **kwargs) -> bool:
        print(info.context.request.scopes)
        return info.context.request.has_scopes(self.checked_scopes)


def NeedsScopes(scopes: str | list[str]) -> Type[HasScopes]:
    if isinstance(scopes, str):
        scopes = [scopes]
    return type(
        f"NeedsScopes{'_'.join(scopes)}",
        (HasScopes,),
        dict(
            message=f"App does not have the required scopes: {','.join(scopes)}",
            checked_scopes=scopes,
        ),
    )


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
