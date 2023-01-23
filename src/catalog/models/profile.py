from datetime import datetime
from typing import Optional, List, Set, Union
from uuid import UUID
from pydantic import Field, validator, AnyUrl
from catalog.models.base import BaseModel
from catalog.models.api import Response, CreateResponse, AuthorizedInput
from catalog.models.common import Unit, Value, Image, Classification
from catalog.models.criteria import Criterion
from catalog.utils import get_now
from enum import Enum
import re
import logging


logger = logging.getLogger(__name__)
AGREEMENT_ID_REGEX = r"^[a-f0-9]{32}$"


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
    classification: Classification
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)
    agreementID: Optional[str] = Field(None, regex=AGREEMENT_ID_REGEX)

    @property
    def criteria(self):
        return []


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
    classification: Optional[Classification]
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)
    agreementID: Optional[str] = Field(None, regex=AGREEMENT_ID_REGEX)


class Profile(BaseModel):
    """
    The Catalog Profile
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
    classification: Classification
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)
    agreementID: Optional[str] = Field(None, regex=AGREEMENT_ID_REGEX)
    dateModified: datetime = Field(default_factory=lambda: get_now().isoformat())
    owner: str
    criteria: List[Criterion] = Field(..., min_items=1, max_items=100)


ProfileCreateInput = AuthorizedInput[ProfileCreateData]
ProfileUpdateInput = AuthorizedInput[ProfileUpdateData]
ProfileResponse = Response[Profile]
ProfileCreateResponse = CreateResponse[Profile]
