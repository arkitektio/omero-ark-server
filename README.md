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
