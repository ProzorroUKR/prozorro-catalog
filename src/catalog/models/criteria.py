from typing import Optional, Set, Union, List
from uuid import uuid4
from pydantic import Field, root_validator,  StrictInt, StrictFloat, StrictBool, StrictStr
from catalog.models.base import BaseModel
from catalog.models.api import Input, Response, BulkInput, ListResponse
from catalog.models.common import Unit, DataTypeEnum, Period
import logging


logger = logging.getLogger(__name__)


class RequirementCreateData(BaseModel):
    title: str = Field(..., min_length=1, max_length=250)
    dataType: DataTypeEnum = Field(..., max_length=100)

    unit: Optional[Unit] = None
    description: Optional[str] = Field(None, max_length=1000)
    period: Optional[Period] = None

    pattern: Optional[str] = Field(None, max_length=250)
    expectedValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None
    maxValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None
    minValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None

    allOf: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]] = Field(None, max_items=100)
    anyOf: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]] = Field(None, max_items=100)
    oneOf: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]] = Field(None, max_items=100)

    @property
    def id(self):
        new_id = uuid4().hex
        self.__dict__['id'] = new_id
        return new_id

    @root_validator
    def check_sum(cls, values):
        if values["dataType"] == DataTypeEnum.integer.value:
            for k in ("expectedValue", "maxValue", "minValue"):
                if values[k] is not None:
                    if not isinstance(values[k], int):
                        raise ValueError(f"Invalid integer '{values[k]}'")
        return values


class RequirementUpdateData(BaseModel):
    title: str = Field(None, min_length=1, max_length=250)
    dataType: DataTypeEnum = Field(None, max_length=100)

    unit: Optional[Unit] = None
    description: Optional[str] = Field(None, max_length=1000)
    period: Optional[Period] = None

    pattern: Optional[str] = Field(None, max_length=250)
    expectedValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None
    maxValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None
    minValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None

    allOf: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]] = Field(None, max_items=100)
    anyOf: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]] = Field(None, max_items=100)
    oneOf: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]] = Field(None, max_items=100)

    @root_validator
    def check_sum(cls, values):
        if values["dataType"] == DataTypeEnum.integer.value:
            for k in ("expectedValue", "maxValue", "minValue"):
                if values[k] is not None:
                    if not isinstance(values[k], int):
                        raise ValueError(f"Invalid integer '{values[k]}'")
        return values


class Requirement(BaseModel):
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    title: str = Field(..., min_length=1, max_length=250)
    dataType: DataTypeEnum = Field(..., max_length=100)

    unit: Optional[Unit] = None
    description: Optional[str] = Field(None, max_length=1000)
    period: Optional[Period] = None

    pattern: Optional[str] = Field(None, max_length=250)
    expectedValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None
    maxValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None
    minValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = None

    allOf: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]] = Field(None, max_items=100)
    anyOf: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]] = Field(None, max_items=100)
    oneOf: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]] = Field(None, max_items=100)


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


class CriterionCreateData(BaseModel):
    title: str = Field(..., min_length=1, max_length=250)
    description: str = Field(..., min_length=1, max_length=250)

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


class Criterion(BaseModel):
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    requirementGroups: List[RequirementGroup] = Field(..., min_items=1, max_items=100)
    title: str = Field(..., min_length=1, max_length=250)
    description: str = Field(..., min_length=1, max_length=250)


CriterionCreateInput = Input[CriterionCreateData]
CriterionUpdateInput = Input[CriterionUpdateData]
CriterionResponse = Response[Criterion]
CriterionListResponse = ListResponse[Criterion]

RGCreateInput = Input[RequirementGroupsCreateData]
RGUpdateInput = Input[RequirementGroupsUpdateData]
RGResponse = Response[RequirementGroup]
RGListResponse = ListResponse[RequirementGroup]

RequirementCreateInput = Input[RequirementCreateData]
RequirementUpdateInput = Input[RequirementUpdateData]
BulkRequirementCreateInput = BulkInput[RequirementCreateData]
RequirementResponse = Response[Requirement]
RequirementListResponse = ListResponse[Requirement]


