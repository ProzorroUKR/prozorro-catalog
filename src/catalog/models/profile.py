from datetime import datetime
from typing import Optional, List, Union
from uuid import uuid4

from pydantic import Field
from catalog.models.base import BaseModel
from catalog.models.api import Response, CreateResponse, AuthorizedInput
from catalog.models.common import (
    Unit,
    Classification,
    CategoryMarketAdministrator,
    AGREEMENT_ID_REGEX, CLASSIFICATION_EXAMPLE, UNIT_EXAMPLE,
)
from catalog.models.criteria import Criterion
from catalog.models.tag import TagsMixin
from catalog.utils import get_now
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class ProfileStatus(str, Enum):
    active = 'active'
    hidden = 'hidden'


class BaseProfileCreateData(TagsMixin, BaseModel):
    """
    The Catalog Profile Create Data
    """
    title: str = Field(
        ...,
        title='Profile Name',
        description='Descriptive profile name',
        min_length=1,
        max_length=250,
    )
    description: Optional[str] = Field(
        None,
        title='Profile Description',
        description='Profile details',
        min_length=1,
        max_length=1000,
        example="description",
    )
    status: ProfileStatus = ProfileStatus.active
    relatedCategory: str = Field(..., pattern=r"^[0-9A-Za-z_-]{1,32}$")
    additionalClassifications: Optional[List[Classification]] = Field(
        None,
        max_length=100,
        example=[CLASSIFICATION_EXAMPLE],
    )
    agreementID: Optional[str] = Field(None, pattern=AGREEMENT_ID_REGEX, example=uuid4().hex)

    @property
    def criteria(self):
        return []


class ProfileCreateData(BaseProfileCreateData):
    @property
    def id(self):
        return uuid4().hex


class DeprecatedProfileCreateData(BaseProfileCreateData):
    """
    Deprecated soon the Catalog Profile Create Data with required id and creation via PUT method
    """
    id: str = Field(..., pattern=r"^[0-9A-Za-z_-]{1,32}$")


class BaseLocalizationProfileCreateData(BaseProfileCreateData):
    unit: Unit
    agreementID: Optional[str] = Field(None, pattern=AGREEMENT_ID_REGEX, example=uuid4().hex)
    classification: Classification


class LocalizationProfileCreateData(BaseLocalizationProfileCreateData):
    @property
    def id(self):
        return uuid4().hex


class DeprecatedLocalizationProfileCreateData(BaseLocalizationProfileCreateData):
    """
    Deprecated soon the Localization Catalog Profile Create Data with required id and creation via PUT method
    """
    id: str = Field(..., pattern=r"^[0-9A-Za-z_-]{1,32}$")


class ProfileUpdateData(TagsMixin, BaseModel):
    """
    The Catalog Profile Update Data
    """
    title: Optional[str] = Field(None, min_length=1, max_length=250, example="title")
    description: Optional[str] = Field(None, min_length=1, max_length=1000, example="description")
    status: Optional[ProfileStatus] = Field(None, example=ProfileStatus.active)
    additionalClassifications: Optional[List[Classification]] = Field(
        None,
        max_length=100,
        example=[CLASSIFICATION_EXAMPLE],
    )
    agreementID: Optional[str] = Field(None, pattern=AGREEMENT_ID_REGEX, example=uuid4().hex)


class LocalizationProfileUpdateData(ProfileUpdateData):
    unit: Optional[Unit] = Field(None, example=UNIT_EXAMPLE)
    classification: Optional[Classification] = Field(None, example=CLASSIFICATION_EXAMPLE)


class Profile(TagsMixin, BaseModel):
    """
    The Catalog Profile
    """
    id: str = Field(..., pattern=r"^[0-9A-Za-z_-]{1,32}$")
    title: str = Field(
        ...,
        title='Profile Name',
        description='Descriptive profile name',
        min_length=1,
        max_length=250,
    )
    description: Optional[str] = Field(
        None,
        title='Profile Description',
        description='Profile details',
        min_length=1,
        max_length=1000,
        example="description",
    )
    status: ProfileStatus = ProfileStatus.active
    marketAdministrator: CategoryMarketAdministrator
    unit: Optional[Unit] = Field(None, example=UNIT_EXAMPLE)
    relatedCategory: str = Field(..., pattern=r"^[0-9A-Za-z_-]{1,32}$")
    classification: Classification
    additionalClassifications: Optional[List[Classification]] = Field(
        None,
        max_length=100,
        example=CLASSIFICATION_EXAMPLE,
    )
    agreementID: Optional[str] = Field(None, pattern=AGREEMENT_ID_REGEX, example=uuid4().hex)
    dateModified: datetime = Field(default_factory=lambda: get_now().isoformat())
    dateCreated: datetime
    owner: str
    criteria: List[Criterion] = Field(...)


RequestProfileCreateInput = AuthorizedInput[Union[ProfileCreateData, LocalizationProfileCreateData]]
DeprecatedRequestProfileCreateInput = AuthorizedInput[Union[DeprecatedProfileCreateData, DeprecatedLocalizationProfileCreateData]]
ProfileCreateInput = AuthorizedInput[ProfileCreateData]
DeprecatedProfileCreateInput = AuthorizedInput[DeprecatedProfileCreateData]
LocalizationProfileInput = AuthorizedInput[LocalizationProfileCreateData]
DeprecatedLocProfileInput = AuthorizedInput[DeprecatedLocalizationProfileCreateData]
RequestProfileUpdateInput = AuthorizedInput[Union[ProfileUpdateData, LocalizationProfileUpdateData]]
ProfileUpdateInput = AuthorizedInput[ProfileUpdateData]
LocalizationProfileUpdateInput = AuthorizedInput[LocalizationProfileUpdateData]
ProfileResponse = Response[Profile]
ProfileCreateResponse = CreateResponse[Profile]
