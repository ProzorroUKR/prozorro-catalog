from typing import Optional, Set, Union, List, Literal
from uuid import uuid4
from enum import Enum
from pydantic import (
    Field,
    model_validator,
    StrictInt,
    StrictFloat,
    StrictBool,
    StrictStr,
    PositiveInt,
    constr,
    conset,
    validator,
)
from catalog.models.base import BaseModel
from catalog.models.api import Response, BulkInput, ListResponse, AuthorizedInput
from catalog.models.common import Unit, DataTypeEnum, Period, DataSchemaEnum, ISO_MAPPING
import logging

from catalog.settings import CRITERIA_LIST

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

    @model_validator(mode="after")
    def check_sum(cls, values):
        if not (data_type := values.dataType):
            return values
        for k in ("expectedValue", "maxValue", "minValue"):
            if getattr(values, k) is not None:
                cls._check_value_type(getattr(values, k), data_type)
        if values.expectedValues:
            for value in values.expectedValues:
                cls._check_value_type(value, data_type)
        return values

    @model_validator(mode="after")
    def validate_available_values(cls, values):

        error_map = {
            "expectedValue": ["minValue", "maxValue", "expectedValues"],
            "expectedValues": ["minValue", "maxValue", "expectedValue"],
        }

        for k, v in error_map.items():
            if (
                    getattr(values, k) is not None
                    and any(getattr(values, i) is not None for i in v)
            ):
                raise ValueError(f"{k} couldn't exists together with one of {v}")
        return values

    @model_validator(mode="after")
    def validate_max_min_range(cls, values):
        min_value = values.minValue
        max_value = values.maxValue
        # TODO: remove after migration data type check
        if (
                min_value
                and max_value
                and isinstance(min_value, TYPEMAP.get(DataTypeEnum.number.value))
                and isinstance(max_value, TYPEMAP.get(DataTypeEnum.number.value))
                and min_value > max_value
        ):
            raise ValueError("minValue couldn't be greater than maxValue")
        return values

    @model_validator(mode="after")
    def validate_unit_exist_to_data_type(cls, values):
        data_type = values.dataType
        unit = values.unit

        if unit:
            if data_type in (DataTypeEnum.string.value, DataTypeEnum.boolean.value):
                raise ValueError(f"Unit is forbid with dataType {data_type}")
        else:
            if data_type in (DataTypeEnum.integer.value, DataTypeEnum.number.value):
                raise ValueError(f"Unit is required with dataType {data_type}")

        return values

    @model_validator(mode="after")
    def validate_data_schema(cls, values):
        data_type = values.dataType
        data_schema = values.dataSchema

        if data_schema:
            if not data_type == DataTypeEnum.string.value:
                raise ValueError(f"dataSchema is forbidden with dataType {data_type}")
            if values.expectedValues and set(values.expectedValues) - set(ISO_MAPPING[values.dataSchema]):
                raise ValueError(
                    f"expectedValues should have {values.dataSchema} format and include codes from standards"
                )

        return values


class ProfileRequirementValidators(RequirementBaseValidators):
    @model_validator(mode="after")
    def validate_expected_items(cls, values):
        expected_min_items = values.expectedMinItems
        expected_max_items = values.expectedMaxItems
        expected_values = values.expectedValues or []

        if expected_values is not None:
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


class CategoryRequirementValidators(RequirementBaseValidators):
    @model_validator(mode="after")
    def validate_expected_items(cls, values):
        expected_min_items = values.expectedMinItems
        expected_max_items = values.expectedMaxItems
        expected_values = values.expectedValues

        if expected_values is not None:
            if not expected_min_items or expected_min_items != 1:
                raise ValueError("expectedMinItems is required when expectedValues exists and should be equal 1")

            if expected_max_items and expected_max_items != 1:
                raise ValueError("expectedMaxItems should be equal 1 or not exist at all")

            if expected_min_items > len(expected_values) or (expected_max_items and expected_max_items > len(expected_values)):
                raise ValueError(
                    "count of items in expectedValues should be equal or greater "
                    "than expectedMinItems/expectedMaxItems values"
                )

        elif expected_min_items or expected_max_items:
            raise ValueError(
                "expectedMinItems and expectedMaxItems couldn't exist without expectedValues"
            )
        elif values.dataType == DataTypeEnum.string.value:
            raise ValueError("expectedValues is required when dataType string")

        return values

    @model_validator(mode="after")
    def validate_number_requirements(cls, values):
        if (
            values.dataType in (DataTypeEnum.integer.value, DataTypeEnum.number.value)
            and values.expectedValue is None
            and values.minValue is None
        ):
            raise ValueError("minValue is required when dataType number or integer")
        return values


