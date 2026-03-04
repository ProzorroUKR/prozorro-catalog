from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import uuid4

from pydantic import Field

from catalog.models.api import Input, PageLink, Response
from catalog.models.base import BaseModel
from catalog.utils import get_now


class PriceCreateData(BaseModel):
    id: str = Field(
        ...,
        pattern=r"^[0-9A-Za-z_-]{1,32}$",
        json_schema_extra={"example": uuid4().hex},
    )
    productId: str = Field(
        ...,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "some-product-id"},
    )
    code: str = Field(
        ...,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "KGM"},
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "кілограм"},
    )
    date: datetime = Field(
        ...,
        json_schema_extra={"example": "2024-01-15T10:00:00+02:00"},
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
    dateCreated: datetime = Field(
        default_factory=lambda: get_now().isoformat(),
        json_schema_extra={"example": "2024-01-15T10:00:00+02:00"},
    )
    dateModified: datetime = Field(
        default_factory=lambda: get_now().isoformat(),
        json_schema_extra={"example": "2024-01-15T12:30:00+02:00"},
    )


class PriceUpdateData(BaseModel):
    productId: Optional[str] = Field(
        None,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "some-product-id"},
    )
    sampleSize: Optional[int] = Field(
        None,
        ge=1,
        json_schema_extra={"example": 100},
    )
    lowerQuartile: Optional[Decimal] = Field(
        None,
        ge=0,
        json_schema_extra={"example": "10.50"},
    )
    medianQuartile: Optional[Decimal] = Field(
        None,
        ge=0,
        json_schema_extra={"example": "15.75"},
    )
    upperQuartile: Optional[Decimal] = Field(
        None,
        ge=0,
        json_schema_extra={"example": "22.00"},
    )


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
    code: str = Field(
        ...,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "KGM"},
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "кілограм"},
    )
    date: datetime = Field(
        ...,
        json_schema_extra={"example": "2024-01-15T10:00:00+02:00"},
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


class PriceListItem(BaseModel):
    id: str
    productId: str
    code: str
    name: str
    date: str
    sampleSize: int
    lowerQuartile: Decimal
    medianQuartile: Decimal
    upperQuartile: Decimal
    dateCreated: str
    dateModified: str


class PaginatedPricesList(BaseModel):
    data: List[PriceListItem]
    next_page: PageLink
    prev_page: Optional[PageLink]

PriceCreateInput = Input[PriceCreateData]
PriceUpdateInput = Input[PriceUpdateData]
PriceResponse = Response[Price]
