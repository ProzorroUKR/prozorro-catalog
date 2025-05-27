from datetime import datetime
from typing import Optional, List, Union, Literal
from uuid import uuid4

from pydantic import Field, field_validator, StrictInt, StrictFloat, StrictBool, StrictStr

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
    uri: Optional[str] = Field(None, min_length=1, max_length=250, example="string")


class VendorProductIdentifier(BaseModel):
    id: str = Field(..., min_length=1, max_length=30)
    scheme: VendorProductIdentifierScheme = VendorProductIdentifierScheme.ean_13
    uri: Optional[str] = Field(None, min_length=1, max_length=250, example="string")


class VendorInfo(BaseModel):
    id: str = Field(..., min_length=1, max_length=250)
    name: str
    identifier: Identifier


class RequirementResponse(BaseModel):
    requirement: str
    value: Optional[Union[StrictInt, StrictFloat, StrictBool, StrictStr]] = Field(None, example="string")
    values: Optional[List[Union[StrictInt, StrictFloat, StrictBool, StrictStr]]] = Field(None, example=["string1", "string2"])


class ProductRequirementResponses(BaseModel):
    requirementResponses: Optional[List[RequirementResponse]] = Field(None, min_length=1, max_length=200, example=[{"requirement": "string", "value": 2}])

    @field_validator('requirementResponses')
    def unique_responses_ids(cls, v):
        if v:
            requirements = [e.requirement for e in v]
            if len(requirements) != len(set(requirements)):
                raise ValueError("not unique requirements")
        return v


class BaseProductCreateData(ProductRequirementResponses):
    title: str = Field(..., min_length=1, max_length=160)
    relatedCategory: str = Field(..., pattern=r"^[0-9A-Za-z_-]{1,32}$")
    description: Optional[str] = Field(None, min_length=1, max_length=1000, example="string")
    classification: Classification
    additionalClassifications: Optional[List[Classification]] = Field(None, max_length=100, example=[{
        "description": "description",
        "id": "33190000-8",
        "scheme": "ДК021"
    }])
    identifier: VendorProductIdentifier
    status: Literal[ProductStatus.active] = ProductStatus.active


class VendorProductCreateData(BaseProductCreateData):
    relatedProfiles: Optional[List[str]] = Field(None, min_length=1, max_length=1, example=[uuid4().hex,])

    @property
    def id(self):
        return uuid4().hex


class BaseProductData(BaseProductCreateData):
    identifier: Optional[ProductIdentifier] = Field(None, example={"id": "463234567819", "scheme": "UPC"})
    alternativeIdentifiers: Optional[List[ProductIdentifier]] = Field(None, max_length=100, example=[{"id": "463234567819", "scheme": "UPC"}])
    images: List[Image] = Field(None, max_length=20, example=[{"url": "/image/1.jpg"}])


class ProductCreateData(BaseProductData):
    @property
    def id(self):
        return uuid4().hex


class ProductUpdateData(ProductRequirementResponses):
    title: Optional[str] = Field(None, min_length=1, max_length=160, example="title")
    relatedCategory: Optional[str] = Field(None, pattern=r"^[0-9A-Za-z_-]{1,32}$", example="296917d994963ae6f8aaadaf3290bb80")
    description: Optional[str] = Field(None, min_length=1, max_length=1000, example="description")
    classification: Optional[Classification] = Field(None, example={
        "description": "description",
        "id": "33190000-8",
        "scheme": "ДК021"
    })
    additionalClassifications: Optional[List[Classification]] = Field(None, max_length=100, example=[{
        "description": "description",
        "id": "33190000-8",
        "scheme": "ДК021"
    }])
    identifier: Optional[ProductIdentifier] = Field(None, example={"id": "463234567819", "scheme": "UPC"})
    alternativeIdentifiers: Optional[List[ProductIdentifier]] = Field(None, max_length=100, example=[{"id": "463234567819", "scheme": "UPC"}])
    images: Optional[List[Image]] = Field(None, max_length=20, example=[{"url": "/image/1.jpg"}])
    status: Optional[ProductStatus] = Field(None, example=ProductStatus.inactive)


class LocalizationProductUpdateData(BaseModel):
    status: Optional[ProductStatus] = Field(None, example=ProductStatus.inactive)
    documents: Optional[List[DocumentPostData]] = Field(
        None,
        example=[{
            "id": uuid4().hex,
            "title": "name.doc",
            "url": "/documents/name.doc",
            "hash": f"md5:{uuid4().hex}",
            "format": "application/msword",
        }]
    )


class Product(BaseProductData):
    id: str = Field(..., pattern=r"^[0-9A-Za-z_-]{1,32}$")
    marketAdministrator: CategoryMarketAdministrator
    dateModified: datetime = Field(default_factory=lambda: get_now().isoformat())
    dateCreated: Optional[datetime] = Field(None, example=get_now().isoformat())
    relatedProfiles: Optional[List[str]] = Field(None, example=["string", ])
    owner: str
    vendor: Optional[VendorInfo] = Field(None, example={"id": "string", "name": "string", "identifier": {"id": "463234567819", "scheme": "UPC"}})
    documents: Optional[Document] = Field(
        None,
        example=[{
            "id": uuid4().hex,
            "title": "name.doc",
            "url": "/documents/name.doc",
            "hash": f"md5:{uuid4().hex}",
            "format": "application/msword",
        }]
    )
    images: Optional[List[Image]] = Field(None, max_length=100, example=[{"url": "/image/1.jpg"}])
    expirationDate: Optional[datetime] = Field(None, example=get_now().isoformat())


ProductCreateInput = AuthorizedInput[ProductCreateData]
VendorProductCreateInput = AuthorizedInput[VendorProductCreateData]
ProductUpdateInput = AuthorizedInput[Union[ProductUpdateData, LocalizationProductUpdateData]]
LocalizationProductUpdateInput = AuthorizedInput[LocalizationProductUpdateData]
ProductResponse = Response[Product]
ProductCreateResponse = CreateResponse[Product]
