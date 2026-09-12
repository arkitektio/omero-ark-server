"""Unit tests for the filter + pagination logic in the projects resolver.

The resolver pulls projects from a live OMERO gateway via get_conn(); here we
monkeypatch get_conn() with a fake gateway returning in-memory objects, so the
filtering/slicing logic is exercised without any OMERO server.
"""

from strawberry_django.pagination import OffsetPaginationInput

import importlib

from bridge.filters import ProjectFilter

# bridge.queries re-exports the `projects` function, which shadows the
# `bridge.queries.projects` submodule on the package — so grab the module from
# sys.modules via importlib to monkeypatch its get_conn.
projects_module = importlib.import_module("bridge.queries.projects")


class FakeProject:
    def __init__(self, id_, name):
        self._id = id_
        self._name = name

    def getId(self):
        return self._id

    def getName(self):
        return self._name


class FakeConn:
    def __init__(self, projects):
        self._projects = projects

    def listProjects(self):
        return list(self._projects)


def _patch_conn(monkeypatch, fake_projects):
    monkeypatch.setattr(
        projects_module, "get_conn", lambda: FakeConn(fake_projects)
    )


def test_no_filters_returns_all(monkeypatch):
    fakes = [FakeProject(1, "alpha"), FakeProject(2, "beta")]
    _patch_conn(monkeypatch, fakes)
    result = projects_module.projects()
    assert [p.value for p in result] == fakes


def test_filter_by_ids(monkeypatch):
    fakes = [FakeProject(1, "alpha"), FakeProject(2, "beta"), FakeProject(3, "gamma")]
    _patch_conn(monkeypatch, fakes)
    result = projects_module.projects(filters=ProjectFilter(ids=["1", "3"]))
    assert [p.value.getId() for p in result] == [1, 3]


def test_filter_by_search_substring(monkeypatch):
    fakes = [FakeProject(1, "alpha"), FakeProject(2, "alphabet"), FakeProject(3, "beta")]
    _patch_conn(monkeypatch, fakes)
    result = projects_module.projects(filters=ProjectFilter(search="alpha"))
    assert [p.value.getName() for p in result] == ["alpha", "alphabet"]


def test_pagination_offset_and_limit(monkeypatch):
    fakes = [FakeProject(i, f"p{i}") for i in range(5)]
    _patch_conn(monkeypatch, fakes)
    result = projects_module.projects(
        pagination=OffsetPaginationInput(offset=1, limit=2)
    )
    assert [p.value.getId() for p in result] == [1, 2]


def test_filter_then_paginate(monkeypatch):
    fakes = [FakeProject(i, "match" if i % 2 == 0 else "skip") for i in range(6)]
    _patch_conn(monkeypatch, fakes)
    result = projects_module.projects(
        filters=ProjectFilter(search="match"),
        pagination=OffsetPaginationInput(offset=1, limit=1),
    )
    # matches are ids 0,2,4; offset 1 limit 1 -> id 2
    assert [p.value.getId() for p in result] == [2]