class EligibleEvidenceType(str, Enum):
    statement = "statement"
    document = "document"


class EligibleEvidence(BaseModel):
    id: str = Field(pattern=r"^[0-9A-Za-z_-]{1,32}$", default_factory=lambda: uuid4().hex)
    title: constr(strip_whitespace=True, min_length=1, max_length=250)
    description: Optional[str] = Field(None, max_length=1000, example="string")
    type: Optional[EligibleEvidenceType] = Field(None, example=EligibleEvidenceType.statement)


class BaseRequirementCreateData(BaseModel):
    title: constr(strip_whitespace=True, min_length=1, max_length=250)
    dataType: DataTypeEnum

    unit: Optional[Unit] = Field(None, example={"code": "string", "name": "string"})
    description: Optional[str] = Field(None, max_length=1000, example="description")
    period: Optional[Period] = Field(None, example={"startDate": "2020-01-01", "endDate": "2020-12-31"})

    pattern: Optional[str] = Field(None, max_length=250, example="string")
    expectedValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = Field(None, example="string")
    maxValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = Field(None, example=1)
    minValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = Field(None, example=1)

    expectedValues: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]] = Field(
        None,
        example=["string1", "string2"],
    )
    expectedMinItems: Optional[PositiveInt] = Field(None, example=1)
    expectedMaxItems: Optional[PositiveInt] = Field(None, example=1)
    dataSchema: Optional[DataSchemaEnum] = Field(None, example=DataSchemaEnum.ISO_639)

    eligibleEvidences: Optional[List[EligibleEvidence]] = Field(
        None,
        max_items=100,
        example=[{"id": uuid4().hex, "title": "string"}]
    )

    @property
    def id(self):
        new_id = uuid4().hex
        self.__dict__['id'] = new_id
        return new_id


class CategoryRequirementCreateData(BaseRequirementCreateData, CategoryRequirementValidators):
    isArchived: bool = False
    expectedValue: Optional[Union[StrictBool, StrictInt, StrictFloat]] = Field(None, example="string")
    maxValue: Optional[Union[StrictInt, StrictFloat]] = Field(None, example=1)
    minValue: Optional[Union[StrictInt, StrictFloat]] = Field(None, example=1)
    expectedValues: Optional[conset(StrictStr, min_length=1)] = Field(
        None,
        example=["string1", "string2"],
    )


class ProfileRequirementCreateData(BaseRequirementCreateData, ProfileRequirementValidators):
    pass


class BaseRequirementUpdateData(BaseModel):
    title: constr(strip_whitespace=True, min_length=1, max_length=250) = None
    dataType: Optional[DataTypeEnum] = Field(None, example=DataTypeEnum.string)

    unit: Optional[Unit] = Field(None, example={"code": "string", "name": "string"})
    description: Optional[str] = Field(None, max_length=1000, example="description")
    period: Optional[Period] = Field(None, example={"startDate": "2020-01-01", "endDate": "2020-12-31"})

    pattern: Optional[str] = Field(None, max_length=250, example="string")
    expectedValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = Field(None, example="string")
    maxValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = Field(None, example=1)
    minValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = Field(None, example=1)

    expectedValues: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]] = Field(
        None,
        example=["string1", "string2"],
    )
    expectedMinItems: Optional[PositiveInt] = Field(None, example=1)
    expectedMaxItems: Optional[PositiveInt] = Field(None, example=1)
    dataSchema: Optional[DataSchemaEnum] = Field(None, example=DataSchemaEnum.ISO_639)

    eligibleEvidences: Optional[List[EligibleEvidence]] = Field(
        None,
        max_items=100,
        example=[{"id": uuid4().hex, "title": "string"}]
    )



