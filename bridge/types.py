"""GraphQL object types wrapping OMERO gateway objects.

Every OMERO-backed type carries the ``BlitzObjectWrapper`` (or raw
``omero.model`` object for shapes) in a private ``value`` field and resolves
its GraphQL fields lazily from it. Nothing is copied eagerly, so a query that
asks for ``{ id name }`` costs a single wrapper attribute read per field.

The hierarchy mirrors OMERO's own model and terminology:

* ``OmeroObject`` — the interface every container/annotation/ROI implements
  (id, name, description, owner, group, dates, permissions, annotations).
* Project → Dataset → Image (→ Channel, Pixels, Fileset) and the HCS branch
  Screen → Plate → Well → WellSample → Image, plus PlateAcquisition.
* ``Annotation`` — interface over Tag/Comment/Map/File/Long/Double/Boolean/
  Timestamp/Term annotations.
* ``Roi`` with a ``Shape`` interface over Rectangle/Ellipse/Point/Line/
  Polygon/Polyline/Label/Mask.
* ``Experimenter`` / ``ExperimenterGroup`` for the user model.
"""

from __future__ import annotations

import datetime
from typing import Optional

import strawberry
import strawberry_django
from django.contrib.auth import get_user_model
from strawberry import auto
from strawberry.types import Info

import omero.gateway as og
import omero.model
import omero.sys

from bridge import models
from bridge.conn import get_conn
from bridge.gateway import parse_points, rgba_int_to_hex, unwrap


# ---------------------------------------------------------------------------
# Django-backed types (the omero-ark account layer)
# ---------------------------------------------------------------------------
@strawberry.type
class DeleteResult:
    """The id of an object that was just deleted."""

    id: strawberry.ID


@strawberry_django.type(get_user_model())
class User:
    id: auto
    sub: str
    username: str
    email: str
    password: str

    @strawberry_django.field
    def omero_user(self) -> Optional["OmeroUser"]:
        return models.OmeroUser.objects.filter(user=self).first()


@strawberry_django.type(models.OmeroUser)
class OmeroUser:
    id: auto
    omero_password: str
    omero_username: str
    omero_host: str
    omero_port: int
    user: User


# ---------------------------------------------------------------------------
# Value types
# ---------------------------------------------------------------------------
@strawberry.type(description="A physical length as OMERO stores it: a value plus its unit.")
class Length:
    value: float
    unit: str = strawberry.field(description="The OMERO UnitsLength name, e.g. MICROMETER")
    symbol: str = strawberry.field(description="The unit symbol, e.g. µm")

    @classmethod
    def from_omero(cls, length: object | None) -> Optional["Length"]:
        if length is None:
            return None
        return cls(value=float(length.getValue()), unit=str(length.getUnit()), symbol=length.getSymbol())


@strawberry.type(description="What the current OMERO user may do with an object.")
class Permissions:
    value: strawberry.Private[og.BlitzObjectWrapper]

    @strawberry.field
    def can_edit(self) -> bool:
        return bool(self.value.canEdit())

    @strawberry.field
    def can_annotate(self) -> bool:
        return bool(self.value.canAnnotate())

    @strawberry.field
    def can_delete(self) -> bool:
        return bool(self.value.canDelete())

    @strawberry.field
    def can_link(self) -> bool:
        return bool(self.value.canLink())

    @strawberry.field
    def can_chgrp(self) -> bool:
        return bool(self.value.canChgrp())

    @strawberry.field
    def can_chown(self) -> bool:
        return bool(self.value.canChown())

    @strawberry.field(description="True if the current OMERO user owns the object.")
    def is_owned(self) -> bool:
        return bool(self.value.isOwned())


@strawberry.type(description="A key/value pair of a map annotation.")
class KeyValue:
    key: str
    value: str


