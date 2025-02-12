from datetime import datetime
from typing import Annotated

from fastapi import Path
from pydantic import BaseModel, field_serializer


class CreateEnergy(BaseModel):
    type: Annotated[int, Path(title='1 - Consumed, 2- Generated', ge=1, le=2)]
    value: int


class EnergySchema(BaseModel):
    id: int
    type: int
    value: float
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime, _info) -> str:
        return value.strftime("%d.%m.%Y in %H.%M.%S")
