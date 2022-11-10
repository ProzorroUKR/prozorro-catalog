from datetime import datetime
from typing import Optional, List, Union
from pydantic import Field, validator, constr, StrictInt, StrictFloat, StrictBool, StrictStr

from catalog.models.base import BaseModel
from catalog.models.api import Response, CreateResponse, AuthorizedInput
from catalog.models.common import Image, Classification, Address, ContactPoint, Identifier
from catalog.models.document import Document
from catalog.utils import get_now
from enum import Enum


class ProductStatus(str, Enum):
    active = 'active'
    hidden = 'hidden'


class VendorProductIdentifierScheme(str, Enum):
    ean_13 = "EAN-13"


class ProductProperty(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    code: str = Field(..., min_length=1, max_length=80)
    value: Union[StrictStr, StrictFloat, StrictInt, StrictBool]


class ProductIdentifier(BaseModel):
    id: str = Field(..., min_length=1, max_length=250)
    scheme: str = Field(..., min_length=1, max_length=80)
    uri: Optional[str] = Field(None, min_length=1, max_length=250)


class VendorProductIdentifier(BaseModel):
    id: str = Field(..., min_length=1, max_length=30)
    scheme: VendorProductIdentifierScheme = VendorProductIdentifierScheme.ean_13
    uri: Optional[str] = Field(None, min_length=1, max_length=250)


class Brand(BaseModel):
    name: constr(min_length=1, max_length=250)
    uri: constr(max_length=250)
    alternativeNames: Optional[List[constr(max_length=250)]]


class VendorProductBrand(Brand):
    uri: Optional[constr(max_length=250)]


class Manufacturer(BaseModel):
    name: constr(max_length=250)
    address: Address
    contactPoint: ContactPoint
    identifier: Identifier


class VendorInfo(BaseModel):
    id: str = Field(..., min_length=1, max_length=250)
    name: str
    identifier: Identifier


class ProductInfo(BaseModel):
    name: constr(min_length=1, max_length=250)
    uri: Optional[constr(max_length=250)]
    alternativeNames: Optional[List[constr(max_length=250)]]


class RequirementResponse(BaseModel):
    requirement: str
    value: Optional[Union[StrictInt, StrictFloat, StrictBool, StrictStr]] = None
    values: List[Union[StrictInt, StrictFloat, StrictBool, StrictStr]] = Field(None, max_items=100)


class ProductRequirementResponses(BaseModel):
    requirementResponses: Optional[List[RequirementResponse]] = Field(None, max_items=100)

    @validator('requirementResponses')
    def unique_responses_ids(cls, v):
        if v:
            requirements = [e.requirement for e in v]
            if len(requirements) != len(set(requirements)):
                raise ValueError("not unique requirements")
        return v


class VendorProductCreateData(ProductRequirementResponses):
    title: str = Field(..., min_length=1, max_length=80)
    # When we will have moved to new logic, we should remove max_items validation
    relatedProfiles: List[str] = Field(..., min_items=1, max_items=1)
    description: str = Field(..., min_length=1, max_length=1000)
    classification: Classification
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)
    identifier: VendorProductIdentifier
    brand: VendorProductBrand
    product: ProductInfo
    status: ProductStatus = ProductStatus.active


class ProductCreateData(VendorProductCreateData):
    additionalProperties: Optional[List[ProductProperty]] = Field(None, max_items=100)
    identifier: ProductIdentifier
    alternativeIdentifiers: Optional[List[ProductIdentifier]] = Field(None, max_items=100)
    manufacturers: Optional[List[Manufacturer]] = Field(None, max_items=100)
    images: Optional[List[Image]] = Field(None, max_items=100)


class ProductUpdateData(ProductRequirementResponses):
    title: Optional[str] = Field(None, min_length=1, max_length=80)
    relatedProfiles: Optional[List[str]] = Field(None, max_items=1)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    classification: Optional[Classification]
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)
    additionalProperties: Optional[List[ProductProperty]] = Field(None, max_items=100)
    identifier: Optional[ProductIdentifier]
    alternativeIdentifiers: Optional[List[ProductIdentifier]] = Field(None, max_items=100)
    brand: Optional[Brand]
    product: Optional[ProductInfo]
    manufacturers: Optional[List[Manufacturer]] = Field(None, max_items=100)
    images: Optional[List[Image]] = Field(None, max_items=100)
    status: Optional[ProductStatus]


class Product(ProductCreateData):
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    dateModified: datetime = Field(default_factory=lambda: get_now().isoformat())
    owner: str
    vendor: Optional[VendorInfo]
    documents: Optional[Document]


ProductCreateInput = AuthorizedInput[ProductCreateData]
VendorProductCreateInput = AuthorizedInput[VendorProductCreateData]
ProductUpdateInput = AuthorizedInput[ProductUpdateData]
ProductResponse = Response[Product]
ProductCreateResponse = CreateResponse[Product]