# ---------------------------------------------------------------------------
# Experimenters & groups
# ---------------------------------------------------------------------------
@strawberry.type(description="An OMERO user account (OMERO calls these experimenters).")
class Experimenter:
    value: strawberry.Private[og.ExperimenterWrapper]
    _full: strawberry.Private[Optional[og.ExperimenterWrapper]] = None

    def _loaded(self) -> og.ExperimenterWrapper:
        """The experimenter OMERO attaches to an object's details is a shallow stub (login name only); reload it once for anything else."""
        if self._full is None:
            self._full = get_conn().getObject("Experimenter", int(self.value.getId())) or self.value
        return self._full

    @strawberry.field
    def id(self) -> strawberry.ID:
        return strawberry.ID(str(self.value.getId()))

    @strawberry.field(description="The OMERO login name (omeName).")
    def ome_name(self) -> str:
        return self.value.getName() or self._loaded().getName() or ""

    @strawberry.field
    def first_name(self) -> Optional[str]:
        return self._loaded().getFirstName()

    @strawberry.field
    def last_name(self) -> Optional[str]:
        return self._loaded().getLastName()

    @strawberry.field
    def full_name(self) -> str:
        exp = self._loaded()
        return exp.getFullName() or exp.getName() or ""

    @strawberry.field
    def email(self) -> Optional[str]:
        return self._loaded().getEmail()

    @strawberry.field
    def institution(self) -> Optional[str]:
        return self._loaded().getInstitution()

    @strawberry.field(description="True if the experimenter is a member of the system group.")
    def is_admin(self) -> bool:
        return any(int(unwrap(g.id)) == 0 for g in self._contained_groups())

    @strawberry.field
    def is_active(self) -> bool:
        return any(int(unwrap(g.id)) == 1 for g in self._contained_groups())

    def _contained_groups(self) -> list:
        return list(get_conn().getAdminService().containedGroups(int(self.value.getId())))

    @strawberry.field(description="The groups this experimenter is a member of.")
    def groups(self) -> list["ExperimenterGroup"]:
        conn = get_conn()
        return [ExperimenterGroup(value=og.ExperimenterGroupWrapper(conn, g)) for g in self._contained_groups()]


@strawberry.type(description="An OMERO group. Data is owned by a user within a group; permissions are set per group.")
class ExperimenterGroup:
    value: strawberry.Private[og.ExperimenterGroupWrapper]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return strawberry.ID(str(self.value.getId()))

    @strawberry.field
    def name(self) -> str:
        return self.value.getName() or ""

    @strawberry.field
    def description(self) -> Optional[str]:
        return self.value.getDescription()

    @strawberry.field(description="The members of this group.")
    def members(self) -> list[Experimenter]:
        conn = get_conn()
        experimenters = conn.getAdminService().containedExperimenters(int(self.value.getId()))
        return [Experimenter(value=og.ExperimenterWrapper(conn, e)) for e in experimenters]


# ---------------------------------------------------------------------------
# The shared OMERO object interface
# ---------------------------------------------------------------------------
@strawberry.interface(description="Fields every OMERO model object exposes: identity, ownership, dates, permissions and annotations.")
class OmeroObject:
    value: strawberry.Private[og.BlitzObjectWrapper]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return strawberry.ID(str(self.value.getId()))

    @strawberry.field
    def name(self) -> str:
        return self.value.getName() or ""

    @strawberry.field
    def description(self) -> str:
        return self.value.getDescription() or ""

    @strawberry.field(description="When the object was created in OMERO.")
    def creation_date(self) -> Optional[datetime.datetime]:
        try:
            return self.value.getDate()
        except Exception:
            return None

    @strawberry.field(description="The experimenter that owns this object.")
    def owner(self) -> Experimenter:
        return Experimenter(value=self.value.getDetails().getOwner())

    @strawberry.field(description="The group this object lives in.")
    def group(self) -> ExperimenterGroup:
        return ExperimenterGroup(value=self.value.getDetails().getGroup())

    @strawberry.field
    def permissions(self) -> Permissions:
        return Permissions(value=self.value)

    @strawberry.field(description="All annotations linked to this object (tags, comments, key/value maps, files, ...).")
    def annotations(self, ns: Optional[str] = None) -> list["Annotation"]:
        return [wrap_annotation(a) for a in self.value.listAnnotations(ns=ns) if wrap_annotation(a) is not None]

    @strawberry.field(description="The text values of the tag annotations linked to this object.")
    def tags(self) -> list[str]:
        return [a.getValue() for a in self.value.listAnnotations() if isinstance(a, og.TagAnnotationWrapper)]


