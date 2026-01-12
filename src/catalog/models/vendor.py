from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import EmailStr, Field, field_validator

from catalog.models.api import AuthorizedInput, CreateResponse, Input, Response
from catalog.models.ban import BAN_EXAMPLE, Ban
from catalog.models.base import BaseModel
from catalog.models.common import ORA_CODES, Address, ContactPoint, Identifier, Organization
from catalog.models.document import Document, DocumentSign


class VendorContactPoint(ContactPoint):
    email: EmailStr


class PostVendorAddress(Address):
    locality: Optional[str] = Field(None, min_length=1, max_length=80, json_schema_extra={"example": "string"})
    postalCode: Optional[str] = Field(None, min_length=1, max_length=20, json_schema_extra={"example": "string"})
    streetAddress: Optional[str] = Field(None, min_length=1, max_length=250, json_schema_extra={"example": "string"})


class VendorAddress(PostVendorAddress):
    region: Optional[str] = Field(None, min_length=1, max_length=80, json_schema_extra={"example": "string"})


class VendorIdentifier(Identifier):
    @field_validator("scheme")
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
    isActivated: Optional[bool] = Field(None, json_schema_extra={"example": True})

    @field_validator("isActivated")
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
    bans: Optional[List[Ban]] = Field(None, json_schema_extra={"example": [BAN_EXAMPLE]})


class VendorSign(VendorPostData):
    vendor: VendorOrganization
    documents: List[DocumentSign]


VendorPostInput = Input[VendorPostData]
VendorPatchInput = AuthorizedInput[VendorPatchData]
VendorResponse = Response[Vendor]
VendorSignResponse = Response[VendorSign]
VendorCreateResponse = CreateResponse[Vendor]
