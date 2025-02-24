from datetime import datetime
from typing import Optional, List
from pydantic import EmailStr, Field, validator, root_validator
from enum import Enum

from catalog.models.ban import Ban
from catalog.models.base import BaseModel
from catalog.models.api import Input, Response, CreateResponse, AuthorizedInput
from catalog.models.common import Identifier, Organization, ContactPoint, Address, ORA_CODES
from catalog.models.document import Document, DocumentSign


class VendorContactPoint(ContactPoint):
    email: EmailStr


class PostVendorAddress(Address):
    locality: Optional[str] = Field(None, min_length=1, max_length=80)
    postalCode: Optional[str] = Field(None, min_length=1, max_length=20)
    streetAddress: Optional[str] = Field(None, min_length=1, max_length=250)


class VendorAddress(PostVendorAddress):
    region: Optional[str] = Field(None, min_length=1, max_length=80)


class VendorIdentifier(Identifier):
    @validator("scheme")
    def scheme_standard(cls, v):
        if v not in ORA_CODES:
            raise ValueError("must be one of organizations/identifier_scheme.json codes")
        return v


class PostVendorOrganization(Organization):
    address: PostVendorAddress
    contactPoint: VendorContactPoint
    identifier: VendorIdentifier


class VendorOrganization(PostVendorOrganization):
    address: VendorAddress


class VendorPostData(BaseModel):
    vendor: PostVendorOrganization


class VendorPatchData(BaseModel):
    isActivated: Optional[bool]

    @validator('isActivated')
    def activation_only(cls, v, values, **kwargs):
        assert v is True, "activation is only allowed action"
        return v


class VendorStatus(str, Enum):
    pending = "pending"
    active = "active"
    banned = "banned"


class Vendor(VendorPostData):
    id: str = Field(..., min_length=32, max_length=32)
    vendor: VendorOrganization
    isActivated: bool = False
    dateModified: datetime
    dateCreated: datetime
    owner: str
    status: VendorStatus = VendorStatus.pending
    documents: List[Document]
    bans: Optional[List[Ban]]


class VendorSign(VendorPostData):
    vendor: VendorOrganization
    documents: List[DocumentSign]


VendorPostInput = Input[VendorPostData]
VendorPatchInput = AuthorizedInput[VendorPatchData]
VendorResponse = Response[Vendor]
VendorSignResponse = Response[VendorSign]
VendorCreateResponse = CreateResponse[Vendor]
