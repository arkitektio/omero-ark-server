"""End-to-end coverage of the wider OMERO surface: metadata, HCS, annotations, ROIs, links, users.

Opt-in like the CRUD suite (``uv run pytest -m integration``). A module-scoped
seed creates one project/dataset/image (with real pixels via ezomero) and one
screen/plate/well pointing at that image, as root, straight through the
gateway; the tests then exercise everything through GraphQL.
"""

import uuid

import numpy as np
import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.omero,
    pytest.mark.django_db(transaction=True),
]


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


@pytest.fixture(scope="module")
def seed(backend_stack):
    """Seed OMERO with a project > dataset > image and a screen > plate > well > image."""
    import ezomero
    from omero.gateway import BlitzGateway
    from omero.model import ImageI, PlateI, WellI, WellSampleI
    from omero.rtypes import rint, rstring

    conn = BlitzGateway("root", "omero", host="localhost", port=4064)
    assert conn.connect()
    try:
        project_id = ezomero.post_project(conn, _uid("seed-proj"), description="seeded")
        dataset_id = ezomero.post_dataset(conn, _uid("seed-ds"), project_id=project_id)
        pixels = np.random.randint(0, 255, size=(16, 12, 1, 2, 1), dtype=np.uint8)  # x y z c t
        image_id = ezomero.post_image(conn, pixels, _uid("seed-img"), dataset_id=dataset_id, dim_order="xyzct")

        screen_id = ezomero.post_screen(conn, _uid("seed-screen"))
        plate = PlateI()
        plate.name = rstring(_uid("seed-plate"))
        plate.columns = rint(12)
        plate.rows = rint(8)
        well = WellI()
        well.row = rint(1)
        well.column = rint(2)
        sample = WellSampleI()
        sample.image = ImageI(image_id, False)
        well.addWellSample(sample)
        plate.addWell(well)
        plate = conn.getUpdateService().saveAndReturnObject(plate, conn.SERVICE_OPTS)
        plate_id = plate.id.val
        ezomero.link_plates_to_screen(conn, [plate_id], screen_id)

        yield dict(project=project_id, dataset=dataset_id, image=image_id, screen=screen_id, plate=plate_id, well=plate.copyWells()[0].id.val)
    finally:
        conn.close()


async def _ok(res):
    assert not res.errors, res.errors
    return res.data


# --- containers -----------------------------------------------------------------
async def test_image_metadata_and_ancestry(aexecute, omero_root_user, seed):
    await omero_root_user()
    data = await _ok(
        await aexecute(
            """
            query($id: ID!) {
              image(id: $id) {
                id name sizeX sizeY sizeZ sizeC sizeT pixelsType defaultZ defaultT
                creationDate acquisitionDate roiCount
                physicalSizeX { value unit symbol }
                channels { index label color windowStart windowEnd isActive }
                datasets { id name projects { id } }
                fileset { id }
                owner { omeName isAdmin }
                group { name }
                permissions { canEdit canAnnotate canDelete isOwned }
                well { position }
              }
            }
            """,
            {"id": str(seed["image"])},
        )
    )
    img = data["image"]
    assert (img["sizeX"], img["sizeY"], img["sizeZ"], img["sizeC"], img["sizeT"]) == (16, 12, 1, 2, 1)
    assert img["pixelsType"] == "uint8"
    assert [c["index"] for c in img["channels"]] == [0, 1]
    assert all(c["color"].startswith("#") and len(c["color"]) == 7 for c in img["channels"])
    assert img["datasets"][0]["id"] == str(seed["dataset"])
    assert img["datasets"][0]["projects"][0]["id"] == str(seed["project"])
    assert img["owner"]["omeName"] == "root" and img["owner"]["isAdmin"] is True
    assert img["permissions"]["isOwned"] is True and img["permissions"]["canEdit"] is True
    assert img["well"]["position"] == "B3"
    assert img["roiCount"] == 0


