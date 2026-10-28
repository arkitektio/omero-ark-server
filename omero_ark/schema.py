"""The omero-ark GraphQL schema.

Queries and mutations are thin: every resolver lives in ``bridge.queries`` /
``bridge.mutations`` and talks to OMERO through the per-request BlitzGateway
that ``bridge.conn.OmeroExtension`` opens for the authenticated user.
"""

from typing import Annotated
from omero_ark.logs import QuietErrorsSchema

import kante
import strawberry
import strawberry_django
from authentikate.strawberry import AuthExtension, AuthSubscribeExtension
from authentikate.strawberry.extension import AuthentikateExtension
from koherent.strawberry.extension import KoherentExtension
from strawberry import ID as StrawberryID
from strawberry_django.optimizer import DjangoOptimizerExtension

from authentikate.catch_alls import declare_catch_alls
from bridge import mutations, queries, types
from bridge.conn import OmeroExtension
from omero_ark.contract import EDITOR, contract

ID = Annotated[StrawberryID, strawberry.argument(description="The unique identifier of an object")]


def field(scope: str = "omero_ark_read", **kwargs):
    "A field an app needs ``scope`` for (``omero_ark_read``, unless it says otherwise)."
    return strawberry.field(extensions=[AuthExtension(scopes=[scope])], **kwargs)


def mutation(scope: str = "omero_ark_write", roles: list[str] | None = None, **kwargs):
    """A write: an app needs ``scope`` for it, a member one of ``roles`` (``omero_ark_editor`` unless it
    says otherwise; ``omero_ark_admin`` holds every role)."""
    return strawberry.field(extensions=[AuthExtension(scopes=[scope], any_role_of=roles or [EDITOR])], **kwargs)


def account_mutation(**kwargs) -> strawberry.mutation:
    """A write to the caller's own OMERO account: it stores (or drops) the credentials every read and
    write goes through, so it is a write like any other (``omero_ark_write``, ``omero_ark_editor``)."""
    return strawberry_django.mutation(extensions=[AuthExtension(scopes=["omero_ark_write"], any_role_of=[EDITOR])], **kwargs)


def subscription(scope: str = "omero_ark_read", **kwargs) -> strawberry.subscription:
    """A subscription an app needs ``scope`` for (``omero_ark_read``, unless it says otherwise)."""
    return kante.subscription(extensions=[AuthSubscribeExtension(scopes=[scope])], **kwargs)


@strawberry.type
class Query:
    # --- account layer ------------------------------------------------------
    omero_users: list[types.OmeroUser] = strawberry_django.field(extensions=[AuthExtension(scopes=["omero_ark_read"])])
    me: types.User = field(resolver=queries.me)

    # --- Project / Dataset / Image -------------------------------------------
    projects: list[types.Project] = field(resolver=queries.projects)
    project: types.Project = field(resolver=queries.project)
    datasets: list[types.Dataset] = field(resolver=queries.datasets)
    dataset: types.Dataset = field(resolver=queries.dataset)
    images: list[types.Image] = field(resolver=queries.images)
    image: types.Image = field(resolver=queries.image)

    # --- Screen / Plate / Well -----------------------------------------------
    screens: list[types.Screen] = field(resolver=queries.screens)
    screen: types.Screen = field(resolver=queries.screen)
    plates: list[types.Plate] = field(resolver=queries.plates)
    plate: types.Plate = field(resolver=queries.plate)
    wells: list[types.Well] = field(resolver=queries.wells)
    well: types.Well = field(resolver=queries.well)
    plate_acquisition: types.PlateAcquisition = field(resolver=queries.plate_acquisition)

    # --- annotations & ROIs --------------------------------------------------
    tags: list[types.TagAnnotation] = field(resolver=queries.tags)
    tag: types.TagAnnotation = field(resolver=queries.tag)
    annotation: types.Annotation = field(resolver=queries.annotation)
    rois: list[types.Roi] = field(resolver=queries.rois)
    roi: types.Roi = field(resolver=queries.roi)

    # --- experimenters & groups ----------------------------------------------
    experimenters: list[types.Experimenter] = field(resolver=queries.experimenters)
    experimenter: types.Experimenter = field(resolver=queries.experimenter)
    current_experimenter: types.Experimenter = field(resolver=queries.current_experimenter)
    groups: list[types.ExperimenterGroup] = field(resolver=queries.groups)
    group: types.ExperimenterGroup = field(resolver=queries.group)