def _unique(wrappers):
    """De-duplicate wrappers by id, keeping order. OMERO allows several links between the same pair, which would otherwise show a parent twice."""
    seen: set[int] = set()
    out = []
    for w in wrappers:
        if w.getId() not in seen:
            seen.add(w.getId())
            out.append(w)
    return out


# ---------------------------------------------------------------------------
# Project / Dataset / Image
# ---------------------------------------------------------------------------
@strawberry.type(description="An OMERO original file: one of the files an image was imported from, or a file annotation's payload.")
class OriginalFile:
    value: strawberry.Private[og.OriginalFileWrapper]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return strawberry.ID(str(self.value.getId()))

    @strawberry.field
    def name(self) -> str:
        return self.value.getName() or ""

    @strawberry.field
    def path(self) -> Optional[str]:
        return self.value.getPath()

    @strawberry.field(description="File size in bytes.")
    def size(self) -> Optional[int]:
        return self.value.getSize()

    @strawberry.field
    def mimetype(self) -> Optional[str]:
        return self.value.getMimetype()


@strawberry.type(description="The set of files a group of images was imported from together.")
class Fileset:
    value: strawberry.Private[og.FilesetWrapper]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return strawberry.ID(str(self.value.getId()))

    @strawberry.field
    def files(self) -> list[OriginalFile]:
        return [OriginalFile(value=f) for f in self.value.listFiles()]

    @strawberry.field(description="The images that were imported from this fileset.")
    def images(self) -> list["Image"]:
        return [Image(value=i) for i in self.value.copyImages()]


@strawberry.type(description="A channel of an image with its rendering settings.")
class Channel:
    value: strawberry.Private[og.ChannelWrapper]
    index: int

    @strawberry.field
    def id(self) -> strawberry.ID:
        return strawberry.ID(str(self.value.getId()))

    @strawberry.field(description="The display label: the channel name, or its wavelength / index if unnamed.")
    def label(self) -> str:
        return self.value.getLabel() or ""

    @strawberry.field
    def name(self) -> Optional[str]:
        return self.value.getName()

    @strawberry.field(description="The rendering colour as #rrggbb.")
    def color(self) -> str:
        return "#" + self.value.getColor().getHtml()

    @strawberry.field
    def emission_wave(self) -> Optional[Length]:
        return Length.from_omero(self.value.getEmissionWave(units=True))

    @strawberry.field
    def excitation_wave(self) -> Optional[Length]:
        return Length.from_omero(self.value.getExcitationWave(units=True))

    @strawberry.field(description="Lower end of the rendering window.")
    def window_start(self) -> Optional[float]:
        return self.value.getWindowStart()

    @strawberry.field(description="Upper end of the rendering window.")
    def window_end(self) -> Optional[float]:
        return self.value.getWindowEnd()

    @strawberry.field(description="Minimum pixel value of the channel.")
    def window_min(self) -> Optional[float]:
        return self.value.getWindowMin()

    @strawberry.field(description="Maximum pixel value of the channel.")
    def window_max(self) -> Optional[float]:
        return self.value.getWindowMax()

    @strawberry.field(description="Whether the channel is switched on in the rendering settings.")
    def is_active(self) -> bool:
        return bool(self.value.isActive())

    @strawberry.field(description="The lookup table applied to the channel, if any.")
    def lut(self) -> Optional[str]:
        return self.value.getLut() or None


