# Omero-Ark-Server


[![codecov](https://codecov.io/gh/arkitektio/omero-ark-server/branch/main/graph/badge.svg?token=UGXEA2THBV)](https://codecov.io/gh/arkitektio/omero-ark-server)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://github.com/arkitektio/omero-ark-server/)
![Maintainer](https://img.shields.io/badge/maintainer-jhnnsrs-blue)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](http://mypy-lang.org/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/jhnnsrs/arkitektio/omero-ark-server)

## Develompent

Omero Ark is a GraphQL API that allows you to interact with OMERO.  Where possible it tries to use the same terminology as OMERO. 
It is written in Python and uses the [Strawberry](https://strawberry.rocks) library to implement the GraphQL API. It is
a micro-service to run within the [Arkitekt](https://arkitekt.live) framework.

### Design

We use the Strawberry Extensions system to pass a `single` user authenticated BlitzGateway session through
the GraphQL resolvers. This should reduce the number of times we need to connect to OMERO, and allow for
more efficient queries.

### API surface

Everything is scoped to the OMERO session of the calling user (their
`OmeroUser` row): a client only ever sees what that OMERO login can see.

| Area | Queries | Mutations |
| --- | --- | --- |
| Project / Dataset / Image | `projects`, `project`, `datasets`, `dataset`, `images`, `image` (filters: `ids`, `search`, `owner`, `project`/`dataset`, `orphaned`; offset pagination) | `createProject`, `updateProject`, `deleteProject`, `createDataset`, `updateDataset`, `deleteDataset`, `updateImage`, `deleteImage` |
| Screen / Plate / Well | `screens`, `screen`, `plates`, `plate`, `wells`, `well`, `plateAcquisition` | `createScreen`, `updateScreen`, `deleteScreen`, `updatePlate`, `deletePlate` |
| Links (many-to-many) | via `datasets`/`projects`/`images`/`screens` fields on each type | `linkDatasets`, `unlinkDatasets`, `linkImages`, `unlinkImages`, `linkPlates`, `unlinkPlates` |
| Annotations | `tags`, `tag`, `annotation`; `annotations`/`tags` on every object | `createTag`, `createComment`, `createMapAnnotation`, `linkAnnotation`, `unlinkAnnotation`, `deleteAnnotation` |
| ROIs | `rois`, `roi`; `rois`/`roiCount` on `Image` | `createRoi` (rectangle, ellipse, point, line, polygon, polyline, label), `deleteRoi` |
| Users | `currentExperimenter`, `experimenters`, `experimenter`, `groups`, `group` | `ensureOmeroUser`, `deleteMe` |

Every OMERO-backed type implements the `OmeroObject` interface (`id`, `name`,
`description`, `creationDate`, `owner`, `group`, `permissions`, `annotations`,
`tags`). `Image` additionally exposes dimensions, pixel type, physical sizes,
channels with rendering windows, the fileset it was imported from, its
datasets and (for HCS data) its well. Annotations and shapes are GraphQL
interfaces (`Annotation`, `Shape`), so query them with inline fragments
(`... on TagAnnotation { text }`, `... on Rectangle { x y width height }`).

Container deletes take `deleteChildren` (default `false`): without it a
project/dataset/screen is removed and its children become orphans, exactly as
in OMERO.insight/web.

### Testing

```bash
uv sync
uv run pytest                  # unit tests only
uv run pytest -m integration   # also boots postgres + redis + a real OMERO.server via dokker (slow)
```
