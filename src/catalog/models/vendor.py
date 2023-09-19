from datetime import datetime
from typing import Optional, List
from pydantic import Field, validator, root_validator
from enum import Enum

from catalog.models.base import BaseModel
from catalog.models.api import Input, Response, CreateResponse, AuthorizedInput
from catalog.models.common import Identifier, Organization, ContactPoint, Address, UKRAINE_COUNTRY_NAME_UK, ORA_CODES
from catalog.models.document import Document, DocumentSign


class CategoryLink(BaseModel):
    id: str = Field(..., min_length=20, max_length=32)


class VendorContactPoint(ContactPoint):
    email: str = Field(..., max_length=250)


class VendorAddress(Address):
    region: Optional[str] = Field(None, min_length=1, max_length=80)

    @root_validator
    def validate_address(cls, values):
        country_name = values.get("countryName")
        if country_name == UKRAINE_COUNTRY_NAME_UK and not values.get("region"):
            raise ValueError("region is required if countryName == 'Україна'")
        return values


class VendorIdentifier(Identifier):
    @validator("scheme")
    def scheme_standard(cls, v):
        if v not in ORA_CODES:
            raise ValueError("must be one of organizations/identifier_scheme.json codes")
        return v


class VendorOrganization(Organization):
    address: VendorAddress
    contactPoint: VendorContactPoint
    identifier: VendorIdentifier


class VendorPostData(BaseModel):
    vendor: VendorOrganization
    categories: List[CategoryLink] = Field(..., min_items=1, max_items=1)


class VendorPatchData(BaseModel):
    isActivated: Optional[bool]

    @validator('isActivated')
    def activation_only(cls, v, values, **kwargs):
        assert v is True, "activation is only allowed action"
        return v


class VendorStatus(str, Enum):
    pending = "pending"
    active = "active"


class Vendor(VendorPostData):
    id: str = Field(..., min_length=32, max_length=32)
    isActivated: bool = False
    dateModified: datetime
    dateCreated: datetime
    owner: str
    status: VendorStatus = VendorStatus.pending
    documents: List[Document]


class VendorSign(VendorPostData):
    vendor: VendorOrganization
    categories: List[CategoryLink]
    documents: List[DocumentSign]


VendorPostInput = Input[VendorPostData]
VendorPatchInput = AuthorizedInput[VendorPatchData]
VendorResponse = Response[Vendor]
VendorSignResponse = Response[VendorSign]
VendorCreateResponse = CreateResponse[Vendor]
