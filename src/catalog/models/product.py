from datetime import datetime
from typing import Optional, List, Union, Literal
from uuid import uuid4

from pydantic import Field, validator, constr, StrictInt, StrictFloat, StrictBool, StrictStr

from catalog.models.base import BaseModel
from catalog.models.api import Response, CreateResponse, AuthorizedInput
from catalog.models.common import (
    Image,
    Classification,
    Identifier,
    CategoryMarketAdministrator,
)
from catalog.models.document import Document, DocumentPostData
from catalog.utils import get_now
from enum import Enum


class ProductStatus(str, Enum):
    active = 'active'
    inactive = 'inactive'
    hidden = 'hidden'


class VendorProductIdentifierScheme(str, Enum):
    ean_13 = "EAN-13"


class ProductIdentifier(BaseModel):
    id: str = Field(..., min_length=1, max_length=250)
    scheme: str = Field(..., min_length=1, max_length=80)
    uri: Optional[str] = Field(None, min_length=1, max_length=250)


class VendorProductIdentifier(BaseModel):
    id: str = Field(..., min_length=1, max_length=30)
    scheme: VendorProductIdentifierScheme = VendorProductIdentifierScheme.ean_13
    uri: Optional[str] = Field(None, min_length=1, max_length=250)


class VendorInfo(BaseModel):
    id: str = Field(..., min_length=1, max_length=250)
    name: str
    identifier: Identifier


class RequirementResponse(BaseModel):
    requirement: str
    value: Optional[Union[StrictInt, StrictFloat, StrictBool, StrictStr]] = None
    values: Optional[List[Union[StrictInt, StrictFloat, StrictBool, StrictStr]]]


class ProductRequirementResponses(BaseModel):
    requirementResponses: Optional[List[RequirementResponse]] = Field(None, min_items=1, max_items=100)

    @validator('requirementResponses')
    def unique_responses_ids(cls, v):
        if v:
            requirements = [e.requirement for e in v]
            if len(requirements) != len(set(requirements)):
                raise ValueError("not unique requirements")
        return v


class BaseProductCreateData(ProductRequirementResponses):
    title: str = Field(..., min_length=1, max_length=160)
    # When we will have moved to new logic, we should remove max_items validation
    relatedCategory: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    classification: Classification
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)
    identifier: VendorProductIdentifier
    status: Literal[ProductStatus.active]


class VendorProductCreateData(BaseProductCreateData):
    relatedProfiles: Optional[List[str]] = Field(None, min_items=1, max_items=1)

    @property
    def id(self):
        return uuid4().hex


class BaseProductData(BaseProductCreateData):
    identifier: Optional[ProductIdentifier]
    alternativeIdentifiers: Optional[List[ProductIdentifier]] = Field(None, max_items=100)
    images: List[Image] = Field(None, max_items=20)


class ProductCreateData(BaseProductData):
    @property
    def id(self):
        return uuid4().hex


class ProductUpdateData(ProductRequirementResponses):
    title: Optional[str] = Field(None, min_length=1, max_length=160)
    relatedCategory: Optional[str] = Field(None, regex=r"^[0-9A-Za-z_-]{1,32}$")
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    classification: Optional[Classification]
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)
    identifier: Optional[ProductIdentifier]
    alternativeIdentifiers: Optional[List[ProductIdentifier]] = Field(None, max_items=100)
    images: Optional[List[Image]] = Field(None, max_items=20)
    status: Optional[ProductStatus]


class LocalizationProductUpdateData(BaseModel):
    status: Optional[ProductStatus]
    documents: Optional[List[DocumentPostData]]


class Product(BaseProductData):
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    marketAdministrator: CategoryMarketAdministrator
    dateModified: datetime = Field(default_factory=lambda: get_now().isoformat())
    dateCreated: Optional[datetime]
    relatedProfiles: Optional[List[str]]
    owner: str
    vendor: Optional[VendorInfo]
    documents: Optional[Document]
    images: Optional[List[Image]] = Field(None, max_items=100)
    expirationDate: Optional[datetime]


ProductCreateInput = AuthorizedInput[ProductCreateData]
VendorProductCreateInput = AuthorizedInput[VendorProductCreateData]
ProductUpdateInput = AuthorizedInput[ProductUpdateData]
LocalizationProductUpdateInput = AuthorizedInput[LocalizationProductUpdateData]
ProductResponse = Response[Product]
ProductCreateResponse = CreateResponse[Product]
