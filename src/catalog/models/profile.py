from datetime import datetime
from typing import Optional, List, Set, Union
from uuid import UUID
from pydantic import Field, validator, AnyUrl
from catalog.models.base import BaseModel
from catalog.models.api import Input, Response
from catalog.models.common import Unit, Value, Image, Criteria, Classification
from catalog.utils import get_now
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class ProfileStatus(str, Enum):
    active = 'active'
    hidden = 'hidden'
    deleted = 'general'


class ProfileCreateData(BaseModel):
    """
    The Catalog Profile Create Data
    """
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    title: str = Field(
        ...,
        title='Profile Name',
        description='Descriptive profile name',
        min_length=1,
        max_length=250,
    )
    description: str = Field(
        ...,
        title='Profile Description',
        description='Profile details',
        min_length=1,
        max_length=1000,
    )
    status: ProfileStatus = ProfileStatus.active
    unit: Unit
    value: Value
    relatedCategory: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    images: Optional[List[Image]] = Field(None, max_items=100)
    criteria: List[Criteria] = Field(..., min_items=1, max_items=100)
    classification: Classification
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)


class ProfileUpdateData(BaseModel):
    """
    The Catalog Profile Update Data
    """
    title: Optional[str] = Field(None, min_length=1, max_length=250)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    status: Optional[ProfileStatus]
    unit: Optional[Unit]
    value: Optional[Value]
    images: Optional[List[Image]] = Field(None, max_items=100)
    criteria: Optional[List[Criteria]] = Field(None, min_items=1, max_items=100)
    classification: Optional[Classification]
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)


class Profile(ProfileCreateData):
    """
    The Catalog Profile
    """
    dateModified: datetime = Field(default_factory=lambda: get_now().isoformat())


ProfileCreateInput = Input[ProfileCreateData]
ProfileUpdateInput = Input[ProfileUpdateData]
ProfileResponse = Response[Profile]
