from datetime import datetime
from typing import Optional, List
from pydantic import Field
from catalog.models.base import BaseModel
from catalog.models.api import Response, CreateResponse, AuthorizedInput
from catalog.models.common import Unit, Value, Image, Classification, AGREEMENT_ID_REGEX
from catalog.models.criteria import Criterion
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
    value: Value
    relatedCategory: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    images: Optional[List[Image]] = Field(None, max_items=100)
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)

    @property
    def criteria(self):
        return []


class LocalizationProfileCreateData(ProfileCreateData):
    unit: Optional[Unit]
    agreementID: Optional[str] = Field(None, regex=AGREEMENT_ID_REGEX)
    classification: Classification


class ProfileUpdateData(BaseModel):
    """
    The Catalog Profile Update Data
    """
    title: Optional[str] = Field(None, min_length=1, max_length=250)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    status: Optional[ProfileStatus]
    images: Optional[List[Image]] = Field(None, max_items=100)
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)


class LocalizationProfileUpdateData(ProfileUpdateData):
    unit: Optional[Unit]
    classification: Optional[Classification]
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
    unit: Optional[Unit]
    value: Value
    relatedCategory: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    images: Optional[List[Image]] = Field(None, max_items=100)
    classification: Classification
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)
    agreementID: Optional[str] = Field(None, regex=AGREEMENT_ID_REGEX)
    dateModified: datetime = Field(default_factory=lambda: get_now().isoformat())
    owner: str
    criteria: List[Criterion] = Field(..., max_items=1)


ProfileCreateInput = AuthorizedInput[ProfileCreateData]
LocalizationProfileInput = AuthorizedInput[LocalizationProfileCreateData]
ProfileUpdateInput = AuthorizedInput[ProfileUpdateData]
LocalizationProfileUpdateInput = AuthorizedInput[LocalizationProfileUpdateData]
ProfileResponse = Response[Profile]
ProfileCreateResponse = CreateResponse[Profile]
