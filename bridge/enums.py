from django.db.models import TextChoices
import strawberry
from enum import Enum



@strawberry.enum
class ColorFormat(str, Enum):
    RGB = "RGB"
    HSL = "HSL"


@strawberry.enum
class ScanDirection(str, Enum):
    ROW_COLUMN_SLICE = "row_column_slice"
    COLUMN_ROW_SLICE = "column_row_slice"
    SLICE_ROW_COLUMN = "slice_row_column"

    ROW_COLUMN_SLICE_SNAKE = "row_column_slice_snake"
    COLUMN_ROW_SLICE_SNAKE = "column_row_slice_snake"
    SLICE_ROW_COLUMN_SNAKE = "slice_row_column_snake"


@strawberry.enum(description="The kinds of OMERO object that can be the target of an annotation or link.")
class OmeroObjectType(str, Enum):
    PROJECT = "Project"
    DATASET = "Dataset"
    IMAGE = "Image"
    SCREEN = "Screen"
    PLATE = "Plate"
    WELL = "Well"
    PLATE_ACQUISITION = "PlateAcquisition"
    ROI = "Roi"
