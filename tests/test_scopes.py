"""What an app may do here is what its token's scopes say: every root field asks for one of omero-ark's
own (the ``@auth`` directive publishes it, a generated client gathers it), and `omero_ark_all` stands
for all of them."""

import pytest
from kante.context import HttpContext, UniversalRequest
from strawberry.http.temporal_response import TemporalResponse

from arkitekt_service.graphql import scope_gaps
from omero_ark.schema import schema

ME = "query { me { id } }"
REGISTER_ROOT = 'mutation { ensureOmeroUser(input: {username: "root", password: "omero", host: "localhost", port: 4064}) { id } }'


def _as(token: str) -> HttpContext:
    return HttpContext(request=UniversalRequest(_extensions={}), response=TemporalResponse(), headers={"Authorization": f"Bearer {token}"}, type="http")


def _reason(result) -> str | None:
    return result.errors[0].extensions.get("reason") if result.errors else None


def test_every_root_field_asks_for_a_scope_omero_ark_declares():
    assert scope_gaps(schema) == []


@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_an_app_granted_reads_reads_and_writes_nothing(backend_stack):
    assert (await schema.execute(ME, context_value=_as("readertest"))).errors is None
    refused = await schema.execute(REGISTER_ROOT, context_value=_as("readertest"))
    assert _reason(refused) == "INSUFFICIENT_SCOPE"


@pytest.mark.integration
@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
async def test_the_all_scope_writes(backend_stack):
    made = await schema.execute(REGISTER_ROOT, context_value=_as("test"))
    assert made.errors is None, made.errors
