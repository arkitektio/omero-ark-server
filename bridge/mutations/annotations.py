"""Annotation mutations: tags, comments, key/value maps, and the links between annotations and objects."""

import omero.constants.metadata
import omero.gateway as og
from kante.types import Info

from bridge import inputs, types
from bridge.conn import get_conn
from bridge.gateway import delete_objects, find_link_ids, get_object


def _target(target: inputs.AnnotationTargetInput, conn):
    return get_object(target.type.value, target.id, conn=conn)


def create_tag(info: Info, input: inputs.CreateTagInput) -> types.TagAnnotation:
    """Create a tag, optionally linking it to an object straight away."""
    conn = get_conn()
    tag = og.TagAnnotationWrapper(conn)
    tag.setValue(input.text)
    if input.description is not None:
        tag.setDescription(input.description)
    tag.save()
    if input.target is not None:
        _target(input.target, conn).linkAnnotation(tag)
    return types.TagAnnotation(value=get_object("TagAnnotation", tag.getId(), conn=conn))


def create_comment(info: Info, input: inputs.CreateCommentInput) -> types.CommentAnnotation:
    """Attach a free-text comment to an object."""
    conn = get_conn()
    comment = og.CommentAnnotationWrapper(conn)
    comment.setValue(input.text)
    comment.save()
    _target(input.target, conn).linkAnnotation(comment)
    return types.CommentAnnotation(value=get_object("CommentAnnotation", comment.getId(), conn=conn))


def create_map_annotation(info: Info, input: inputs.CreateMapAnnotationInput) -> types.MapAnnotation:
    """Attach key/value pairs to an object."""
    conn = get_conn()
    ann = og.MapAnnotationWrapper(conn)
    ann.setNs(input.ns or omero.constants.metadata.NSCLIENTMAPANNOTATION)
    ann.setValue([[kv.key, kv.value] for kv in input.values])
    ann.save()
    _target(input.target, conn).linkAnnotation(ann)
    return types.MapAnnotation(value=get_object("MapAnnotation", ann.getId(), conn=conn))


def link_annotation(info: Info, input: inputs.AnnotationLinkInput) -> types.Annotation:
    """Link an existing annotation (typically a tag) to an object."""
    conn = get_conn()
    ann = get_object("Annotation", input.annotation_id, conn=conn)
    _target(input.target, conn).linkAnnotation(ann)
    return types.wrap_annotation(get_object("Annotation", input.annotation_id, conn=conn))


def unlink_annotation(info: Info, input: inputs.AnnotationLinkInput) -> types.Annotation:
    """Remove the link between an annotation and an object. The annotation itself survives."""
    conn = get_conn()
    link_type = f"{input.target.type.value}AnnotationLink"
    link_ids = find_link_ids(link_type, input.target.id, input.annotation_id, conn=conn)
    if link_ids:
        delete_objects(link_type, link_ids, delete_children=True, conn=conn)
    return types.wrap_annotation(get_object("Annotation", input.annotation_id, conn=conn))


def delete_annotation(info: Info, input: inputs.DeleteObjectInput) -> types.DeleteResult:
    """Delete an annotation and every link to it."""
    delete_objects("Annotation", [input.id])
    return types.DeleteResult(id=input.id)
