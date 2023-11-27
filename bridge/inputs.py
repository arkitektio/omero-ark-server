import strawberry_django
from bridge import models
from typing import List, Optional
from strawberry import ID
import strawberry
from pydantic import BaseModel
from strawberry.experimental import pydantic


class OmeroUserInputModel(BaseModel):
    username:str
    password: str


@pydantic.input(OmeroUserInputModel)
class OmerUserInput:
    username: str
    password: str



