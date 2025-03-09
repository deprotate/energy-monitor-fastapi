from datetime import datetime
from typing import Annotated, Literal
from fastapi import Path, Query
from pydantic import BaseModel, field_serializer, Field


class CreateEnergy(BaseModel):
    type: Annotated[int, Field(title='1 - Consumed, 2- Generated', ge=1, le=2, examples=[1,2])]
    value: Annotated[int, Field(title='value', ge=0, examples=[1000])]


class EnergyResponse(BaseModel):
    id: int
    type: int
    value: float
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime, _info) -> str:
        return value.strftime("%d.%m.%Y in %H.%M.%S")


class PredictIn(BaseModel):
    start_date: Annotated[str, Field(examples=["2025-12-31"])] = "2025-12-31"
    end_date: Annotated[str, Field(examples=["2026-10-15"])] = "2026-10-15"
    longitude: Annotated[float, Field(examples=[37.62])] = 37.62
    latitude: Annotated[float, Field(examples=[55.75])] = 55.75
    group_by: Annotated[Literal["day", "month", "year"] | None, Field(title="Group periods by day/month/year" )] = None