class CategoryRequirementUpdateData(BaseRequirementUpdateData):
    isArchived: Optional[bool] = Field(None, example=True)
    expectedValue: Optional[Union[StrictBool, StrictInt, StrictFloat]] = Field(None, example="string")
    maxValue: Optional[Union[StrictInt, StrictFloat]] = Field(None, example=1)
    minValue: Optional[Union[StrictInt, StrictFloat]] = Field(None, example=1)
    expectedValues: Optional[Set[StrictStr]] = Field(
        None,
        example=["string1", "string2"],
    )


class ProfileRequirementUpdateData(BaseRequirementUpdateData):
    pass


class Requirement(BaseModel):
    id: str = Field(..., pattern=r"^[0-9A-Za-z_-]{1,32}$")
    title: str = Field(..., min_length=1, max_length=250)
    dataType: DataTypeEnum

    unit: Optional[Unit] = Field(None, example={"code": "string", "name": "string"})
    description: Optional[str] = Field(None, max_length=1000, example="description")
    period: Optional[Period] = Field(None, example={"startDate": "2020-01-01", "endDate": "2020-12-31"})
    isArchived: Optional[bool] = Field(None, example=True)

    pattern: Optional[str] = Field(None, max_length=250, example="string")
    expectedValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = Field(None, example="string")
    maxValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = Field(None, example=1)
    minValue: Optional[Union[StrictBool, StrictInt, StrictFloat, StrictStr]] = Field(None, example=1)

    expectedValues: Optional[Set[Union[StrictBool, StrictInt, StrictFloat, StrictStr]]] = Field(
        None,
        example=["string1", "string2"],
    )
    expectedMinItems: Optional[PositiveInt] = Field(None, example=1)
    expectedMaxItems: Optional[PositiveInt] = Field(None, example=1)
    dataSchema: Optional[DataSchemaEnum] = Field(None, example=DataSchemaEnum.ISO_639)

    eligibleEvidences: Optional[List[EligibleEvidence]] = Field(None, max_items=100, example=[{"id": uuid4().hex, "title": "string"}])


class CategoryRequirement(Requirement, CategoryRequirementValidators):
    pass


class ProfileRequirement(Requirement, ProfileRequirementValidators):
    pass


class RequirementGroupsCreateData(BaseModel):
    description: str = Field(..., min_length=1, max_length=1000)

    @property
    def id(self):
        return uuid4().hex

    @property
    def requirements(self):
        return []


class RequirementGroupsUpdateData(BaseModel):
    description: str = Field(None, min_length=1, max_length=1000, example="description")


class RequirementGroup(BaseModel):
    id: str = Field(..., pattern=r"^[0-9A-Za-z_-]{1,32}$")
    description: str = Field(..., min_length=1, max_length=1000)
    requirements: List[Requirement] = Field(..., min_items=1, max_items=200)


class LegislationIdentifier(BaseModel):
    id: str
    uri: str = Field(..., min_length=1)
    scheme: Optional[str] = Field(None, min_length=1, max_length=250, example="string")
    legalName: Optional[str] = Field(None, min_length=1, max_length=500, example="string")
    legalName_en: Optional[str] = Field(None, min_length=1, max_length=500, example="string")
    legalName_ru: Optional[str] = Field(None, min_length=1, max_length=500, example="string")


class LegislationItem(BaseModel):
    identifier: LegislationIdentifier
    version: str = Field(..., min_length=1, max_length=250)
    type: str = Field("NATIONAL_LEGISLATION", min_length=1, max_length=100)
    article: str = Field(..., min_length=1, max_length=250)


