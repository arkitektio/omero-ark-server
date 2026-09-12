"""Unit tests for the pydantic input models in bridge/inputs.py.

These are pure validation models (no DB / no OMERO), so they run on every
`pytest` invocation.
"""

import pytest
from django.conf import settings
from pydantic import ValidationError

from bridge.inputs import (
    CreateDatasetInputModel,
    CreateProjectInputModel,
    DeleteImageInputModel,
    OmeroUserInputModel,
)


class TestOmeroUserInputModel:
    def test_defaults_host_and_port_from_settings(self):
        m = OmeroUserInputModel(username="root", password="omero")
        assert m.host == settings.OMERO_HOST
        assert m.port == settings.OMERO_PORT

    def test_explicit_host_and_port_override_defaults(self):
        m = OmeroUserInputModel(
            username="root", password="omero", host="otherhost", port=4242
        )
        assert m.host == "otherhost"
        assert m.port == 4242

    def test_username_and_password_required(self):
        with pytest.raises(ValidationError):
            OmeroUserInputModel(password="omero")
        with pytest.raises(ValidationError):
            OmeroUserInputModel(username="root")


class TestCreateProjectInputModel:
    def test_description_optional(self):
        m = CreateProjectInputModel(name="proj")
        assert m.name == "proj"
        assert m.description is None

    def test_name_required(self):
        with pytest.raises(ValidationError):
            CreateProjectInputModel(description="no name")


class TestCreateDatasetInputModel:
    def test_valid(self):
        m = CreateDatasetInputModel(project_id="12", name="ds", description="d")
        assert m.project_id == "12"
        assert m.name == "ds"

    def test_project_id_rejects_non_string(self):
        # project_id is typed as str; pydantic v2 does not coerce ints to str.
        with pytest.raises(ValidationError):
            CreateDatasetInputModel(project_id=12, name="ds")

    def test_project_id_and_name_required(self):
        with pytest.raises(ValidationError):
            CreateDatasetInputModel(name="ds")
        with pytest.raises(ValidationError):
            CreateDatasetInputModel(project_id="1")


class TestDeleteImageInputModel:
    def test_id_required(self):
        with pytest.raises(ValidationError):
            DeleteImageInputModel()

    def test_valid(self):
        assert DeleteImageInputModel(id="99").id == "99"
