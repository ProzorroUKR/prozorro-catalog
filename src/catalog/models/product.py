from datetime import datetime
from typing import Optional, List, Set, Union
from uuid import UUID
from pydantic import Field, validator, AnyUrl, constr
from catalog.models.base import BaseModel
from catalog.models.api import Input, Response
from catalog.models.common import Unit, Value, Image, Criteria, Classification, Address, ContactPoint, Identifier
from catalog.utils import get_now
from enum import Enum
import re
import logging


logger = logging.getLogger(__name__)


class ProductStatus(str, Enum):
    active = 'active'
    hidden = 'hidden'


class ProductProperty(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    code: str = Field(..., min_length=1, max_length=80)
    value: Union[str, int, float, bool]


class ProductIdentifier(BaseModel):
    id: str = Field(..., min_length=1, max_length=250)
    scheme: str = Field(..., min_length=1, max_length=80)
    uri: Optional[str] = Field(None, min_length=1, max_length=250)


class Brand(BaseModel):
    name: constr(max_length=250)
    uri: constr(max_length=250)
    alternativeNames: Optional[List[constr(max_length=250)]]


class Manufacturer(BaseModel):
    name: constr(max_length=250)
    address: Address
    contactPoint: ContactPoint
    identifier: Identifier


class ProductInfo(BaseModel):
    name: constr(max_length=250)
    uri: Optional[constr(max_length=250)]
    alternativeNames: Optional[List[constr(max_length=250)]]


class RequirementResponse(BaseModel):
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    requirement: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    value: Union[int, str, float, bool, List[str], List[float]]


class ProductCreateData(BaseModel):
    title: str = Field(..., min_length=1, max_length=80)
    relatedProfile: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    description: str = Field(..., min_length=1, max_length=1000)
    classification: Classification
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)
    additionalProperties: Optional[List[ProductProperty]] = Field(None, max_items=100)
    identifier: ProductIdentifier
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    alternativeIdentifiers: Optional[List[ProductIdentifier]] = Field(None, max_items=100)
    brand: Brand
    product: ProductInfo
    manufacturers: Optional[List[Manufacturer]] = Field(None, max_items=100)
    images: Optional[List[Image]] = Field(None, max_items=100)
    requirementResponses: Optional[List[RequirementResponse]] = Field(None, max_items=100)
    status: ProductStatus = ProductStatus.active

    @validator('id')
    def id_format(cls, v, values, **kwargs):
        """
        instead of generating id, we ask user to pass through all these validations
        """
        if values['identifier'].id[:12] not in v:
            raise ValueError('id must include identifier')
        if values['classification'].id[:4] not in v:
            raise ValueError('id must include classification')
        return v

    @validator('requirementResponses')
    def unique_responses_ids(cls, v):
        if v:
            ids = [e.id for e in v]
            if len(ids) != len(set(ids)):
                raise ValueError("not unique requirementResponses.id")

            requirements = [e.requirement for e in v]
            if len(requirements) != len(set(requirements)):
                raise ValueError("not unique requirements")
        return v

    @staticmethod
    def validate_responses(profile, data):  # TODO improve this ?
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


class ProductUpdateData(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=250)
    description: Optional[str] = Field(None, min_length=1, max_length=1000)
    status: Optional[ProductStatus]
    unit: Optional[Unit]
    value: Optional[Value]
    images: Optional[List[Image]] = Field(None, max_items=100)
    criteria: Optional[List[Criteria]] = Field(None, min_items=1, max_items=100)
    classification: Optional[Classification]
    additionalClassifications: Optional[List[Classification]] = Field(None, max_items=100)


class Product(ProductCreateData):
    dateModified: datetime = Field(default_factory=lambda: get_now().isoformat())


ProductCreateInput = Input[ProductCreateData]
ProductUpdateInput = Input[ProductUpdateData]
ProductResponse = Response[Product]