async def test_list_filters_push_down(aexecute, omero_root_user, seed):
    await omero_root_user()
    data = await _ok(
        await aexecute(
            """
            query($project: ID!, $dataset: ID!, $owner: ID!) {
              inProject: datasets(filters: {project: $project}) { id }
              inDataset: images(filters: {dataset: $dataset}) { id }
              byOwner: projects(filters: {owner: $owner, ids: [$project]}) { id datasetCount }
              orphans: datasets(filters: {orphaned: true}) { id }
              paged: images(pagination: {offset: 0, limit: 1}) { id }
            }
            """,
            {"project": str(seed["project"]), "dataset": str(seed["dataset"]), "owner": "0"},
        )
    )
    assert [d["id"] for d in data["inProject"]] == [str(seed["dataset"])]
    assert [i["id"] for i in data["inDataset"]] == [str(seed["image"])]
    assert data["byOwner"] == [{"id": str(seed["project"]), "datasetCount": 1}]
    assert str(seed["dataset"]) not in [d["id"] for d in data["orphans"]]
    assert len(data["paged"]) == 1


async def test_update_and_delete_project_without_children(aexecute, omero_root_user, seed):
    await omero_root_user()
    name = _uid("proj")
    created = await _ok(await aexecute("mutation($i: CreateProjectInput!) { createProject(input: $i) { id } }", {"i": {"name": name}}))
    pid = created["createProject"]["id"]
    ds = await _ok(await aexecute("mutation($i: CreateDatasetInput!) { createDataset(input: $i) { id } }", {"i": {"name": _uid("ds"), "projectId": pid}}))
    did = ds["createDataset"]["id"]

    updated = await _ok(await aexecute("mutation($i: UpdateObjectInput!) { updateProject(input: $i) { name description } }", {"i": {"id": pid, "description": "new desc"}}))
    assert updated["updateProject"] == {"name": name, "description": "new desc"}

    deleted = await _ok(await aexecute("mutation($i: DeleteContainerInput!) { deleteProject(input: $i) { id } }", {"i": {"id": pid}}))
    assert deleted["deleteProject"]["id"] == pid

    gone = await aexecute("query($id: ID!) { project(id: $id) { id } }", {"id": pid})
    assert gone.errors and "not found" in gone.errors[0].message
    survivor = await _ok(await aexecute("query($id: ID!) { dataset(id: $id) { id projects { id } } }", {"id": did}))
    assert survivor["dataset"]["projects"] == []


async def test_delete_dataset_with_children_removes_images(aexecute, omero_root_user, seed):
    await omero_root_user()
    import ezomero
    from omero.gateway import BlitzGateway

    conn = BlitzGateway("root", "omero", host="localhost", port=4064)
    conn.connect()
    try:
        did = ezomero.post_dataset(conn, _uid("ds"))
        iid = ezomero.post_image(conn, np.zeros((4, 4, 1, 1, 1), dtype=np.uint8), _uid("img"), dataset_id=did, dim_order="xyzct")
    finally:
        conn.close()

    await _ok(await aexecute("mutation($i: DeleteContainerInput!) { deleteDataset(input: $i) { id } }", {"i": {"id": str(did), "deleteChildren": True}}))
    gone = await aexecute("query($id: ID!) { image(id: $id) { id } }", {"id": str(iid)})
    assert gone.errors and "not found" in gone.errors[0].message


async def test_link_and_unlink_images_and_datasets(aexecute, omero_root_user, seed):
    await omero_root_user()
    ds = await _ok(await aexecute("mutation($i: CreateDatasetInput!) { createDataset(input: $i) { id projects { id } } }", {"i": {"name": _uid("orphan-ds")}}))
    did = ds["createDataset"]["id"]
    assert ds["createDataset"]["projects"] == []

    linked = await _ok(await aexecute("mutation($i: DatasetImagesInput!) { linkImages(input: $i) { images { id } } }", {"i": {"datasetId": did, "imageIds": [str(seed["image"])]}}))
    assert [i["id"] for i in linked["linkImages"]["images"]] == [str(seed["image"])]

    unlinked = await _ok(await aexecute("mutation($i: DatasetImagesInput!) { unlinkImages(input: $i) { images { id } } }", {"i": {"datasetId": did, "imageIds": [str(seed["image"])]}}))
    assert unlinked["unlinkImages"]["images"] == []
    still_there = await _ok(await aexecute("query($id: ID!) { image(id: $id) { datasets { id } } }", {"id": str(seed["image"])}))
    assert [d["id"] for d in still_there["image"]["datasets"]] == [str(seed["dataset"])]

    pl = await _ok(await aexecute("mutation($i: ProjectDatasetsInput!) { linkDatasets(input: $i) { datasets { id } } }", {"i": {"projectId": str(seed["project"]), "datasetIds": [did]}}))
    assert did in [d["id"] for d in pl["linkDatasets"]["datasets"]]
    pu = await _ok(await aexecute("mutation($i: ProjectDatasetsInput!) { unlinkDatasets(input: $i) { datasets { id } } }", {"i": {"projectId": str(seed["project"]), "datasetIds": [did]}}))
    assert did not in [d["id"] for d in pu["unlinkDatasets"]["datasets"]]


