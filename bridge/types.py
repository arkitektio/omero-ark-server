import strawberry
import strawberry.django
from strawberry import auto
from typing import List, Optional, Annotated, Union, cast
import strawberry_django
from bridge import models, scalars, filters, enums
from django.contrib.auth import get_user_model
from koherent.models import AppHistoryModel
from authentikate.strawberry.types import App
from kante.types import Info
import datetime

from itertools import chain
from enum import Enum
from strawberry.experimental import pydantic
from pydantic import BaseModel

@strawberry.type
class DeleteResult:
    id: str


@strawberry_django.type(get_user_model())
class User:
    id: auto
    sub: str
    username: str
    email: str
    password: str

    @strawberry_django.field
    def omero_user(self) -> Optional["OmeroUser"]:
        return models.OmeroUser.objects.filter(user=self).first()



@strawberry.type()
class Image:
    value: strawberry.Private[object]

    @strawberry.field
    def name(self) -> str:
        return self.value.getName()
    

    @strawberry.field
    def description(self) -> str:
        return self.value.getDescription()
    
    @strawberry.field
    def tags(self) -> list[str]:
        return ["fake"]

    
    @strawberry.field
    def id(self) -> str:
        return self.value.getId()
    
    @strawberry.field
    def acquisition_date(self) -> Optional[datetime.datetime]:
        return self.value.getAcquisitionDate()
    
    @strawberry.field
    def original_file(self) -> Optional[str]:
        return self.value.getOriginalFile()




@strawberry.type()
class Dataset:
    value: strawberry.Private[object]


    @strawberry.field
    def id(self) -> str:
        print(self.value)
        return self.value.getId()

    @strawberry.field
    def name(self) -> str:
        return self.value.getName()
    
    @strawberry.field
    def description(self) -> str:
        return self.value.getDescription()
    
    @strawberry.field
    def tags(self) -> list[str]:
        return ["fake"]
    
    @strawberry.field
    def images(self) -> list[Image]:
        return [Image(value=i) for i in self.value.listChildren()]
    




@strawberry.type()
class Project:
    value: strawberry.Private[object]


    @strawberry.field
    def id(self) -> str:
        return self.value.getId()

    @strawberry.field
    def name(self) -> str:
        return self.value.getName()
    
    @strawberry.field
    def tags(self) -> list[str]:
        return ["fake"]
    
    @strawberry.field
    def description(self) -> str:
        return self.value.getDescription()
    
    @strawberry.field
    def datasets(self) -> list[Dataset]:
        return [Dataset(value=i) for i in self.value.listChildren()]
    
    




@strawberry_django.type(models.OmeroUser)
class OmeroUser:
    id: auto
    omero_password: str
    omero_username: str
    user: User