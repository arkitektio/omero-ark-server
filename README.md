# Omero-Ark

## Develompent

Omero Ark is a GraphQL API that allows you to interact with OMERO.  Where possible it tries to use the same terminology as OMERO. 
It is written in Python and uses the [Strawberry](https://strawberry.rocks) library to implement the GraphQL API. It is
a micro-service to run within the [Arkitekt](https://arkitekt.live) framework.

### Design

We use the Strawberry Extensions system to pass a `single` user authenticated BlitzGateway session through
the GraphQL resolvers. This should reduce the number of times we need to connect to OMERO, and allow for
more efficient queries.
