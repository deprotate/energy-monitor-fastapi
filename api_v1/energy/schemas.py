from typing import Annotated

from fastapi import Path
from pydantic import BaseModel


class CreateEnergy(BaseModel):
    type: Annotated[int, Path(title='1 - Consumed, 2- Generated', ge=1, le=2)]
    value: int

