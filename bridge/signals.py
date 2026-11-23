from typing import Any

from django.db.models.signals import post_save
from django.dispatch import receiver

from bridge.channel import image_broadcast
from bridge.models import Image


@receiver(post_save, sender=Image)
def my_handler(sender: type[Image], **kwargs: Any) -> None:
    image_broadcast(kwargs["instance"].id)