async def test_update_image(aexecute, omero_root_user, seed):
    await omero_root_user()
    name = _uid("renamed")
    data = await _ok(await aexecute("mutation($i: UpdateObjectInput!) { updateImage(input: $i) { id name } }", {"i": {"id": str(seed["image"]), "name": name}}))
    assert data["updateImage"]["name"] == name


# --- HCS ------------------------------------------------------------------------
async def test_screen_plate_well_hierarchy(aexecute, omero_root_user, seed):
    await omero_root_user()
    data = await _ok(
        await aexecute(
            """
            query($screen: ID!, $plate: ID!, $well: ID!) {
              screen(id: $screen) { id name plateCount plates { id name } }
              plates(filters: {screen: $screen}) { id rows columns rowLabels columnLabels wellCount screens { id }
                wells { id row column position images { id } samples { image { id } plateAcquisition { id } } } }
              well(id: $well) { position plate { id } }
              wells(filters: {plate: $plate}) { id }
            }
            """,
            {"screen": str(seed["screen"]), "plate": str(seed["plate"]), "well": str(seed["well"])},
        )
    )
    assert data["screen"]["plateCount"] == 1
    assert data["screen"]["plates"][0]["id"] == str(seed["plate"])
    plate = data["plates"][0]
    assert (plate["rows"], plate["columns"]) == (8, 12)
    assert plate["rowLabels"][:2] == ["A", "B"] and plate["columnLabels"][:2] == ["1", "2"]
    assert plate["screens"][0]["id"] == str(seed["screen"])
    well = plate["wells"][0]
    assert (well["row"], well["column"], well["position"]) == (1, 2, "B3")
    assert well["images"][0]["id"] == str(seed["image"])
    assert well["samples"][0]["image"]["id"] == str(seed["image"])
    assert data["well"]["plate"]["id"] == str(seed["plate"])
    assert [w["id"] for w in data["wells"]] == [str(seed["well"])]


async def test_screen_mutations_and_plate_links(aexecute, omero_root_user, seed):
    await omero_root_user()
    created = await _ok(await aexecute("mutation($i: CreateScreenInput!) { createScreen(input: $i) { id name } }", {"i": {"name": _uid("screen")}}))
    sid = created["createScreen"]["id"]
    linked = await _ok(await aexecute("mutation($i: ScreenPlatesInput!) { linkPlates(input: $i) { plates { id } } }", {"i": {"screenId": sid, "plateIds": [str(seed["plate"])]}}))
    assert [p["id"] for p in linked["linkPlates"]["plates"]] == [str(seed["plate"])]
    unlinked = await _ok(await aexecute("mutation($i: ScreenPlatesInput!) { unlinkPlates(input: $i) { plates { id } } }", {"i": {"screenId": sid, "plateIds": [str(seed["plate"])]}}))
    assert unlinked["unlinkPlates"]["plates"] == []
    renamed = await _ok(await aexecute("mutation($i: UpdateObjectInput!) { updateScreen(input: $i) { description } }", {"i": {"id": sid, "description": "d"}}))
    assert renamed["updateScreen"]["description"] == "d"
    await _ok(await aexecute("mutation($i: DeleteContainerInput!) { deleteScreen(input: $i) { id } }", {"i": {"id": sid}}))
    # the seed plate must survive an unlinked screen's deletion
    await _ok(await aexecute("query($id: ID!) { plate(id: $id) { id } }", {"id": str(seed["plate"])}))


