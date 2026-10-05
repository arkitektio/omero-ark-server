# omero-ark-server

A GraphQL API over an [OMERO](https://www.openmicroscopy.org/omero/) server, for an
[Arkitekt](https://arkitekt.live) hub. It lets the hub's users and apps browse, annotate and
organize what is in OMERO, using OMERO's own terminology where possible. It stores no image
data and no metadata of its own: every request is answered live from OMERO, as the OMERO
login of the calling user.

## What it stores

One table. An `OmeroUser` row holds, for one hub user, the OMERO username, password, host
and port to connect with. A user creates their own with `ensureOmeroUser` and removes it
with `deleteMe`.

## Design

We use the Strawberry extensions system to pass a single user-authenticated BlitzGateway
session through the GraphQL resolvers (`bridge/conn.py`). One connection is opened per
operation and closed after it, so a query that touches many objects connects to OMERO once.

## API

GraphQL is served at `/graphql` (HTTP and WebSocket), with the SDL at `/schema`.

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

Beside GraphQL, `api/thumbnails/<id>/` returns a rendered JPEG thumbnail of an image
(`?size=`, default 200).

## Running

The image is `jhnnsrs/omero-ark`, for `linux/amd64` only. It has no default command:

```sh
bash run.sh   # wait for the database, apply migrations, serve on :80 (daphne)
```

Unlike the other Arkitekt services, this one still migrates when it starts.
`run-debug.sh` does the same with Django's autoreloading server, for development.

It needs an OMERO.server 5 it can reach on its Ice port (4064 by default), Postgres, Redis,
and tokens issued by lok.

The OMERO client library pins the platform: `zeroc-ice` is installed from a prebuilt
wheel that exists for Python 3.12 on x86-64 Linux, so the project requires Python 3.12 and
does not build on arm64.

## Configuration

The service reads `config.yaml`, or the file named by `ARKITEKT_CONFIG_FILE`; any value can
be overridden by an environment variable (`POSTGRES__HOST`). `python manage.py
validate_settings` prints the configuration as the service reads it, with secrets redacted.
The default OMERO server is set by `omero_host` and `omero_port`.

See [CONFIG.md](CONFIG.md) for every value.

## Development

```sh
uv sync
uv run pytest                  # unit tests only
uv run pytest --integration    # unit tests and the integration tests
uv run pytest -m integration   # the integration tests only
```

The integration tests run against a real stack, brought up by
[dokker](https://github.com/jhnnsrs/dokker) from `tests/integration/docker-compose.yaml`:
Postgres, Redis and a real OMERO.server with its own database. They need a running Docker
daemon and the host ports 5556, 6667, 4063 and 4064 free. OMERO takes a while to start; the
suite waits up to ten minutes for it.

## Releases

Releases are tags: a push to `main` cuts a stable version, a push to `next` a release
candidate. Each one publishes `jhnnsrs/omero-ark` under its version (`X.Y.Z`, `X.Y`, `X`),
plus `latest` from `main` and `next` from `next`. The `version` in `pyproject.toml` is a
placeholder. Release notes are on
[GitHub Releases](https://github.com/arkitektio/omero-ark-server/releases); `CHANGELOG.md`
is frozen.
