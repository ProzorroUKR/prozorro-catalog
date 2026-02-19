from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from pydantic import Field

from catalog.models.api import Response
from catalog.models.base import BaseModel
from catalog.models.common import BidUnit
from catalog.utils import get_now


class Price(BaseModel):
    id: str = Field(
        ...,
        pattern=r"^[0-9A-Za-z_-]{1,32}$",
        json_schema_extra={"example": uuid4().hex},
    )
    productId: str = Field(
        ...,
        min_length=1,
        pattern=r"^[0-9A-Za-z_-]{1,32}$",
        json_schema_extra={"example": "some-product-id"},
    )
    unit: Optional[BidUnit] = Field(
        None,
        json_schema_extra={"example": {"code": "KGM", "name": "кілограм"}},
    )
    dateCreated: datetime = Field(
        default_factory=lambda: get_now().isoformat(),
        json_schema_extra={"example": "2024-01-15T10:00:00+02:00"},
    )
    dateModified: datetime = Field(
        default_factory=lambda: get_now().isoformat(),
        json_schema_extra={"example": "2024-01-15T12:30:00+02:00"},
    )
    sampleSize: int = Field(
        ...,
        ge=1,
        json_schema_extra={"example": 100},
    )
    lowerQuartile: Decimal = Field(
        ...,
        ge=0,
        json_schema_extra={"example": "10.50"},
    )
    medianQuartile: Decimal = Field(
        ...,
        ge=0,
        json_schema_extra={"example": "15.75"},
    )
    upperQuartile: Decimal = Field(
        ...,
        ge=0,
        json_schema_extra={"example": "22.00"},
    )


PriceResponse = Response[Price]
