from kante.channel import build_channel
from pydantic import BaseModel, Field  


class ImageSignal(BaseModel):
    image: int | None = Field(None, description="The message that was created.")



image_channel = build_channel(ImageSignal)
