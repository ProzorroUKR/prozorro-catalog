from datetime import datetime
from typing import Optional, List
from pydantic import Field, constr
from catalog.models.base import BaseModel
from catalog.models.common import OfferSuppliersAddress, OfferDeliveryAddress, ContactPoint, Identifier
from catalog.utils import get_now
from enum import Enum


class OfferStatus(str, Enum):
    active = 'active'
    hidden = 'hidden'


class Supplier(BaseModel):
    name: constr(max_length=250)
    scale: constr(max_length=50)
    address: OfferSuppliersAddress
    contactPoint: ContactPoint
    identifier: Identifier


class MinOrderValue(BaseModel):
    amount: float = Field(ge=0.01, le=999999999)
    currency: str = Field(..., regex=r"^[A-Z]{3}$")


class OfferValue(MinOrderValue):
    valueAddedTaxIncluded: bool = True


class Offer(BaseModel):
    id: str = Field(..., regex=r"^[0-9a-z]{32}$")
    relatedProduct: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    deliveryAddresses: List[OfferDeliveryAddress] = Field(..., min_items=1, max_items=100)
    status: OfferStatus
    suppliers: List[Supplier] = Field(..., min_items=1, max_items=1)
    value: OfferValue
    minOrderValue: Optional[MinOrderValue]
    comment: Optional[constr(max_length=250)]
    dateModified: datetime = Field(default_factory=lambda: get_now().isoformat())
    owner: str
