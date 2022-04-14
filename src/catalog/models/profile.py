from datetime import datetime
from typing import Optional, List, Set, Union
from uuid import UUID
from pydantic import Field, validator, AnyUrl
from catalog.models.base import BaseModel
from catalog.models.api import Input, Response, CreateResponse
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

    @staticmethod
    def validate_product(profile, data):  # TODO redesign this ?
        profile_requirements = {
            r["id"]: r
            for c in profile.get("criteria", "")
            for group in c["requirementGroups"]
            for r in group["requirements"]
        }
        responded_requirements = set()
        for req_response in data.get("requirementResponses", ""):
            key = req_response['requirement']
            value = req_response['value']
            responded_requirements.add(key)

            if key not in profile_requirements:
                raise ValueError('requirement %s not found' % key)

            requirement = profile_requirements[key]
            if 'expectedValue' in requirement:
                if value != requirement['expectedValue']:
                    raise ValueError('requirement %s unexpected value' % key)
            if 'minValue' in requirement:
                if value < requirement['minValue']:
                    raise ValueError('requirement %s minValue' % key)
            if 'maxValue' in requirement:
                if value > requirement['maxValue']:
                    raise ValueError('requirement %s maxValue' % key)
            if 'pattern' in requirement:
                if not re.match(requirement['pattern'], str(value)):
                    raise ValueError('requirement %s pattern' % key)
            if 'allOf' in requirement:
                if set(value) != set(requirement['allOf']):
                    raise ValueError('requirement %s allOf' % key)
            if 'anyOf' in requirement:
                if isinstance(value, list):
                    if not set(value).issubset(set(requirement['anyOf'])):
                        raise ValueError('requirement %s anyOf' % key)
                elif value not in requirement['anyOf']:
                    raise ValueError('requirement %s anyOf' % key)
            if 'oneOf' in requirement:
                if value not in requirement['oneOf']:
                    raise ValueError('requirement %s oneOf' % key)

        for cr in profile['criteria']:
            group_found = 0
            for rg in cr['requirementGroups']:
                requirement_found = 0
                for req in rg['requirements']:
                    if req['id'] in responded_requirements:
                        requirement_found += 1
                if requirement_found == len(rg['requirements']):
                    group_found += 1
            if group_found == 0:
                raise ValueError('criteria %s not satisfied' % cr['id'])

    @staticmethod
    def validate_offer(profile, data):
        if data['value']['currency'] != profile['value']['currency']:
            raise ValueError('value.currency mismatch')

        if 'valueAddedTaxIncluded' in profile['value']:
            if data['value'].get('valueAddedTaxIncluded', None) != profile['value']['valueAddedTaxIncluded']:
                raise ValueError('value.valueAddedTaxIncluded mismatch')

        if 'minOrderValue' in data:
            if data['minOrderValue']['amount'] < data['value']['amount']:
                raise ValueError('minOrderValue.amount mismatch')
            if data['minOrderValue']['currency'] != data['value']['currency']:
                raise ValueError('minOrderValue.currency mismatch')


ProfileCreateInput = Input[ProfileCreateData]
ProfileUpdateInput = Input[ProfileUpdateData]
ProfileResponse = Response[Profile]
ProfileCreateResponse = CreateResponse[Profile]
