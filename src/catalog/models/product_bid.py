from datetime import datetime
from typing import Optional
from uuid import uuid4

from pydantic import Field

from catalog.models.api import Input, Response
from catalog.models.base import BaseModel
from catalog.models.common import BID_UNIT_EXAMPLE, BidUnit
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
    unit: BidUnit = Field(
        ...,
        json_schema_extra={"example": BID_UNIT_EXAMPLE},
    )
    date: datetime = Field(
        ...,
        json_schema_extra={"example": "2024-01-15T10:00:00+02:00"},
    )
    lotValueStatus: str = Field(
        ...,
        min_length=1,
        max_length=80,
        json_schema_extra={"example": "active"},
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
    unit: Optional[BidUnit] = Field(
        None,
        json_schema_extra={"example": BID_UNIT_EXAMPLE},
    )
    date: Optional[datetime] = Field(
        None,
        json_schema_extra={"example": "2024-01-15T10:00:00+02:00"},
    )
    lotValueStatus: Optional[str] = Field(
        None,
        min_length=1,
        max_length=80,
        json_schema_extra={"example": "active"},
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
    unit: BidUnit = Field(
        ...,
        json_schema_extra={"example": BID_UNIT_EXAMPLE},
    )
    date: datetime = Field(
        ...,
        json_schema_extra={"example": "2024-01-15T10:00:00+02:00"},
    )
    lotValueStatus: str = Field(
        ...,
        min_length=1,
        max_length=80,
        json_schema_extra={"example": "active"},
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