@strawberry.type(description="An image in OMERO. The pixel data itself is served over the thumbnail/download REST endpoints.")
class Image(OmeroObject):
    value: strawberry.Private[og.ImageWrapper]

    @strawberry.field
    def acquisition_date(self) -> Optional[datetime.datetime]:
        return self.value.getAcquisitionDate()

    @strawberry.field(description="The name of the image's original file, when known.")
    def original_file(self) -> Optional[str]:
        files = list(self.value.getImportedImageFiles())
        return files[0].getName() if files else None

    @strawberry.field
    def size_x(self) -> int:
        return int(self.value.getSizeX())

    @strawberry.field
    def size_y(self) -> int:
        return int(self.value.getSizeY())

    @strawberry.field
    def size_z(self) -> int:
        return int(self.value.getSizeZ())

    @strawberry.field
    def size_c(self) -> int:
        return int(self.value.getSizeC())

    @strawberry.field
    def size_t(self) -> int:
        return int(self.value.getSizeT())

    @strawberry.field(description="The pixel data type, e.g. uint8, uint16, float.")
    def pixels_type(self) -> Optional[str]:
        return self.value.getPixelsType()

    @strawberry.field
    def physical_size_x(self) -> Optional[Length]:
        return Length.from_omero(self.value.getPixelSizeX(units=True))

    @strawberry.field
    def physical_size_y(self) -> Optional[Length]:
        return Length.from_omero(self.value.getPixelSizeY(units=True))

    @strawberry.field
    def physical_size_z(self) -> Optional[Length]:
        return Length.from_omero(self.value.getPixelSizeZ(units=True))

    @strawberry.field(description="The default Z plane shown by the rendering settings.")
    def default_z(self) -> int:
        return int(self.value.getDefaultZ())

    @strawberry.field(description="The default timepoint shown by the rendering settings.")
    def default_t(self) -> int:
        return int(self.value.getDefaultT())

    @strawberry.field
    def channels(self) -> list[Channel]:
        return [Channel(value=c, index=i) for i, c in enumerate(self.value.getChannels())]

    @strawberry.field(description="The datasets this image is linked into (an image can be in several).")
    def datasets(self) -> list["Dataset"]:
        return [Dataset(value=d) for d in _unique(self.value.listParents())]

    @strawberry.field(description="The fileset this image was imported with, if any.")
    def fileset(self) -> Optional[Fileset]:
        fs = self.value.getFileset()
        return Fileset(value=fs) if fs is not None else None

    @strawberry.field
    def roi_count(self) -> int:
        return int(self.value.getROICount())

    @strawberry.field
    def rois(self) -> list["Roi"]:
        conn = get_conn()
        return [Roi(value=r) for r in conn.getObjects("Roi", opts={"image": int(self.value.getId()), "load_shapes": True, "order_by": "obj.id"})]

    @strawberry.field(description="The well this image belongs to, when it is part of a plate.")
    def well(self) -> Optional["Well"]:
        conn = get_conn()
        params = omero.sys.ParametersI()
        params.addLong("iid", int(self.value.getId()))
        query = "select ws.well from WellSample ws where ws.image.id = :iid"
        wells = conn.getQueryService().findAllByQuery(query, params, conn.SERVICE_OPTS)
        return Well(value=og.WellWrapper(conn, wells[0])) if wells else None


@strawberry.type(description="A dataset: an unordered collection of images.")
class Dataset(OmeroObject):
    value: strawberry.Private[og.DatasetWrapper]

    @strawberry.field
    def images(self) -> list[Image]:
        return [Image(value=i) for i in self.value.listChildren()]

    @strawberry.field
    def image_count(self) -> int:
        return int(self.value.countChildren())

    @strawberry.field(description="The projects this dataset is linked into.")
    def projects(self) -> list["Project"]:
        return [Project(value=p) for p in _unique(self.value.listParents())]


@strawberry.type(description="A project: a collection of datasets.")
class Project(OmeroObject):
    value: strawberry.Private[og.ProjectWrapper]

    @strawberry.field
    def datasets(self) -> list[Dataset]:
        return [Dataset(value=d) for d in self.value.listChildren()]

    @strawberry.field
    def dataset_count(self) -> int:
        return int(self.value.countChildren())


