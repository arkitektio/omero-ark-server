"""Filter inputs for the list queries.

Filters are plain data; ``bridge.gateway.list_objects`` interprets them. ``ids``
and ``owner`` are pushed into OMERO's query, ``search`` is a case-insensitive
substring match on the name applied in Python.
"""

import strawberry


@strawberry.input
class IDFilterMixin:
    ids: list[strawberry.ID] | None = None


@strawberry.input
class SearchFilterMixin:
    search: str | None = None


@strawberry.input
class OwnerFilterMixin:
    owner: strawberry.ID | None = strawberry.field(default=None, description="Only objects owned by this experimenter.")


@strawberry.input
class ProjectFilter(IDFilterMixin, SearchFilterMixin, OwnerFilterMixin):
    pass


@strawberry.input
class DatasetFilter(IDFilterMixin, SearchFilterMixin, OwnerFilterMixin):
    project: strawberry.ID | None = strawberry.field(default=None, description="Only datasets linked into this project.")
    orphaned: bool | None = strawberry.field(default=None, description="Only datasets that are in no project.")


@strawberry.input
class ImageFilter(IDFilterMixin, SearchFilterMixin, OwnerFilterMixin):
    dataset: strawberry.ID | None = strawberry.field(default=None, description="Only images linked into this dataset.")
    orphaned: bool | None = strawberry.field(default=None, description="Only images that are in no dataset and no well.")


@strawberry.input
class ScreenFilter(IDFilterMixin, SearchFilterMixin, OwnerFilterMixin):
    pass


@strawberry.input
class PlateFilter(IDFilterMixin, SearchFilterMixin, OwnerFilterMixin):
    screen: strawberry.ID | None = strawberry.field(default=None, description="Only plates linked into this screen.")
    orphaned: bool | None = strawberry.field(default=None, description="Only plates that are in no screen.")


@strawberry.input
class WellFilter(IDFilterMixin):
    plate: strawberry.ID | None = strawberry.field(default=None, description="Only wells of this plate.")


@strawberry.input
class TagFilter(IDFilterMixin, SearchFilterMixin, OwnerFilterMixin):
    pass


@strawberry.input
class RoiFilter(IDFilterMixin):
    image: strawberry.ID | None = strawberry.field(default=None, description="Only ROIs drawn on this image.")


@strawberry.input
class ExperimenterFilter(IDFilterMixin, SearchFilterMixin):
    pass


@strawberry.input
class ExperimenterGroupFilter(IDFilterMixin, SearchFilterMixin):
    pass
