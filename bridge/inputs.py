"""Mutation inputs.

The account inputs (``OmeroUserInput``) and the two original create inputs are
pydantic-backed; everything newer is a plain strawberry input, which is all a
GraphQL input needs.
"""

import strawberry
from django.conf import settings
from pydantic import BaseModel
from strawberry import field
from strawberry.experimental import pydantic

from bridge.enums import OmeroObjectType


class OmeroUserInputModel(BaseModel):
    username: str
    password: str
    host: str | None = settings.OMERO_HOST
    port: int | None = settings.OMERO_PORT


@pydantic.input(OmeroUserInputModel)
class OmeroUserInput:
    username: str
    password: str
    host: str | None = field(default=settings.OMERO_HOST, description="The host for the omero user (relative to SERVER not client)")
    port: int | None = field(default=settings.OMERO_PORT, description="The port for the omero user (relative to SERVER not client)")


class CreateProjectInputModel(BaseModel):
    name: str
    description: str | None = None


@pydantic.input(CreateProjectInputModel)
class CreateProjectInput:
    name: str
    description: str | None = None


class CreateDatasetInputModel(BaseModel):
    project_id: str | None = None
    name: str
    description: str | None = None


@pydantic.input(CreateDatasetInputModel)
class CreateDatasetInput:
    project_id: strawberry.ID | None = field(default=None, description="The project to link the new dataset into. Omit for an orphaned dataset.")
    name: str
    description: str | None = None


class DeleteImageInputModel(BaseModel):
    id: str


@pydantic.input(DeleteImageInputModel)
class DeleteImageInput:
    id: strawberry.ID


# --- generic update / delete ------------------------------------------------
@strawberry.input(description="Rename and/or re-describe an object. Fields left null are not touched.")
class UpdateObjectInput:
    id: strawberry.ID
    name: str | None = None
    description: str | None = None


@strawberry.input(description="Delete a container. Children are only deleted when deleteChildren is true; otherwise they are unlinked and become orphans.")
class DeleteContainerInput:
    id: strawberry.ID
    delete_children: bool = False


@strawberry.input
class DeleteObjectInput:
    id: strawberry.ID


@strawberry.input
class CreateScreenInput:
    name: str
    description: str | None = None


# --- links --------------------------------------------------------------------
@strawberry.input
class ProjectDatasetsInput:
    project_id: strawberry.ID
    dataset_ids: list[strawberry.ID]


@strawberry.input
class DatasetImagesInput:
    dataset_id: strawberry.ID
    image_ids: list[strawberry.ID]


@strawberry.input
class ScreenPlatesInput:
    screen_id: strawberry.ID
    plate_ids: list[strawberry.ID]


# --- annotations --------------------------------------------------------------
@strawberry.input(description="The object an annotation is linked to (or should be linked to).")
class AnnotationTargetInput:
    type: OmeroObjectType
    id: strawberry.ID


@strawberry.input
class CreateTagInput:
    text: str
    description: str | None = None
    target: AnnotationTargetInput | None = field(default=None, description="Link the new tag to this object right away.")


@strawberry.input
class CreateCommentInput:
    target: AnnotationTargetInput
    text: str


@strawberry.input
class KeyValueInput:
    key: str
    value: str


@strawberry.input
class CreateMapAnnotationInput:
    target: AnnotationTargetInput
    values: list[KeyValueInput]
    ns: str | None = field(default=None, description="Namespace. Defaults to OMERO's client map-annotation namespace so the pairs show up as editable key/value pairs in OMERO.web.")


@strawberry.input
class AnnotationLinkInput:
    target: AnnotationTargetInput
    annotation_id: strawberry.ID


# --- ROIs ---------------------------------------------------------------------
@strawberry.input
class VertexInput:
    x: float
    y: float


@strawberry.input
class RectangleInput:
    x: float
    y: float
    width: float
    height: float


@strawberry.input
class EllipseInput:
    x: float = field(description="Centre x.")
    y: float = field(description="Centre y.")
    radius_x: float
    radius_y: float


@strawberry.input
class PointInput:
    x: float
    y: float


@strawberry.input
class LineInput:
    x1: float
    y1: float
    x2: float
    y2: float


@strawberry.input
class PolygonInput:
    points: list[VertexInput]


@strawberry.input
class PolylineInput:
    points: list[VertexInput]


@strawberry.input
class LabelInput:
    x: float
    y: float
    text: str
    font_size: float = 12.0


@strawberry.input(one_of=True, description="Exactly one geometry.")
class GeometryInput:
    rectangle: RectangleInput | None = strawberry.UNSET
    ellipse: EllipseInput | None = strawberry.UNSET
    point: PointInput | None = strawberry.UNSET
    line: LineInput | None = strawberry.UNSET
    polygon: PolygonInput | None = strawberry.UNSET
    polyline: PolylineInput | None = strawberry.UNSET
    label: LabelInput | None = strawberry.UNSET


@strawberry.input
class ShapeInput:
    geometry: GeometryInput
    z: int | None = field(default=None, description="Zero-based Z plane; null for all planes.")
    t: int | None = field(default=None, description="Zero-based timepoint; null for all timepoints.")
    c: int | None = field(default=None, description="Zero-based channel; null for all channels.")
    text: str | None = None
    stroke_color: str | None = field(default=None, description="#rrggbb or #rrggbbaa")
    fill_color: str | None = field(default=None, description="#rrggbb or #rrggbbaa")
    stroke_width: float | None = field(default=None, description="Stroke width in pixels.")


@strawberry.input
class CreateRoiInput:
    image_id: strawberry.ID
    shapes: list[ShapeInput]
    name: str | None = None
    description: str | None = None
