from bridge.conn import get_conn
from bridge import types, filters, inputs
from strawberry_django import pagination
import strawberry
from kante.types import Info
from ezomero import post_dataset

def create_dataset(info: Info, input: inputs.CreateDatasetInput) -> types.Dataset:
    con = get_conn()
    id = post_dataset(con, dataset_name=input.name, project_id=int(input.project_id), description=input.description)
    project = get_conn().getObject("Dataset", id)
    return types.Dataset(value=project)