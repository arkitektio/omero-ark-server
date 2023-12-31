from django.db import models
from django.contrib.auth import get_user_model
from taggit.managers import TaggableManager
from bridge import enums
from koherent.fields import HistoryField, HistoricForeignKey
import koherent.signals
from django_choices_field import TextChoicesField


# Create your models here.
import boto3
import json
from django.conf import settings



class OmeroUser(models.Model):
    """
    A dataset is a collection of data files and metadata files.
    It mimics the concept of a folder in a file system and is the top level
    object in the data model.

    """

    user = models.ForeignKey(
        get_user_model(),
        on_delete=models.CASCADE,
        related_name="omero_user",
        help_text="The user that created the dataset",
    )
    omero_password = models.CharField(
        max_length=2000,
        help_text="The password for the omero user",
    )
    omero_username = models.CharField(
        max_length=2000,
        help_text="The username for the omero user",
    )
    