# --- annotations ----------------------------------------------------------------
async def test_tags_end_to_end(aexecute, omero_root_user, seed):
    await omero_root_user()
    text = _uid("tag")
    created = await _ok(
        await aexecute(
            "mutation($i: CreateTagInput!) { createTag(input: $i) { id text description owner { omeName } } }",
            {"i": {"text": text, "description": "why", "target": {"type": "IMAGE", "id": str(seed["image"])}}},
        )
    )
    tag = created["createTag"]
    assert tag["text"] == text and tag["description"] == "why"

    img = await _ok(await aexecute("query($id: ID!) { image(id: $id) { tags annotations { __typename id ... on TagAnnotation { text } } } }", {"id": str(seed["image"])}))
    assert text in img["image"]["tags"]
    assert {"__typename": "TagAnnotation", "id": tag["id"], "text": text} in img["image"]["annotations"]

    listed = await _ok(await aexecute("query($s: String!) { tags(filters: {search: $s}) { id } tag(id: %s) { text } }" % tag["id"], {"s": text[-6:]}))
    assert [t["id"] for t in listed["tags"]] == [tag["id"]]
    assert listed["tag"]["text"] == text

    # link the same tag to the dataset, then unlink it from the image
    await _ok(await aexecute("mutation($i: AnnotationLinkInput!) { linkAnnotation(input: $i) { id } }", {"i": {"target": {"type": "DATASET", "id": str(seed["dataset"])}, "annotationId": tag["id"]}}))
    ds = await _ok(await aexecute("query($id: ID!) { dataset(id: $id) { tags } }", {"id": str(seed["dataset"])}))
    assert text in ds["dataset"]["tags"]
    await _ok(await aexecute("mutation($i: AnnotationLinkInput!) { unlinkAnnotation(input: $i) { id } }", {"i": {"target": {"type": "IMAGE", "id": str(seed["image"])}, "annotationId": tag["id"]}}))
    img2 = await _ok(await aexecute("query($id: ID!) { image(id: $id) { tags } }", {"id": str(seed["image"])}))
    assert text not in img2["image"]["tags"]

    await _ok(await aexecute("mutation($i: DeleteObjectInput!) { deleteAnnotation(input: $i) { id } }", {"i": {"id": tag["id"]}}))
    gone = await aexecute("query($id: ID!) { annotation(id: $id) { id } }", {"id": tag["id"]})
    assert gone.errors and "not found" in gone.errors[0].message


async def test_comment_and_map_annotations(aexecute, omero_root_user, seed):
    await omero_root_user()
    target = {"type": "PROJECT", "id": str(seed["project"])}
    comment = await _ok(await aexecute("mutation($i: CreateCommentInput!) { createComment(input: $i) { id text } }", {"i": {"target": target, "text": "hello"}}))
    kv = await _ok(
        await aexecute(
            "mutation($i: CreateMapAnnotationInput!) { createMapAnnotation(input: $i) { id ns values { key value } } }",
            {"i": {"target": target, "values": [{"key": "a", "value": "1"}, {"key": "b", "value": "2"}]}},
        )
    )
    assert kv["createMapAnnotation"]["values"] == [{"key": "a", "value": "1"}, {"key": "b", "value": "2"}]
    assert kv["createMapAnnotation"]["ns"] == "openmicroscopy.org/omero/client/mapAnnotation"

    proj = await _ok(
        await aexecute(
            """query($id: ID!) { project(id: $id) { annotations { __typename id ... on CommentAnnotation { text } ... on MapAnnotation { values { key } } } } }""",
            {"id": str(seed["project"])},
        )
    )
    kinds = {a["id"]: a for a in proj["project"]["annotations"]}
    assert kinds[comment["createComment"]["id"]] == {"__typename": "CommentAnnotation", "id": comment["createComment"]["id"], "text": "hello"}
    assert kinds[kv["createMapAnnotation"]["id"]]["values"] == [{"key": "a"}, {"key": "b"}]

    one = await _ok(await aexecute("query($id: ID!) { annotation(id: $id) { __typename ... on CommentAnnotation { text } } }", {"id": comment["createComment"]["id"]}))
    assert one["annotation"] == {"__typename": "CommentAnnotation", "text": "hello"}