# ---------------------------------------------------------------------------
# Screen / Plate / Well (high-content screening)
# ---------------------------------------------------------------------------
@strawberry.type(description="A run of a plate through the microscope. Multi-run plates have one image per well per acquisition.")
class PlateAcquisition(OmeroObject):
    value: strawberry.Private[og.PlateAcquisitionWrapper]

    @strawberry.field
    def start_time(self) -> Optional[datetime.datetime]:
        return self.value.getStartTime()

    @strawberry.field
    def end_time(self) -> Optional[datetime.datetime]:
        return self.value.getEndTime()

    @strawberry.field
    def maximum_field_count(self) -> Optional[int]:
        return unwrap(self.value._obj.maximumFieldCount)


@strawberry.type(description="One field of view in a well: the link between a well and an image.")
class WellSample:
    value: strawberry.Private[og.WellSampleWrapper]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return strawberry.ID(str(self.value.getId()))

    @strawberry.field
    def image(self) -> Optional[Image]:
        img = self.value.getImage()
        return Image(value=img) if img is not None else None

    @strawberry.field
    def plate_acquisition(self) -> Optional[PlateAcquisition]:
        pa = self.value.getPlateAcquisition()
        return PlateAcquisition(value=pa) if pa is not None else None

    @strawberry.field(description="Stage position of the field within the well.")
    def position_x(self) -> Optional[Length]:
        return Length.from_omero(self.value._obj.posX)

    @strawberry.field
    def position_y(self) -> Optional[Length]:
        return Length.from_omero(self.value._obj.posY)


@strawberry.type(description="A well of a plate, addressed by row/column.")
class Well(OmeroObject):
    value: strawberry.Private[og.WellWrapper]

    @strawberry.field(description="Zero-based row index.")
    def row(self) -> int:
        return int(unwrap(self.value._obj.row))

    @strawberry.field(description="Zero-based column index.")
    def column(self) -> int:
        return int(unwrap(self.value._obj.column))

    @strawberry.field(description="The human label, e.g. A1.")
    def position(self) -> str:
        return self.value.getWellPos()

    @strawberry.field(description="The well colour as #rrggbbaa, when one was set at import.")
    def color(self) -> Optional[str]:
        obj = self.value._obj
        rgba = [unwrap(getattr(obj, k)) for k in ("red", "green", "blue", "alpha")]
        if any(v is None for v in rgba):
            return None
        r, g, b, a = (int(v) & 0xFF for v in rgba)
        return f"#{r:02x}{g:02x}{b:02x}{a:02x}"

    @strawberry.field
    def samples(self) -> list[WellSample]:
        return [WellSample(value=ws) for ws in self.value.listChildren()]

    @strawberry.field(description="The images acquired in this well, one per field/acquisition.")
    def images(self) -> list[Image]:
        return [Image(value=ws.getImage()) for ws in self.value.listChildren() if ws.getImage() is not None]

    @strawberry.field
    def plate(self) -> "Plate":
        return Plate(value=self.value.getParent())


@strawberry.type(description="A multi-well plate.")
class Plate(OmeroObject):
    value: strawberry.Private[og.PlateWrapper]

    @strawberry.field(description="Declared row count, falling back to the highest occupied row when the plate does not declare one.")
    def rows(self) -> int:
        declared = unwrap(self.value._obj.rows)
        return int(declared) if declared else int(self.value.getGridSize()["rows"])

    @strawberry.field(description="Declared column count, falling back to the highest occupied column when the plate does not declare one.")
    def columns(self) -> int:
        declared = unwrap(self.value._obj.columns)
        return int(declared) if declared else int(self.value.getGridSize()["columns"])

    @strawberry.field
    def row_labels(self) -> list[str]:
        return [str(x) for x in self.value.getRowLabels()]

    @strawberry.field
    def column_labels(self) -> list[str]:
        return [str(x) for x in self.value.getColumnLabels()]

    @strawberry.field
    def wells(self) -> list[Well]:
        return [Well(value=w) for w in self.value.listChildren()]

    @strawberry.field
    def well_count(self) -> int:
        return int(self.value.countChildren())

    @strawberry.field
    def plate_acquisitions(self) -> list[PlateAcquisition]:
        return [PlateAcquisition(value=pa) for pa in self.value.listPlateAcquisitions()]

    @strawberry.field(description="The screens this plate is linked into.")
    def screens(self) -> list["Screen"]:
        return [Screen(value=s) for s in _unique(self.value.listParents())]


