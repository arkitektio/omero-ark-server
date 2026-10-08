from django.db import models
from django.contrib.auth import get_user_model

# Create your models here.
from django.conf import settings


def configured_host() -> str:
    """The OMERO server the config names: a default asked for when a row is made, so that
    no migration carries one deployment's host."""
    return settings.OMERO_HOST


def configured_port() -> int:
    """The same for its port."""
    return settings.OMERO_PORT


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
    omero_host = models.CharField(
        max_length=2000,
        help_text="The host for the omero user",
        default=configured_host,
    )
    omero_port = models.IntegerField(
        help_text="The port for the omero user",
        default=configured_port,
    )
    


