from datetime import datetime
from typing import Optional

from pydantic import Field

from catalog.models.api import Response
from catalog.models.base import BaseModel
from catalog.models.common import BidUnit, Classification
from catalog.utils import get_now

BID_UNIT_EXAMPLE = BidUnit(code="KGM", name="кілограм", value=150.00, quantity=10.00).model_dump(exclude_none=True)

CLASSIFICATION_EXAMPLE = Classification(
    id="33600000-6", scheme="ДК021", description="Фармацевтична продукція"
).model_dump(exclude_none=True)


class ProductBid(BaseModel):
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
    itemClassification: Classification = Field(
        ...,
        json_schema_extra={"example": CLASSIFICATION_EXAMPLE},
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


ProductBidResponse = Response[ProductBid]
