"""ROI mutations, built on ezomero's shape dataclasses."""

import ezomero
import ezomero.rois as ez
import strawberry
from kante.types import Info

from bridge import inputs, types
from bridge.conn import get_conn
from bridge.gateway import delete_objects, get_object, hex_to_rgba_tuple


def _set(value) -> bool:
    """One-of input members that were not provided arrive as UNSET (or None); only a provided one counts."""
    return value is not None and value is not strawberry.UNSET


def shape_from_input(shape: inputs.ShapeInput):
    """Translate one GraphQL shape input into the ezomero dataclass ``post_roi`` expects."""
    common = dict(
        z=shape.z,
        c=shape.c,
        t=shape.t,
        fill_color=hex_to_rgba_tuple(shape.fill_color),
        stroke_color=hex_to_rgba_tuple(shape.stroke_color),
        stroke_width=shape.stroke_width,
    )
    g = shape.geometry
    if _set(g.rectangle):
        return ez.Rectangle(x=g.rectangle.x, y=g.rectangle.y, width=g.rectangle.width, height=g.rectangle.height, label=shape.text, **common)
    if _set(g.ellipse):
        return ez.Ellipse(x=g.ellipse.x, y=g.ellipse.y, x_rad=g.ellipse.radius_x, y_rad=g.ellipse.radius_y, label=shape.text, **common)
    if _set(g.point):
        return ez.Point(x=g.point.x, y=g.point.y, label=shape.text, **common)
    if _set(g.line):
        return ez.Line(x1=g.line.x1, y1=g.line.y1, x2=g.line.x2, y2=g.line.y2, label=shape.text, **common)
    if _set(g.polygon):
        return ez.Polygon(points=[(p.x, p.y) for p in g.polygon.points], label=shape.text, **common)
    if _set(g.polyline):
        return ez.Polyline(points=[(p.x, p.y) for p in g.polyline.points], label=shape.text, **common)
    if _set(g.label):
        return ez.Label(x=g.label.x, y=g.label.y, label=g.label.text, fontSize=g.label.font_size, **common)
    raise ValueError("ShapeInput.geometry must set exactly one geometry")


def create_roi(info: Info, input: inputs.CreateRoiInput) -> types.Roi:
    """Create a region of interest with one or more shapes on an image."""
    conn = get_conn()
    shapes = [shape_from_input(s) for s in input.shapes]
    if not shapes:
        raise ValueError("A ROI needs at least one shape")
    roi_id = ezomero.post_roi(conn, int(input.image_id), shapes, name=input.name, description=input.description)
    return types.Roi(value=get_object("Roi", roi_id, conn=conn))


def delete_roi(info: Info, input: inputs.DeleteObjectInput) -> types.DeleteResult:
    """Delete a ROI and all its shapes."""
    delete_objects("Roi", [input.id], delete_children=True)
    return types.DeleteResult(id=input.id)
