"""Unit tests for the pure helpers in bridge.gateway and the ROI input mapper.

These need no OMERO server: they cover colour packing, OMERO's points string
dialects, and the GraphQL -> ezomero shape translation.
"""

import pytest
import strawberry

from bridge import inputs
from bridge.gateway import hex_to_rgba_tuple, parse_points, rgba_int_to_hex


class TestColours:
    def test_rgba_int_round_trips_through_signed_int32(self):
        # OMERO stores opaque red as the signed int32 for 0xFF0000FF.
        packed = 0xFF0000FF - (1 << 32)
        assert rgba_int_to_hex(packed) == "#ff0000ff"
        assert rgba_int_to_hex(-1) == "#ffffffff"
        assert rgba_int_to_hex(None) is None

    def test_hex_to_tuple_accepts_short_and_long_forms(self):
        assert hex_to_rgba_tuple("#ff0000") == (255, 0, 0, 255)
        assert hex_to_rgba_tuple("00ff0080") == (0, 255, 0, 128)
        assert hex_to_rgba_tuple(None) is None

    def test_hex_to_tuple_rejects_garbage(self):
        with pytest.raises(ValueError):
            hex_to_rgba_tuple("#abc")


class TestPoints:
    def test_plain_dialect(self):
        assert parse_points("1,2 3.5,4") == [(1.0, 2.0), (3.5, 4.0)]

    def test_legacy_bracketed_dialect_uses_first_list(self):
        assert parse_points("points[1,2 3,4] points1[9,9] mask[]") == [(1.0, 2.0), (3.0, 4.0)]

    def test_empty(self):
        assert parse_points(None) == []
        assert parse_points("") == []


class TestShapeFromInput:
    def _shape(self, **geometry):
        return inputs.ShapeInput(geometry=inputs.GeometryInput(**geometry), z=1, t=2, c=None, text="lbl", stroke_color="#ff0000", fill_color=None, stroke_width=2.0)

    def test_rectangle(self):
        from bridge.mutations.rois import shape_from_input
        import ezomero.rois as ez

        shape = shape_from_input(self._shape(rectangle=inputs.RectangleInput(x=1, y=2, width=3, height=4)))
        assert isinstance(shape, ez.Rectangle)
        assert (shape.x, shape.y, shape.width, shape.height) == (1, 2, 3, 4)
        assert (shape.z, shape.t, shape.c) == (1, 2, None)
        assert shape.stroke_color == (255, 0, 0, 255)
        assert shape.fill_color is None
        assert shape.label == "lbl"

    def test_unset_members_are_skipped(self):
        """Members a client omits arrive as UNSET; only the provided geometry may be picked."""
        from bridge.mutations.rois import shape_from_input
        import ezomero.rois as ez

        geometry = inputs.GeometryInput(polygon=inputs.PolygonInput(points=[inputs.VertexInput(x=0, y=0), inputs.VertexInput(x=1, y=1)]))
        assert geometry.rectangle is strawberry.UNSET
        shape = shape_from_input(inputs.ShapeInput(geometry=geometry))
        assert isinstance(shape, ez.Polygon)
        assert shape.points == [(0, 0), (1, 1)]

    def test_every_geometry_maps(self):
        from bridge.mutations.rois import shape_from_input
        import ezomero.rois as ez

        cases = {
            "ellipse": (inputs.EllipseInput(x=1, y=1, radius_x=2, radius_y=3), ez.Ellipse),
            "point": (inputs.PointInput(x=1, y=1), ez.Point),
            "line": (inputs.LineInput(x1=0, y1=0, x2=1, y2=1), ez.Line),
            "polyline": (inputs.PolylineInput(points=[inputs.VertexInput(x=0, y=0)]), ez.Polyline),
            "label": (inputs.LabelInput(x=0, y=0, text="hi"), ez.Label),
        }
        for key, (value, expected) in cases.items():
            assert isinstance(shape_from_input(inputs.ShapeInput(geometry=inputs.GeometryInput(**{key: value}))), expected), key

    def test_no_geometry_is_an_error(self):
        from bridge.mutations.rois import shape_from_input

        with pytest.raises(ValueError):
            shape_from_input(inputs.ShapeInput(geometry=inputs.GeometryInput()))
