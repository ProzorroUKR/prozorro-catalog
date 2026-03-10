from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import uuid4

from pydantic import Field

from catalog.models.api import Input, Response
from catalog.models.base import BaseModel
from catalog.utils import get_now


class BaseProductBidData(BaseModel):
    id: str = Field(
        ...,
        pattern=r"^[0-9A-Za-z_-]{1,32}$",
        json_schema_extra={"example": "a1b2c3d4e5f6"},
    )
    tenderId: str = Field(
        ...,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "tender-id-001"},
    )
    bidId: str = Field(
        ...,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "bid-id-001"},
    )
    itemId: str = Field(
        ...,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "item-id-001"},
    )
    productId: Optional[str] = Field(
        None,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "catalog-product-id-001"},
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
    amount: Decimal = Field(
        ...,
        ge=0,
        json_schema_extra={"example": "100.50"},
    )
    date: datetime = Field(
        ...,
        json_schema_extra={"example": "2024-01-15T10:00:00+02:00"},
    )
    dateModified: datetime = Field(
        default_factory=lambda: get_now().isoformat(),
        json_schema_extra={"example": "2024-01-15T12:30:00+02:00"},
    )
    dateCreated: datetime = Field(
        default_factory=lambda: get_now().isoformat(),
        json_schema_extra={"example": "2024-01-15T10:00:00+02:00"},
    )


class ProductBidCreateData(BaseProductBidData):
    @property
    def id(self):
        return uuid4().hex


class ProductBidUpdateData(BaseModel):
    tenderId: Optional[str] = Field(
        None,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "tender-id-001"},
    )
    bidId: Optional[str] = Field(
        None,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "bid-id-001"},
    )
    itemId: Optional[str] = Field(
        None,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "item-id-001"},
    )
    productId: Optional[str] = Field(
        None,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "catalog-product-id-001"},
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
    amount: Decimal = Field(
        ...,
        ge=0,
        json_schema_extra={"example": "100.50"},
    )
    date: Optional[datetime] = Field(
        None,
        json_schema_extra={"example": "2024-01-15T10:00:00+02:00"},
    )


class ProductBid(BaseProductBidData):
    id: str = Field(
        ...,
        pattern=r"^[0-9A-Za-z_-]{1,32}$",
        json_schema_extra={"example": "a1b2c3d4e5f6"},
    )
    tenderId: str = Field(
        ...,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "tender-id-001"},
    )
    bidId: str = Field(
        ...,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "bid-id-001"},
    )
    itemId: str = Field(
        ...,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "item-id-001"},
    )
    productId: Optional[str] = Field(
        None,
        min_length=1,
        max_length=250,
        json_schema_extra={"example": "catalog-product-id-001"},
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
    amount: Decimal = Field(
        ...,
        ge=0,
        json_schema_extra={"example": "100.50"},
    )
    date: datetime = Field(
        ...,
        json_schema_extra={"example": "2024-01-15T10:00:00+02:00"},
    )
    dateModified: datetime = Field(
        default_factory=lambda: get_now().isoformat(),
        json_schema_extra={"example": "2024-01-15T12:30:00+02:00"},
    )
    dateCreated: datetime = Field(
        default_factory=lambda: get_now().isoformat(),
        json_schema_extra={"example": "2024-01-15T10:00:00+02:00"},
    )


ProductBidCreateInput = Input[ProductBidCreateData]
ProductBidUpdateInput = Input[ProductBidUpdateData]
ProductBidResponse = Response[ProductBid]
