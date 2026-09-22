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

from bridge import mutations, queries, types
from bridge.conn import OmeroExtension

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
    # --- account layer ------------------------------------------------------
    omero_users: list[types.OmeroUser] = strawberry_django.field(extensions=[])
    me: types.User = strawberry.field(resolver=queries.me)

    # --- Project / Dataset / Image -------------------------------------------
    projects: list[types.Project] = strawberry.field(resolver=queries.projects)
    project: types.Project = strawberry.field(resolver=queries.project)
    datasets: list[types.Dataset] = strawberry.field(resolver=queries.datasets)
    dataset: types.Dataset = strawberry.field(resolver=queries.dataset)
    images: list[types.Image] = strawberry.field(resolver=queries.images)
    image: types.Image = strawberry.field(resolver=queries.image)

    # --- Screen / Plate / Well -----------------------------------------------
    screens: list[types.Screen] = strawberry.field(resolver=queries.screens)
    screen: types.Screen = strawberry.field(resolver=queries.screen)
    plates: list[types.Plate] = strawberry.field(resolver=queries.plates)
    plate: types.Plate = strawberry.field(resolver=queries.plate)
    wells: list[types.Well] = strawberry.field(resolver=queries.wells)
    well: types.Well = strawberry.field(resolver=queries.well)
    plate_acquisition: types.PlateAcquisition = strawberry.field(resolver=queries.plate_acquisition)

    # --- annotations & ROIs --------------------------------------------------
    tags: list[types.TagAnnotation] = strawberry.field(resolver=queries.tags)
    tag: types.TagAnnotation = strawberry.field(resolver=queries.tag)
    annotation: types.Annotation = strawberry.field(resolver=queries.annotation)
    rois: list[types.Roi] = strawberry.field(resolver=queries.rois)
    roi: types.Roi = strawberry.field(resolver=queries.roi)

    # --- experimenters & groups ----------------------------------------------
    experimenters: list[types.Experimenter] = strawberry.field(resolver=queries.experimenters)
    experimenter: types.Experimenter = strawberry.field(resolver=queries.experimenter)
    current_experimenter: types.Experimenter = strawberry.field(resolver=queries.current_experimenter)
    groups: list[types.ExperimenterGroup] = strawberry.field(resolver=queries.groups)
    group: types.ExperimenterGroup = strawberry.field(resolver=queries.group)


@strawberry.type
class Mutation:
    # --- account layer ------------------------------------------------------
    ensure_omero_user: types.OmeroUser = strawberry_django.mutation(resolver=mutations.ensure_omero_user)
    delete_me: types.User = strawberry_django.mutation(resolver=mutations.delete_me)

    # --- Project / Dataset / Image -------------------------------------------
    create_project: types.Project = strawberry.field(resolver=mutations.create_project)
    update_project: types.Project = strawberry.field(resolver=mutations.update_project)
    delete_project: types.DeleteResult = strawberry.field(resolver=mutations.delete_project)
    create_dataset: types.Dataset = strawberry.field(resolver=mutations.create_dataset)
    update_dataset: types.Dataset = strawberry.field(resolver=mutations.update_dataset)
    delete_dataset: types.DeleteResult = strawberry.field(resolver=mutations.delete_dataset)
    update_image: types.Image = strawberry.field(resolver=mutations.update_image)
    delete_image: types.DeleteResult = strawberry.field(resolver=mutations.delete_image)

    # --- Screen / Plate ------------------------------------------------------
    create_screen: types.Screen = strawberry.field(resolver=mutations.create_screen)
    update_screen: types.Screen = strawberry.field(resolver=mutations.update_screen)
    delete_screen: types.DeleteResult = strawberry.field(resolver=mutations.delete_screen)
    update_plate: types.Plate = strawberry.field(resolver=mutations.update_plate)
    delete_plate: types.DeleteResult = strawberry.field(resolver=mutations.delete_plate)

    # --- links ---------------------------------------------------------------
    link_datasets: types.Project = strawberry.field(resolver=mutations.link_datasets)
    unlink_datasets: types.Project = strawberry.field(resolver=mutations.unlink_datasets)
    link_images: types.Dataset = strawberry.field(resolver=mutations.link_images)
    unlink_images: types.Dataset = strawberry.field(resolver=mutations.unlink_images)
    link_plates: types.Screen = strawberry.field(resolver=mutations.link_plates)
    unlink_plates: types.Screen = strawberry.field(resolver=mutations.unlink_plates)

    # --- annotations ---------------------------------------------------------
    create_tag: types.TagAnnotation = strawberry.field(resolver=mutations.create_tag)
    create_comment: types.CommentAnnotation = strawberry.field(resolver=mutations.create_comment)
    create_map_annotation: types.MapAnnotation = strawberry.field(resolver=mutations.create_map_annotation)
    link_annotation: types.Annotation = strawberry.field(resolver=mutations.link_annotation)
    unlink_annotation: types.Annotation = strawberry.field(resolver=mutations.unlink_annotation)
    delete_annotation: types.DeleteResult = strawberry.field(resolver=mutations.delete_annotation)

    # --- ROIs ----------------------------------------------------------------
    create_roi: types.Roi = strawberry.field(resolver=mutations.create_roi)
    delete_roi: types.DeleteResult = strawberry.field(resolver=mutations.delete_roi)


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
