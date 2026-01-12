from datetime import datetime
from enum import Enum
from typing import List, Literal, Optional, Union
from uuid import uuid4

from pydantic import Field, StrictBool, StrictFloat, StrictInt, StrictStr, field_validator

from catalog.models.api import AuthorizedInput, CreateResponse, Response
from catalog.models.base import BaseModel
from catalog.models.common import (
    CLASSIFICATION_EXAMPLE,
    CategoryMarketAdministrator,
    Classification,
    Identifier,
    Image,
)
from catalog.models.document import DOCUMENT_EXAMPLE, Document, DocumentPostData
from catalog.settings import TIMEZONE
from catalog.utils import get_now


class ProductStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    hidden = "hidden"


class VendorProductIdentifierScheme(str, Enum):
    ean_13 = "EAN-13"


class ProductIdentifier(BaseModel):
    id: str = Field(..., min_length=1, max_length=250)
    scheme: str = Field(..., min_length=1, max_length=80)
    uri: Optional[str] = Field(None, min_length=1, max_length=250, json_schema_extra={"example": "string"})


IDENTIFIER_EXAMPLE = ProductIdentifier(id="463234567819", scheme="UPC").model_dump(exclude_none=True)


class VendorProductIdentifier(BaseModel):
    id: str = Field(..., min_length=1, max_length=30)
    scheme: VendorProductIdentifierScheme = VendorProductIdentifierScheme.ean_13
    uri: Optional[str] = Field(None, min_length=1, max_length=250, json_schema_extra={"example": "string"})


class VendorInfo(BaseModel):
    id: str = Field(..., min_length=1, max_length=250)
    name: str
    identifier: Identifier


VENDOR_INFO_EXAMPLE = VendorInfo(
    id="string", name="string", identifier=Identifier(id="463234567819", scheme="UPC", legalName="string")
).model_dump(exclude_none=True)


class RequirementResponse(BaseModel):
    requirement: str
    value: Optional[Union[StrictInt, StrictFloat, StrictBool, StrictStr]] = Field(
        None,
        json_schema_extra={"example": "string"},
    )
    values: Optional[List[Union[StrictInt, StrictFloat, StrictBool, StrictStr]]] = Field(
        None,
        json_schema_extra={"example": ["string1", "string2"]},
    )


class ProductRequirementResponses(BaseModel):
    requirementResponses: Optional[List[RequirementResponse]] = Field(
        None,
        min_length=1,
        max_length=200,
        json_schema_extra={"example": [{"requirement": "string", "value": 2}]},
    )

    @field_validator("requirementResponses")
    def unique_responses_ids(cls, v):
        if v:
            requirements = [e.requirement for e in v]
            if len(requirements) != len(set(requirements)):
                raise ValueError("not unique requirements")
        return v


class BaseProductCreateData(ProductRequirementResponses):
    title: str = Field(..., min_length=1, max_length=160)
    relatedCategory: str = Field(..., pattern=r"^[0-9A-Za-z_-]{1,32}$")
    description: Optional[str] = Field(None, min_length=1, max_length=1000, json_schema_extra={"example": "string"})
    classification: Classification
    additionalClassifications: Optional[List[Classification]] = Field(
        None,
        max_length=100,
        json_schema_extra={"example": [CLASSIFICATION_EXAMPLE]},
    )
    identifier: VendorProductIdentifier
    status: Literal[ProductStatus.active] = ProductStatus.active


class VendorProductCreateData(BaseProductCreateData):
    relatedProfiles: Optional[List[str]] = Field(
        None,
        min_length=1,
        max_length=1,
        json_schema_extra={
            "example": [
                uuid4().hex,
            ]
        },
    )

    @property
    def id(self):
        return uuid4().hex


