from datetime import datetime
from typing import Optional, List
from pydantic import Field, validator, constr
from catalog.models.base import BaseModel
from catalog.models.api import Input, Response, CreateResponse, AuthorizedInput
from catalog.models.common import OfferSuppliersAddress, OfferDeliveryAddress, ContactPoint, Identifier
from catalog.utils import get_now
from enum import Enum
import standards


SCALE_STANDARD = standards.load("organizations/scale.json")
CURRENCIES_STANDARD = standards.load("codelists/tender/tender_currency.json")


class OfferStatus(str, Enum):
    active = 'active'
    hidden = 'hidden'


class Supplier(BaseModel):
    name: constr(max_length=250)
    scale: constr(max_length=50)
    address: OfferSuppliersAddress
    contactPoint: ContactPoint
    identifier: Identifier

    @validator('scale')
    def scale_standard(cls, v):
        if v not in SCALE_STANDARD.keys():
            raise ValueError("must be one of organizations/scale.json keys")
        return v


class MinOrderValue(BaseModel):
    amount: float = Field(ge=0.01, le=999999999)
    currency: str = Field(..., regex=r"^[A-Z]{3}$")

    @validator('currency')
    def currency_standard(cls, v):
        if v not in CURRENCIES_STANDARD.keys():
            raise ValueError("must be one of codelists/tender/tender_currency.json keys")
        return v


class OfferValue(MinOrderValue):
    valueAddedTaxIncluded: bool = True


class OfferCreateData(BaseModel):
    id: str = Field(..., regex=r"^[0-9a-z]{32}$")
    relatedProduct: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    deliveryAddresses: List[OfferDeliveryAddress] = Field(..., min_items=1, max_items=100)
    status: OfferStatus
    suppliers: List[Supplier] = Field(..., min_items=1, max_items=1)
    value: OfferValue
    minOrderValue: Optional[MinOrderValue]
    comment: Optional[constr(max_length=250)]


class OfferUpdateData(BaseModel):
    deliveryAddresses: Optional[List[OfferDeliveryAddress]] = Field(None, min_items=1, max_items=100)
    status: Optional[OfferStatus]
    suppliers: Optional[List[Supplier]] = Field(None, min_items=1, max_items=1)
    value: Optional[OfferValue]
    minOrderValue: Optional[MinOrderValue]
    comment: Optional[constr(max_length=250)]


class Offer(OfferCreateData):
    dateModified: datetime = Field(default_factory=lambda: get_now().isoformat())
    owner: str

    @staticmethod
    def validate_offer(data):  # TODO redesign this ?
        if 'minOrderValue' in data:
            if data['minOrderValue']['amount'] < data['value']['amount']:
                raise ValueError('minOrderValue.amount mismatch')
            if data['minOrderValue']['currency'] != data['value']['currency']:
                raise ValueError('minOrderValue.currency mismatch')


OfferCreateInput = Input[OfferCreateData]
OfferUpdateInput = AuthorizedInput[OfferUpdateData]
OfferResponse = Response[Offer]
OfferCreateResponse = CreateResponse[Offer]