@strawberry.type(description="A screen: a collection of plates.")
class Screen(OmeroObject):
    value: strawberry.Private[og.ScreenWrapper]

    @strawberry.field
    def plates(self) -> list[Plate]:
        return [Plate(value=p) for p in self.value.listChildren()]

    @strawberry.field
    def plate_count(self) -> int:
        return int(self.value.countChildren())


# ---------------------------------------------------------------------------
# Annotations
# ---------------------------------------------------------------------------
@strawberry.interface(description="Metadata attached to an OMERO object. Concrete kinds carry their payload in kind-specific fields.")
class Annotation:
    value: strawberry.Private[og.AnnotationWrapper]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return strawberry.ID(str(self.value.getId()))

    @strawberry.field(description="The namespace the annotation was written under, if any.")
    def ns(self) -> Optional[str]:
        return self.value.getNs()

    @strawberry.field
    def description(self) -> Optional[str]:
        return self.value.getDescription()

    @strawberry.field
    def creation_date(self) -> Optional[datetime.datetime]:
        try:
            return self.value.getDate()
        except Exception:
            return None

    @strawberry.field
    def owner(self) -> Experimenter:
        return Experimenter(value=self.value.getDetails().getOwner())

    @strawberry.field
    def group(self) -> ExperimenterGroup:
        return ExperimenterGroup(value=self.value.getDetails().getGroup())

    @strawberry.field
    def permissions(self) -> Permissions:
        return Permissions(value=self.value)


@strawberry.type(description="A tag. Tags are shared, reusable labels linked to many objects.")
class TagAnnotation(Annotation):
    value: strawberry.Private[og.TagAnnotationWrapper]

    @strawberry.field
    def text(self) -> str:
        return self.value.getValue() or ""


@strawberry.type(description="A free-text comment.")
class CommentAnnotation(Annotation):
    value: strawberry.Private[og.CommentAnnotationWrapper]

    @strawberry.field
    def text(self) -> str:
        return self.value.getValue() or ""


@strawberry.type(description="An ordered list of key/value pairs.")
class MapAnnotation(Annotation):
    value: strawberry.Private[og.MapAnnotationWrapper]

    @strawberry.field
    def values(self) -> list[KeyValue]:
        return [KeyValue(key=k, value=v) for k, v in (self.value.getValue() or [])]


@strawberry.type(description="A file attached to an object.")
class FileAnnotation(Annotation):
    value: strawberry.Private[og.FileAnnotationWrapper]

    @strawberry.field
    def file_name(self) -> Optional[str]:
        return self.value.getFileName()

    @strawberry.field(description="File size in bytes.")
    def file_size(self) -> Optional[int]:
        return self.value.getFileSize()

    @strawberry.field
    def file(self) -> Optional[OriginalFile]:
        f = self.value.getFile()
        return OriginalFile(value=f) if f is not None else None

    @strawberry.field(description="True for the companion file OMERO writes with the original metadata at import.")
    def is_original_metadata(self) -> bool:
        return bool(self.value.isOriginalMetadata())


@strawberry.type
class LongAnnotation(Annotation):
    value: strawberry.Private[og.LongAnnotationWrapper]

    @strawberry.field
    def long_value(self) -> Optional[int]:
        return self.value.getValue()


@strawberry.type
class DoubleAnnotation(Annotation):
    value: strawberry.Private[og.DoubleAnnotationWrapper]

    @strawberry.field
    def double_value(self) -> Optional[float]:
        return self.value.getValue()


