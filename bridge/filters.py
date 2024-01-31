import strawberry
from bridge import models
from koherent.strawberry.filters import ProvenanceFilter
from strawberry import auto
from typing import Optional
from strawberry_django.filters import FilterLookup


@strawberry.input
class IDFilterMixin:
    ids: list[strawberry.ID] | None = None

    def filter_ids(self, queryset, info):
        if self.ids is None:
            return queryset
        return queryset.filter(id__in=self.ids)


@strawberry.input
class SearchFilterMixin:
    search: str | None = None

    def filter_search(self, queryset, info):
        if self.search is None:
            return queryset
        return queryset.filter(name__contains=self.search)





@strawberry.input
class ProjectFilter:
    ids: list[strawberry.ID] | None = None
    search: str | None = None
    pass

@strawberry.input
class ImageFilter(IDFilterMixin, SearchFilterMixin):
    pass

@strawberry.input
class DatasetFilter(IDFilterMixin, SearchFilterMixin):
    pass