class BaseProductData(BaseProductCreateData):
    identifier: Optional[ProductIdentifier] = Field(None, json_schema_extra={"example": IDENTIFIER_EXAMPLE})
    alternativeIdentifiers: Optional[List[ProductIdentifier]] = Field(
        None,
        max_length=100,
        json_schema_extra={"example": [IDENTIFIER_EXAMPLE]},
    )
    images: Optional[List[Image]] = Field(None, max_length=20, json_schema_extra={"example": [{"url": "/image/1.jpg"}]})
    expirationDate: Optional[datetime] = Field(None, json_schema_extra={"example": get_now().isoformat()})

    @field_validator("expirationDate")
    def validate_date(cls, v):
        if v and isinstance(v, datetime):
            if not v.tzinfo:
                v = v.replace(tzinfo=TIMEZONE)
            if v < get_now():
                raise ValueError("should be greater than now")
            return v.isoformat()


class ProductCreateData(BaseProductData):
    @property
    def id(self):
        return uuid4().hex


class BaseProductUpdateData(ProductRequirementResponses):
    title: Optional[str] = Field(None, min_length=1, max_length=160, json_schema_extra={"example": "title"})
    relatedCategory: Optional[str] = Field(
        None,
        pattern=r"^[0-9A-Za-z_-]{1,32}$",
        json_schema_extra={"example": uuid4().hex},
    )
    description: Optional[str] = Field(
        None,
        min_length=1,
        max_length=1000,
        json_schema_extra={"example": "description"},
    )
    classification: Optional[Classification] = Field(None, json_schema_extra={"example": CLASSIFICATION_EXAMPLE})
    additionalClassifications: Optional[List[Classification]] = Field(
        None,
        max_length=100,
        json_schema_extra={"example": [CLASSIFICATION_EXAMPLE]},
    )
    identifier: Optional[ProductIdentifier] = Field(None, json_schema_extra={"example": IDENTIFIER_EXAMPLE})
    alternativeIdentifiers: Optional[List[ProductIdentifier]] = Field(
        None,
        max_length=100,
        json_schema_extra={"example": [IDENTIFIER_EXAMPLE]},
    )
    images: Optional[List[Image]] = Field(None, max_length=20, json_schema_extra={"example": [{"url": "/image/1.jpg"}]})
    status: Optional[ProductStatus] = Field(None, json_schema_extra={"example": ProductStatus.inactive})


class ProductUpdateData(BaseProductUpdateData):
    expirationDate: Optional[datetime] = Field(None, json_schema_extra={"example": get_now().isoformat()})

    @field_validator("expirationDate")
    def validate_date(cls, v):
        if v and isinstance(v, datetime):
            if not v.tzinfo:
                v = v.replace(tzinfo=TIMEZONE)
            if v < get_now():
                raise ValueError("should be greater than now")
            return v.isoformat()


class LocalizationProductUpdateData(BaseModel):
    status: Optional[ProductStatus] = Field(None, json_schema_extra={"example": ProductStatus.inactive})
    documents: Optional[List[DocumentPostData]] = Field(None, json_schema_extra={"example": [DOCUMENT_EXAMPLE]})


class Product(BaseProductData):
    id: str = Field(..., pattern=r"^[0-9A-Za-z_-]{1,32}$")
    marketAdministrator: CategoryMarketAdministrator
    dateModified: datetime = Field(default_factory=lambda: get_now().isoformat())
    dateCreated: Optional[datetime] = Field(None, json_schema_extra={"example": get_now().isoformat()})
    relatedProfiles: Optional[List[str]] = Field(
        None,
        json_schema_extra={
            "example": [
                "string",
            ]
        },
    )
    owner: str
    vendor: Optional[VendorInfo] = Field(None, json_schema_extra={"example": VENDOR_INFO_EXAMPLE})
    documents: Optional[Document] = Field(None, json_schema_extra={"example": [DOCUMENT_EXAMPLE]})
    images: Optional[List[Image]] = Field(
        None,
        max_length=100,
        json_schema_extra={"example": [{"url": "/image/1.jpg"}]},
    )


ProductCreateInput = AuthorizedInput[ProductCreateData]
VendorProductCreateInput = AuthorizedInput[VendorProductCreateData]
ProductUpdateInput = AuthorizedInput[Union[ProductUpdateData, LocalizationProductUpdateData]]
LocalizationProductUpdateInput = AuthorizedInput[LocalizationProductUpdateData]
ProductResponse = Response[Product]
ProductCreateResponse = CreateResponse[Product]
