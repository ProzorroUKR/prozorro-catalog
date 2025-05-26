from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from pydantic import Field, validator
from catalog.models.base import BaseModel
from catalog.models.api import Input, AuthorizedInput, Response, CreateResponse
from catalog.models.common import Classification, Image, CategoryMarketAdministrator, Unit, AGREEMENT_ID_REGEX
from catalog.models.criteria import Criterion
from catalog.utils import get_now
from enum import Enum


class CategoryStatus(str, Enum):
    active = "active"
    hidden = "hidden"


class BaseCategoryCreateData(BaseModel):
    classification: Classification
    marketAdministrator: CategoryMarketAdministrator
    title: str = Field(..., min_length=1, max_length=80)
    unit: Unit
    description: Optional[str] = Field(None, min_length=1, max_length=1000, example="string")
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100, example=[{
        "description": "description",
        "id": "33190000-8",
        "scheme": "ДК021"
    }])
    status: CategoryStatus = CategoryStatus.active
    images: Optional[List[Image]] = Field(None, max_items=100, example=[{"url": "/image/1.jpg"}])
    agreementID: Optional[str] = Field(None, pattern=AGREEMENT_ID_REGEX, example="string")

    @property
    def criteria(self):
        return []


class CategoryCreateData(BaseCategoryCreateData):
    @property
    def id(self):
        return uuid4().hex


class DeprecatedCategoryCreateData(BaseCategoryCreateData):
    """
    Deprecated soon the Catalog Category Create Data with required id and creation via PUT method
    """
    id: str = Field(..., pattern=r"^[0-9A-Za-z_-]{20,32}$")

    @validator('id')
    def id_format(cls, v, values, **kwargs):
        """
        instead of generating id, we ask user to pass through all these validations
        """
        if "classification" in values and values["classification"].id[:8] not in v:
            raise ValueError('id must include cpv')
        if "marketAdministrator" in values and values["marketAdministrator"].identifier.id not in v:
            raise ValueError('id must include edr')
        return v


class CategoryUpdateData(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=80, example="string")
    unit: Optional[Unit] = Field(None, example={"code": "string", "name": "string"})
    description: Optional[str] = Field(None, min_length=1, max_length=1000, example="string")
    status: Optional[CategoryStatus] = Field(None, example=CategoryStatus.active)
    images: Optional[List[Image]] = Field(None, max_items=100, example=[{"url": "/image/1.jpg"}])
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100, example=[{
        "description": "description",
        "id": "33190000-8",
        "scheme": "ДК021"
    }])
    agreementID: Optional[str] = Field(None, pattern=AGREEMENT_ID_REGEX, example="string")


class Category(BaseModel):
    """
    The Catalog Profile
    """
    classification: Classification
    marketAdministrator: CategoryMarketAdministrator
    id: str = Field(..., pattern=r"^[0-9A-Za-z_-]{20,32}$")
    title: Optional[str] = Field(..., min_length=1, max_length=80, example="title")
    unit: Unit
    description: Optional[str] = Field(..., min_length=1, max_length=1000, example="description")
    additionalClassifications: Optional[List[Classification]] = Field(..., max_items=100)
    status: CategoryStatus = CategoryStatus.active
    images: Optional[List[Image]] = Field(..., max_items=100)
    dateModified: datetime = Field(default_factory=lambda: get_now().isoformat())
    criteria: List[Criterion] = Field(...)
    agreementID: Optional[str] = Field(None, pattern=AGREEMENT_ID_REGEX, example="string")
    owner: str


CategoryCreateInput = Input[CategoryCreateData]
DeprecatedCategoryCreateInput = Input[DeprecatedCategoryCreateData]
CategoryUpdateInput = AuthorizedInput[CategoryUpdateData]
CategoryResponse = Response[Category]
CategoryCreateResponse = CreateResponse[Category]
