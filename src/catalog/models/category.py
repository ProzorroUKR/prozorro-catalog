from datetime import datetime
from typing import Optional, List
from pydantic import Field, validator
from catalog.models.base import BaseModel
from catalog.models.api import Input, AuthorizedInput, Response, CreateResponse
from catalog.models.common import Classification, Image, ProcuringEntity, Unit, AGREEMENT_ID_REGEX
from catalog.models.criteria import Criterion
from catalog.utils import get_now
from enum import Enum


class CategoryStatus(str, Enum):
    active = "active"
    hidden = "hidden"
    deleted = "deleted"


class CategoryCreateData(BaseModel):
    classification: Classification
    procuringEntity: ProcuringEntity
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{20,32}$")
    title: Optional[str] = Field(None, min_length=1, max_length=80)
    unit: Optional[Unit]
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)
    status: CategoryStatus = CategoryStatus.active
    images: Optional[List[Image]] = Field(None, max_items=100)
    agreementID: Optional[str] = Field(None, regex=AGREEMENT_ID_REGEX)

    @validator('id')
    def id_format(cls, v, values, **kwargs):
        """
        instead of generating id, we ask user to pass through all these validations
        """
        if "classification" in values and values["classification"].id[:8] not in v:
            raise ValueError('id must include cpv')
        if "procuringEntity" in values and values["procuringEntity"].identifier.id not in v:
            raise ValueError('id must include edr')
        return v

    @property
    def criteria(self):
        return []


class CategoryUpdateData(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=80)
    unit: Optional[Unit]
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    status: Optional[CategoryStatus]
    images: Optional[List[Image]] = Field(None, max_items=100)
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)
    agreementID: Optional[str] = Field(None, regex=AGREEMENT_ID_REGEX)


class Category(BaseModel):
    """
    The Catalog Profile
    """
    classification: Classification
    procuringEntity: ProcuringEntity
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{20,32}$")
    title: Optional[str] = Field(..., min_length=1, max_length=80)
    unit: Unit
    description: Optional[str] = Field(..., min_length=1, max_length=1000)
    additionalClassifications: Optional[List[Classification]] = Field(..., max_items=100)
    status: CategoryStatus = CategoryStatus.active
    images: Optional[List[Image]] = Field(..., max_items=100)
    dateModified: datetime = Field(default_factory=lambda: get_now().isoformat())
    criteria: List[Criterion] = Field(..., max_items=1)
    agreementID: Optional[str] = Field(None, regex=AGREEMENT_ID_REGEX)
    owner: str


CategoryCreateInput = Input[CategoryCreateData]
CategoryUpdateInput = AuthorizedInput[CategoryUpdateData]
CategoryResponse = Response[Category]
CategoryCreateResponse = CreateResponse[Category]
