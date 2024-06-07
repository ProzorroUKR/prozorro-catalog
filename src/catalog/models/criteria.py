from typing import Optional, Set, Union, List
from uuid import uuid4
from pydantic import (
    Field,
    root_validator,
    StrictInt,
    StrictFloat,
    StrictBool,
    StrictStr,
    PositiveInt,
    constr,
)
from catalog.models.base import BaseModel
from catalog.models.api import Response, BulkInput, ListResponse, AuthorizedInput
from catalog.models.common import Unit, DataTypeEnum, Period
import logging


logger = logging.getLogger(__name__)

TYPEMAP = {
    DataTypeEnum.string.value: str,
    DataTypeEnum.integer.value: int,
    DataTypeEnum.number.value: (float, int),
    DataTypeEnum.datetime.value: str,
    DataTypeEnum.boolean.value: bool,
}


class RequirementBaseValidators(BaseModel):

    @classmethod
    def _check_value_type(cls, value, data_type_name):
        data_type = TYPEMAP.get(data_type_name)
        if not data_type:
            raise ValueError(f"Invalid dataType '{data_type_name}'")

        if not isinstance(value, data_type):
            raise ValueError(f"Value '{value}' isn't {data_type_name}")

    @root_validator
    def check_sum(cls, values):

        for k in ("expectedValue", "maxValue", "minValue"):
            if values.get(k) is not None:
                cls._check_value_type(values[k], values["dataType"])
        if values.get("expectedValues"):
            for value in values["expectedValues"]:
                cls._check_value_type(value, values["dataType"])
        return values

    @root_validator
    def validate_expected_items(cls, values):
        expected_min_items = values.get("expectedMinItems")
        expected_max_items = values.get("expectedMaxItems")
        expected_values = values.get("expectedValues")

        if expected_values:
            if expected_min_items and expected_max_items and expected_min_items > expected_max_items:
                raise ValueError("expectedMinItems couldn't be greater then expectedMaxItems")

            if expected_min_items and expected_min_items > len(expected_values):
                raise ValueError(
                    "expectedMinItems couldn't be greater then count of items in expectedValues"
                )

            if expected_max_items and expected_max_items > len(expected_values):
                raise ValueError(
                    "expectedMaxItems couldn't be greater then count of items in expectedValues"
                )

        elif expected_min_items or expected_max_items:
            raise ValueError(
                "expectedMinItems and expectedMaxItems couldn't exist without expectedValues"
            )

        return values

    @root_validator
    def validate_available_values(cls, values):

        error_map = {
            "expectedValue": ["minValue", "maxValue", "expectedValues"],
            "expectedValues": ["minValue", "maxValue", "expectedValue"],
        }

        for k, v in error_map.items():
            if (
                    values.get(k) is not None
                    and any(values.get(i) is not None for i in v)
            ):
                raise ValueError(f"{k} couldn't exists together with one of {v}")
        return values


class ProfileRequirementCreateData(RequirementBaseValidators):
    title: constr(strip_whitespace=True, min_length=1, max_length=250)
    dataType: DataTypeEnum = Field(None, max_length=100)

    unit: Optional[Unit] = None
    description: Optional[str] = Field(None, max_length=1000)
    period: Optional[Period] = None

    pattern: Optional[str] = Field(None, max_length=250)
    expectedValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None
    maxValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None
    minValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None

    expectedValues: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]]
    expectedMinItems: Optional[PositiveInt] = None
    expectedMaxItems: Optional[PositiveInt] = None

    @property
    def id(self):
        new_id = uuid4().hex
        self.__dict__['id'] = new_id
        return new_id


class RequirementCreateData(ProfileRequirementCreateData):
    isArchived: bool = False


class ProfileRequirementUpdateData(BaseModel):
    title: constr(strip_whitespace=True, min_length=1, max_length=250) = None
    dataType: DataTypeEnum = Field(None, max_length=100)

    unit: Optional[Unit] = None
    description: Optional[str] = Field(None, max_length=1000)
    period: Optional[Period] = None

    pattern: Optional[str] = Field(None, max_length=250)
    expectedValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None
    maxValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]
    minValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]

    expectedValues: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]]
    expectedMinItems: Optional[PositiveInt]
    expectedMaxItems: Optional[PositiveInt]


