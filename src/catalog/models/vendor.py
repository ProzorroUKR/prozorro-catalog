from datetime import datetime
from typing import Optional, List
from pydantic import Field, validator
from catalog.models.base import BaseModel
from catalog.models.api import Input, Response, CreateResponse, AuthorizedInput
from catalog.models.common import Organization, ContactPoint


class CategoryLink(BaseModel):
    id: str = Field(..., min_length=20, max_length=32)


class VendorContactPoint(ContactPoint):
    email: str = Field(..., max_length=250)


class VendorOrganization(Organization):
    contactPoint: VendorContactPoint


class VendorPostData(BaseModel):
    vendor: VendorOrganization
    categories: List[CategoryLink] = Field(..., min_items=1, max_items=1)


class VendorPatchData(BaseModel):
    isActive: Optional[bool]

    @validator('isActive')
    def activation_only(cls, v, values, **kwargs):
        assert v is True, "activation is only allowed action"
        return v


class Vendor(VendorPostData):
    id: str = Field(..., min_length=32, max_length=32)
    isActive: bool = False
    dateModified: datetime
    dateCreated: datetime
    owner: str


VendorPostInput = Input[VendorPostData]
VendorPatchInput = AuthorizedInput[VendorPatchData]
VendorResponse = Response[Vendor]
VendorCreateResponse = CreateResponse[Vendor]