@strawberry.type
class BooleanAnnotation(Annotation):
    value: strawberry.Private[og.BooleanAnnotationWrapper]

    @strawberry.field
    def boolean_value(self) -> Optional[bool]:
        return self.value.getValue()


@strawberry.type
class TimestampAnnotation(Annotation):
    value: strawberry.Private[og.TimestampAnnotationWrapper]

    @strawberry.field
    def time_value(self) -> Optional[datetime.datetime]:
        return self.value.getValue()


@strawberry.type(description="A reference to an ontology term.")
class TermAnnotation(Annotation):
    value: strawberry.Private[og.TermAnnotationWrapper]

    @strawberry.field
    def term(self) -> Optional[str]:
        return self.value.getValue()


ANNOTATION_TYPES: dict[type, type] = {
    og.TagAnnotationWrapper: TagAnnotation,
    og.CommentAnnotationWrapper: CommentAnnotation,
    og.MapAnnotationWrapper: MapAnnotation,
    og.FileAnnotationWrapper: FileAnnotation,
    og.LongAnnotationWrapper: LongAnnotation,
    og.DoubleAnnotationWrapper: DoubleAnnotation,
    og.BooleanAnnotationWrapper: BooleanAnnotation,
    og.TimestampAnnotationWrapper: TimestampAnnotation,
    og.TermAnnotationWrapper: TermAnnotation,
}


def wrap_annotation(wrapper: og.AnnotationWrapper) -> Optional[Annotation]:
    """Pick the GraphQL type for an annotation wrapper; ``None`` for kinds we do not expose (e.g. XML)."""
    for cls, gql in ANNOTATION_TYPES.items():
        if isinstance(wrapper, cls):
            return gql(value=wrapper)
    return None


# ---------------------------------------------------------------------------
# ROIs and shapes
# ---------------------------------------------------------------------------
@strawberry.interface(description="A 2D shape of a region of interest, positioned on one Z/T/C plane (or all, when unset).")
class Shape:
    value: strawberry.Private[omero.model.Shape]

    @strawberry.field
    def id(self) -> strawberry.ID:
        return strawberry.ID(str(unwrap(self.value.id)))

    @strawberry.field(description="Zero-based Z plane, or null if the shape spans all planes.")
    def z(self) -> Optional[int]:
        return unwrap(self.value.theZ)

    @strawberry.field(description="Zero-based timepoint, or null if the shape spans all timepoints.")
    def t(self) -> Optional[int]:
        return unwrap(self.value.theT)

    @strawberry.field(description="Zero-based channel, or null if the shape applies to all channels.")
    def c(self) -> Optional[int]:
        return unwrap(self.value.theC)

    @strawberry.field(description="Stroke colour as #rrggbbaa.")
    def stroke_color(self) -> Optional[str]:
        return rgba_int_to_hex(unwrap(self.value.strokeColor))

    @strawberry.field(description="Fill colour as #rrggbbaa.")
    def fill_color(self) -> Optional[str]:
        return rgba_int_to_hex(unwrap(self.value.fillColor))

    @strawberry.field
    def stroke_width(self) -> Optional[Length]:
        return Length.from_omero(self.value.strokeWidth)

    @strawberry.field(description="The text label drawn with the shape.")
    def text(self) -> Optional[str]:
        return unwrap(self.value.textValue)


@strawberry.type
class Rectangle(Shape):
    @strawberry.field
    def x(self) -> float:
        return float(unwrap(self.value.x))

    @strawberry.field
    def y(self) -> float:
        return float(unwrap(self.value.y))

    @strawberry.field
    def width(self) -> float:
        return float(unwrap(self.value.width))

    @strawberry.field
    def height(self) -> float:
        return float(unwrap(self.value.height))


@strawberry.type
class Ellipse(Shape):
    @strawberry.field(description="Centre x.")
    def x(self) -> float:
        return float(unwrap(self.value.x))

    @strawberry.field(description="Centre y.")
    def y(self) -> float:
        return float(unwrap(self.value.y))

    @strawberry.field
    def radius_x(self) -> float:
        return float(unwrap(self.value.radiusX))

    @strawberry.field
    def radius_y(self) -> float:
        return float(unwrap(self.value.radiusY))