class RequirementUpdateData(ProfileRequirementUpdateData):
    isArchived: Optional[bool] = None


class Requirement(RequirementBaseValidators):
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    title: str = Field(..., min_length=1, max_length=250)
    dataType: DataTypeEnum = Field(..., max_length=100)

    unit: Optional[Unit] = None
    description: Optional[str] = Field(None, max_length=1000)
    period: Optional[Period] = None
    isArchived: Optional[bool]

    pattern: Optional[str] = Field(None, max_length=250)
    expectedValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None
    maxValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None
    minValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None

    expectedValues: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]]
    expectedMinItems: Optional[PositiveInt] = None
    expectedMaxItems: Optional[PositiveInt] = None


class RequirementGroupsCreateData(BaseModel):
    description: str = Field(..., min_length=1, max_length=1000)

    @property
    def id(self):
        return uuid4().hex

    @property
    def requirements(self):
        return []


class RequirementGroupsUpdateData(BaseModel):
    description: str = Field(None, min_length=1, max_length=1000)


class RequirementGroup(BaseModel):
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    description: str = Field(..., min_length=1, max_length=1000)
    requirements: List[Requirement] = Field(..., min_items=1, max_items=100)


class LegislationIdentifier(BaseModel):
    id: str
    scheme: Optional[str] = Field(None, min_length=1, max_length=250)
    legalName: Optional[str] = Field(None, min_length=1, max_length=250)
    legalName_en: Optional[str] = Field(None, min_length=1, max_length=250)
    legalName_ru: Optional[str] = Field(None, min_length=1, max_length=250)
    uri: Optional[str] = None


class LegislationItem(BaseModel):
    identifier: LegislationIdentifier
    version: Optional[str] = Field(None, min_length=1, max_length=250)
    type: str = "NATIONAL_LEGISLATION"
    article: Optional[str] = Field(None, min_length=1, max_length=250)


class CriterionClassification(BaseModel):
    scheme: str = Field(..., min_length=1, max_length=250)
    id: str = Field(..., min_length=1, max_length=250)


class CriterionCreateData(BaseModel):
    title: str = Field(..., min_length=1, max_length=250)
    description: str = Field(..., min_length=1, max_length=250)
    legislation: Optional[List[LegislationItem]] = Field(None, min_items=1, max_items=100)
    classification: Optional[CriterionClassification] = None

    @property
    def id(self):
        return uuid4().hex

    @property
    def requirementGroups(self):
        return []


class CriterionUpdateData(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=250)
    code: Optional[str] = Field(None, regex=r"^[0-9A-Za-z_-]{1,32}$")
    description: Optional[str] = Field(None, min_length=1, max_length=250)
    legislation: Optional[List[LegislationItem]] = Field(None, min_items=1, max_items=100)
    classification: Optional[CriterionClassification] = None


class Criterion(BaseModel):
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    requirementGroups: List[RequirementGroup] = Field(..., min_items=1, max_items=100)
    title: str = Field(..., min_length=1, max_length=250)
    description: str = Field(..., min_length=1, max_length=250)
    legislation: Optional[List[LegislationItem]] = Field(None, min_items=1, max_items=100)
    classification: Optional[CriterionClassification] = None


CriterionCreateInput = AuthorizedInput[CriterionCreateData]
CriterionUpdateInput = AuthorizedInput[CriterionUpdateData]
CriterionResponse = Response[Criterion]
CriterionListResponse = ListResponse[Criterion]

RGCreateInput = AuthorizedInput[RequirementGroupsCreateData]
RGUpdateInput = AuthorizedInput[RequirementGroupsUpdateData]
RGResponse = Response[RequirementGroup]
RGListResponse = ListResponse[RequirementGroup]

RequirementCreateInput = AuthorizedInput[RequirementCreateData]
RequirementUpdateInput = AuthorizedInput[RequirementUpdateData]
ProfileRequirementCreateInput = AuthorizedInput[ProfileRequirementCreateData]
ProfileRequirementUpdateInput = AuthorizedInput[ProfileRequirementUpdateData]
BulkRequirementCreateInput = BulkInput[RequirementCreateData]
ProfileBulkRequirementCreateInput = BulkInput[ProfileRequirementCreateData]
RequirementResponse = Response[Requirement]
RequirementListResponse = ListResponse[Requirement]