@strawberry.type
class Mutation:
    # --- account layer ------------------------------------------------------
    ensure_omero_user: types.OmeroUser = account_mutation(resolver=mutations.ensure_omero_user)
    delete_me: types.User = account_mutation(resolver=mutations.delete_me)

    # --- Project / Dataset / Image -------------------------------------------
    create_project: types.Project = mutation(resolver=mutations.create_project)
    update_project: types.Project = mutation(resolver=mutations.update_project)
    delete_project: types.DeleteResult = mutation(resolver=mutations.delete_project)
    create_dataset: types.Dataset = mutation(resolver=mutations.create_dataset)
    update_dataset: types.Dataset = mutation(resolver=mutations.update_dataset)
    delete_dataset: types.DeleteResult = mutation(resolver=mutations.delete_dataset)
    update_image: types.Image = mutation(resolver=mutations.update_image)
    delete_image: types.DeleteResult = mutation(resolver=mutations.delete_image)

    # --- Screen / Plate ------------------------------------------------------
    create_screen: types.Screen = mutation(resolver=mutations.create_screen)
    update_screen: types.Screen = mutation(resolver=mutations.update_screen)
    delete_screen: types.DeleteResult = mutation(resolver=mutations.delete_screen)
    update_plate: types.Plate = mutation(resolver=mutations.update_plate)
    delete_plate: types.DeleteResult = mutation(resolver=mutations.delete_plate)

    # --- links ---------------------------------------------------------------
    link_datasets: types.Project = mutation(resolver=mutations.link_datasets)
    unlink_datasets: types.Project = mutation(resolver=mutations.unlink_datasets)
    link_images: types.Dataset = mutation(resolver=mutations.link_images)
    unlink_images: types.Dataset = mutation(resolver=mutations.unlink_images)
    link_plates: types.Screen = mutation(resolver=mutations.link_plates)
    unlink_plates: types.Screen = mutation(resolver=mutations.unlink_plates)

    # --- annotations ---------------------------------------------------------
    create_tag: types.TagAnnotation = mutation(resolver=mutations.create_tag)
    create_comment: types.CommentAnnotation = mutation(resolver=mutations.create_comment)
    create_map_annotation: types.MapAnnotation = mutation(resolver=mutations.create_map_annotation)
    link_annotation: types.Annotation = mutation(resolver=mutations.link_annotation)
    unlink_annotation: types.Annotation = mutation(resolver=mutations.unlink_annotation)
    delete_annotation: types.DeleteResult = mutation(resolver=mutations.delete_annotation)

    # --- ROIs ----------------------------------------------------------------
    create_roi: types.Roi = mutation(resolver=mutations.create_roi)
    delete_roi: types.DeleteResult = mutation(resolver=mutations.delete_roi)


class Schema(QuietErrorsSchema, kante.Schema):
    """kante.Schema, logging expected resolver errors as one line and bugs with a traceback (see logs.py)."""


schema = Schema(
    query=Query,
    mutation=Mutation,
    types=types.INTERFACE_IMPLEMENTATIONS,
    extensions=[
        AuthentikateExtension,
        DjangoOptimizerExtension,
        KoherentExtension,
        OmeroExtension,
    ],
)

# What stands for every scope and role here (`omero_ark_all`, `omero_ark_admin`). omero-ark has no
# hub structures, so no `annotate_schema`: the contract's catch-alls are declared directly.
declare_catch_alls(scope=contract.description.all_scope, role=contract.description.admin_role)