@strawberry.type
class Point(Shape):
    @strawberry.field
    def x(self) -> float:
        return float(unwrap(self.value.x))

    @strawberry.field
    def y(self) -> float:
        return float(unwrap(self.value.y))


@strawberry.type
class Line(Shape):
    @strawberry.field
    def x1(self) -> float:
        return float(unwrap(self.value.x1))

    @strawberry.field
    def y1(self) -> float:
        return float(unwrap(self.value.y1))

    @strawberry.field
    def x2(self) -> float:
        return float(unwrap(self.value.x2))

    @strawberry.field
    def y2(self) -> float:
        return float(unwrap(self.value.y2))


@strawberry.type(description="An x/y coordinate.")
class Vertex:
    x: float
    y: float


@strawberry.type
class Polygon(Shape):
    @strawberry.field
    def points(self) -> list[Vertex]:
        return [Vertex(x=x, y=y) for x, y in parse_points(unwrap(self.value.points))]


@strawberry.type
class Polyline(Shape):
    @strawberry.field
    def points(self) -> list[Vertex]:
        return [Vertex(x=x, y=y) for x, y in parse_points(unwrap(self.value.points))]


@strawberry.type(description="A text label anchored at a point.")
class Label(Shape):
    @strawberry.field
    def x(self) -> float:
        return float(unwrap(self.value.x))

    @strawberry.field
    def y(self) -> float:
        return float(unwrap(self.value.y))


@strawberry.type(description="A binary mask covering a rectangle. The mask bytes are not exposed over GraphQL.")
class Mask(Shape):
    @strawberry.field
    def x(self) -> float:
        return float(unwrap(self.value.x))

    @strawberry.field
    def y(self) -> float:
        return float(unwrap(self.value.y))

    @strawberry.field
    def width(self) -> float:
        return float(unwrap(self.value.width))

    @strawberry.field
    def height(self) -> float:
        return float(unwrap(self.value.height))


SHAPE_TYPES: dict[type, type] = {
    omero.model.RectangleI: Rectangle,
    omero.model.EllipseI: Ellipse,
    omero.model.PointI: Point,
    omero.model.LineI: Line,
    omero.model.PolygonI: Polygon,
    omero.model.PolylineI: Polyline,
    omero.model.LabelI: Label,
    omero.model.MaskI: Mask,
}


def wrap_shape(shape: omero.model.Shape) -> Optional[Shape]:
    """Pick the GraphQL type for a raw ``omero.model`` shape; ``None`` for unknown kinds."""
    gql = SHAPE_TYPES.get(type(shape))
    return gql(value=shape) if gql is not None else None


@strawberry.type(description="A region of interest on an image: a named group of shapes.")
class Roi(OmeroObject):
    value: strawberry.Private[og.RoiWrapper]

    @strawberry.field
    def image(self) -> Image:
        return Image(value=self.value.getImage())

    @strawberry.field
    def shapes(self) -> list[Shape]:
        obj = self.value._obj
        if not obj.isShapesLoaded():
            obj = get_conn().getObject("Roi", int(self.value.getId()), opts={"load_shapes": True})._obj
        return [s for s in (wrap_shape(sh) for sh in obj.copyShapes()) if s is not None]

    @strawberry.field
    def shape_count(self) -> int:
        obj = self.value._obj
        if obj.isShapesLoaded():
            return obj.sizeOfShapes()
        return len(self.shapes())


# Every type that only appears behind an interface has to be registered on
# the schema explicitly; the schema module passes this list as ``types=``.
INTERFACE_IMPLEMENTATIONS: list[type] = [
    *ANNOTATION_TYPES.values(),
    *SHAPE_TYPES.values(),
    Project,
    Dataset,
    Image,
    Screen,
    Plate,
    Well,
    PlateAcquisition,
    Roi,
]
