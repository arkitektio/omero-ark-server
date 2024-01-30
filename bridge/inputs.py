import strawberry_django
from bridge import models
from typing import List, Optional
from strawberry import ID
import strawberry
from pydantic import BaseModel
from strawberry.experimental import pydantic
from django.conf import settings
from strawberry import field

class OmeroUserInputModel(BaseModel):
    username:str
    password: str
    host: str | None = settings.OMERO_HOST
    port: int | None = settings.OMERO_PORT


@pydantic.input(OmeroUserInputModel)
class OmeroUserInput:
    username: str
    password: str
    host: str | None = field(default=settings.OMERO_HOST, description="The host for the omero user (relative to SERVER not client)")
    port: int | None = field(default=settings.OMERO_PORT, description="The port for the omero user (relative to SERVER not client)")



class CreateProjectInputModel(BaseModel):
    name: str
    description: str | None = None

@pydantic.input(CreateProjectInputModel)
class CreateProjectInput:
    name: str
    description: str | None = None