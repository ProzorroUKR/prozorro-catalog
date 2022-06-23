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

    @classmethod
    def _validate_req_response_value(cls, requirement, value, key):
        if value is None:
            raise ValueError(f'requirement {key} should have value')
        if (
            'expectedValue' in requirement
            and value != requirement['expectedValue']
        ):
            raise ValueError(f'requirement {key} unexpected value')
        if 'minValue' in requirement and value < requirement['minValue']:
            raise ValueError(f'requirement {key} minValue')
        if 'maxValue' in requirement and value > requirement['maxValue']:
            raise ValueError(f'requirement {key} maxValue')
        if 'pattern' in requirement and not re.match(
                requirement['pattern'], str(value)
        ):
            raise ValueError(f'requirement {key} pattern')

    @classmethod
    def _validate_req_response_values(cls, requirement, values, key):
        if not values:
            raise ValueError(f'requirement {key} should have values')
        if not set(values).issubset(set(requirement['expectedValues'])):
            raise ValueError(f'requirement {key} expectedValues')
        if 'expectedMinItems' in requirement and len(values) < requirement['expectedMinItems']:
            raise ValueError(f'requirement {key} expectedMinItems')
        if 'expectedMaxItems' in requirement and len(values) > requirement['expectedMaxItems']:
            raise ValueError(f'requirement {key} expectedMaxItems')

    @classmethod
    def _validate_product_req_response(cls, req_response, requirement):
        value = req_response.get('value')
        values = req_response.get('values')
        key = req_response.get('requirement')

        if any(i in requirement for i in ('expectedValue', 'minValue', 'maxValue', 'pattern')):
            cls._validate_req_response_value(requirement, value, key)

        elif 'expectedValues' in requirement:
            cls._validate_req_response_values(requirement, values, key)

    @classmethod
    def validate_product(cls, profile, data):  # TODO redesign this ?
        profile_requirements = {
            r["id"]: r
            for c in profile.get("criteria", "")
            for group in c["requirementGroups"]
            for r in group["requirements"]
        }
        responded_requirements = set()
        for req_response in data.get("requirementResponses", ""):
            key = req_response['requirement']
            responded_requirements.add(key)

            if key not in profile_requirements:
                raise ValueError(f'requirement {key} not found')

            requirement = profile_requirements[key]
            cls._validate_product_req_response(req_response, requirement)

        for cr in profile['criteria']:
            group_found = 0
            for rg in cr['requirementGroups']:
                requirement_found = sum(req['id'] in responded_requirements for req in rg['requirements'])

                if requirement_found == len(rg['requirements']):
                    group_found += 1
            if group_found == 0:
                raise ValueError('criteria %s not satisfied' % cr['id'])


ProfileCreateInput = AuthorizedInput[ProfileCreateData]
ProfileUpdateInput = AuthorizedInput[ProfileUpdateData]
ProfileResponse = Response[Profile]
ProfileCreateResponse = CreateResponse[Profile]
