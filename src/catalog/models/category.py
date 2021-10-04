from datetime import datetime
from typing import Optional, List, Set, Union, Any
from uuid import UUID
from pydantic import Field, validator, AnyUrl
from catalog.models.base import BaseModel
from catalog.models.api import Input, Response
from catalog.models.common import Classification, Image, ProcuringEntity
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
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)
    status: CategoryStatus = CategoryStatus.active
    images: Optional[List[Image]] = Field(None, max_items=100)

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


class CategoryUpdateData(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=80)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    status: Optional[CategoryStatus]
    images: Optional[List[Image]] = Field(None, max_items=100)
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)


class Category(CategoryCreateData):
    """
    The Catalog Profile
    """
    dateModified: datetime = Field(default_factory=lambda: get_now().isoformat())


CategoryCreateInput = Input[CategoryCreateData]
CategoryUpdateInput = Input[CategoryUpdateData]
CategoryResponse = Response[Category]
