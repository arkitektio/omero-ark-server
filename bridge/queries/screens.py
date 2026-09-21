"""Screen / Plate / Well / PlateAcquisition queries (the HCS hierarchy)."""

from typing import List

import strawberry
from strawberry_django import pagination

from bridge import filters, types
from bridge.gateway import get_object, list_objects


def screens(filters: filters.ScreenFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> List[types.Screen]:
    """List the screens visible to the current OMERO user."""
    return [
        types.Screen(value=s)
        for s in list_objects(
            "Screen",
            ids=filters.ids if filters else None,
            search=filters.search if filters else None,
            owner=filters.owner if filters else None,
            offset=pagination.offset if pagination else None,
            limit=pagination.limit if pagination else None,
        )
    ]


def screen(id: strawberry.ID) -> types.Screen:
    """Fetch one screen by id."""
    return types.Screen(value=get_object("Screen", id))


def plates(filters: filters.PlateFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> List[types.Plate]:
    """List plates, optionally restricted to one screen or to orphans."""
    opts = {}
    if filters and filters.screen is not None:
        opts["screen"] = int(filters.screen)
    if filters and filters.orphaned:
        opts["orphaned"] = True
    return [
        types.Plate(value=p)
        for p in list_objects(
            "Plate",
            ids=filters.ids if filters else None,
            search=filters.search if filters else None,
            owner=filters.owner if filters else None,
            opts=opts,
            offset=pagination.offset if pagination else None,
            limit=pagination.limit if pagination else None,
        )
    ]


def plate(id: strawberry.ID) -> types.Plate:
    """Fetch one plate by id."""
    return types.Plate(value=get_object("Plate", id))


def wells(filters: filters.WellFilter | None = None, pagination: pagination.OffsetPaginationInput | None = None) -> List[types.Well]:
    """List wells, usually of one plate."""
    opts = {}
    if filters and filters.plate is not None:
        opts["plate"] = int(filters.plate)
    return [
        types.Well(value=w)
        for w in list_objects(
            "Well",
            ids=filters.ids if filters else None,
            opts=opts,
            offset=pagination.offset if pagination else None,
            limit=pagination.limit if pagination else None,
        )
    ]


def well(id: strawberry.ID) -> types.Well:
    """Fetch one well by id."""
    return types.Well(value=get_object("Well", id))


def plate_acquisition(id: strawberry.ID) -> types.PlateAcquisition:
    """Fetch one plate acquisition (run) by id."""
    return types.PlateAcquisition(value=get_object("PlateAcquisition", id))