# --- ROIs -----------------------------------------------------------------------
async def test_rois_end_to_end(aexecute, omero_root_user, seed):
    await omero_root_user()
    created = await _ok(
        await aexecute(
            """
            mutation($i: CreateRoiInput!) {
              createRoi(input: $i) {
                id name image { id } shapeCount
                shapes {
                  __typename id z t c text strokeColor fillColor
                  ... on Rectangle { x y width height }
                  ... on Ellipse { x y radiusX radiusY }
                  ... on Polygon { points { x y } }
                  ... on Point { x y }
                  ... on Line { x1 y1 x2 y2 }
                  ... on Label { x y }
                }
              }
            }
            """,
            {
                "i": {
                    "imageId": str(seed["image"]),
                    "name": "cells",
                    "shapes": [
                        {"geometry": {"rectangle": {"x": 1, "y": 2, "width": 3, "height": 4}}, "z": 0, "t": 0, "text": "r", "strokeColor": "#ff0000", "fillColor": "#00ff0080"},
                        {"geometry": {"ellipse": {"x": 5, "y": 5, "radiusX": 2, "radiusY": 1}}},
                        {"geometry": {"polygon": {"points": [{"x": 0, "y": 0}, {"x": 4, "y": 0}, {"x": 4, "y": 4}]}}},
                        {"geometry": {"point": {"x": 7, "y": 8}}},
                        {"geometry": {"line": {"x1": 0, "y1": 0, "x2": 3, "y2": 3}}},
                        {"geometry": {"label": {"x": 1, "y": 1, "text": "hello"}}},
                    ],
                }
            },
        )
    )
    roi = created["createRoi"]
    assert roi["name"] == "cells" and roi["image"]["id"] == str(seed["image"]) and roi["shapeCount"] == 6
    by_type = {s["__typename"]: s for s in roi["shapes"]}
    assert set(by_type) == {"Rectangle", "Ellipse", "Polygon", "Point", "Line", "Label"}
    rect = by_type["Rectangle"]
    assert (rect["x"], rect["y"], rect["width"], rect["height"]) == (1, 2, 3, 4)
    assert (rect["z"], rect["t"], rect["c"], rect["text"]) == (0, 0, None, "r")
    assert rect["strokeColor"] == "#ff0000ff" and rect["fillColor"] == "#00ff0080"
    assert by_type["Ellipse"]["z"] is None
    assert by_type["Polygon"]["points"] == [{"x": 0, "y": 0}, {"x": 4, "y": 0}, {"x": 4, "y": 4}]
    assert by_type["Label"]["text"] == "hello"

    listed = await _ok(await aexecute("query($img: ID!, $id: ID!) { rois(filters: {image: $img}) { id } roi(id: $id) { shapeCount } image(id: $img) { roiCount rois { id } } }", {"img": str(seed["image"]), "id": roi["id"]}))
    assert [r["id"] for r in listed["rois"]] == [roi["id"]]
    assert listed["roi"]["shapeCount"] == 6
    assert listed["image"]["roiCount"] == 1 and listed["image"]["rois"][0]["id"] == roi["id"]

    await _ok(await aexecute("mutation($i: DeleteObjectInput!) { deleteRoi(input: $i) { id } }", {"i": {"id": roi["id"]}}))
    after = await _ok(await aexecute("query($img: ID!) { image(id: $img) { roiCount } }", {"img": str(seed["image"])}))
    assert after["image"]["roiCount"] == 0


# --- experimenters --------------------------------------------------------------
async def test_experimenters_and_groups(aexecute, omero_root_user, seed):
    await omero_root_user()
    data = await _ok(
        await aexecute(
            """
            {
              currentExperimenter { id omeName fullName isAdmin groups { id name } }
              experimenters(filters: {search: "root"}) { omeName }
              groups(filters: {search: "system"}) { name members { omeName } }
              experimenter(id: "0") { omeName }
            }
            """
        )
    )
    me = data["currentExperimenter"]
    assert me["omeName"] == "root" and me["isAdmin"] is True
    assert "system" in [g["name"] for g in me["groups"]]
    assert "root" in [e["omeName"] for e in data["experimenters"]]
    assert data["groups"][0]["name"] == "system" and "root" in [m["omeName"] for m in data["groups"][0]["members"]]
    assert data["experimenter"]["omeName"] == "root"


async def test_missing_objects_report_not_found(aexecute, omero_root_user, seed):
    await omero_root_user()
    for query in ("{ image(id: \"999999999\") { id } }", "{ plate(id: \"999999999\") { id } }", "{ image(id: \"abc\") { id } }"):
        res = await aexecute(query)
        assert res.errors, query
        assert "not found" in res.errors[0].message or "must be an integer" in res.errors[0].message