class CriterionClassification(BaseModel):
    scheme: Literal["ESPD211"]
    id: str = Field(..., min_length=1, max_length=250)

    @validator('id')
    def validate_id(cls, value):
        if value not in CRITERIA_LIST:
            raise ValueError(f"must be one of {CRITERIA_LIST}")
        return value


class CriterionCreateData(BaseModel):
    classification: CriterionClassification
    title: str = Field(..., min_length=1, max_length=250)
    description: str = Field(..., min_length=1, max_length=1000)
    legislation: List[LegislationItem] = Field(..., min_items=1, max_items=100)
    source: str = Field("tenderer", min_length=1, max_length=100)

    @property
    def id(self):
        return uuid4().hex

    @property
    def requirementGroups(self):
        return []


class CriterionUpdateData(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=250, example="string")
    code: Optional[str] = Field(None, pattern=r"^[0-9A-Za-z_-]{1,32}$", example="string")
    description: Optional[str] = Field(None, min_length=1, max_length=1000, example="string")
    legislation: Optional[List[LegislationItem]] = Field(None, min_items=1, max_items=100, example=[
        {
            "identifier": {
                "id": "string",
                "uri": "string",
            },
            "version": "string",
            "type": "NATIONAL_LEGISLATION",
            "article": "string"
        }
    ])
    classification: Optional[CriterionClassification] = Field(None, example={
        "scheme": "ESPD211",
        "id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.TECHNICAL_FEATURES",
    })


class Criterion(BaseModel):
    id: str = Field(..., pattern=r"^[0-9A-Za-z_-]{1,32}$")
    requirementGroups: List[RequirementGroup] = Field(..., min_items=1, max_items=100)
    title: str = Field(..., min_length=1, max_length=250)
    description: str = Field(..., min_length=1, max_length=1000)
    legislation: Optional[List[LegislationItem]] = Field(None, min_items=1, max_items=100, example=[
        {
            "identifier": {
                "id": "string",
                "uri": "string",
            },
            "version": "string",
            "type": "NATIONAL_LEGISLATION",
            "article": "string"
        }
    ])
    classification: Optional[CriterionClassification] = Field(None, example={
        "scheme": "ESPD211",
        "id": "CRITERION.OTHER.SUBJECT_OF_PROCUREMENT.TECHNICAL_FEATURES",
    })
    source: str = "tenderer"


CriterionCreateInput = AuthorizedInput[Union[CriterionCreateData, List[CriterionCreateData]]]
CriterionBulkCreateInput = BulkInput[CriterionCreateData]
CriterionUpdateInput = AuthorizedInput[CriterionUpdateData]
CriterionResponse = Response[Criterion]
CriterionListResponse = ListResponse[Criterion]

RGCreateInput = AuthorizedInput[RequirementGroupsCreateData]
RGUpdateInput = AuthorizedInput[RequirementGroupsUpdateData]
RGResponse = Response[RequirementGroup]
RGListResponse = ListResponse[RequirementGroup]

CategoryRequirementCreateInput = AuthorizedInput[CategoryRequirementCreateData]
CategoryRequirementUpdateInput = AuthorizedInput[CategoryRequirementUpdateData]
ProfileRequirementCreateInput = AuthorizedInput[ProfileRequirementCreateData]
ProfileRequirementUpdateInput = AuthorizedInput[ProfileRequirementUpdateData]
CategoryBulkRequirementCreateInput = BulkInput[CategoryRequirementCreateData]
ProfileBulkRequirementCreateInput = BulkInput[ProfileRequirementCreateData]
RequirementCreateInput = AuthorizedInput[
    Union[
        CategoryRequirementCreateData,
        List[CategoryRequirementCreateData],
        ProfileRequirementCreateData,
        List[ProfileRequirementCreateData],
    ]
]
RequirementUpdateInput = AuthorizedInput[Union[CategoryRequirementUpdateData, ProfileRequirementUpdateData]]
RequirementResponse = Response[Requirement]
RequirementListResponse = ListResponse[Requirement]


