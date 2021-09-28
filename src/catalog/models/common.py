from datetime import datetime
from typing import Optional, List, Set, Union
from pydantic import Field, validator, AnyUrl
from catalog.models.base import BaseModel
from enum import Enum


class DataTypeEnum(str, Enum):
    string = "string"
    datetime = "date-time"
    number = "number"
    integer = "integer"
    boolean = "boolean"


class Unit(BaseModel):
    code: str = Field(..., min_length=1, max_length=80)
    name: str = Field(..., min_length=1, max_length=250)


class Value(BaseModel):
    amount: float
    currency: str = Field(..., regex=r"^[A-Z]{3}$")
    valueAddedTaxIncluded: bool = True


class Period(BaseModel):
    durationInDays: Optional[int] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None


class Image(BaseModel):
    sizes: str = Field(..., regex=r"^[0-9]{2,4}x[0-9]{2,4}$")
    url: AnyUrl
    title: Optional[str] = Field(None, min_length=1, max_length=250)
    format: Optional[str] = Field(None, regex=r"^image/[a-z]{2,10}$")


class Requirement(BaseModel):
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    title: str = Field(..., min_length=1, max_length=250)
    dataType: DataTypeEnum = Field(..., max_length=100)

    unit: Optional[Unit] = None
    description: Optional[str] = Field(None, max_length=1000)
    period: Optional[Period] = None

    pattern: Optional[str] = Field(None, max_length=250)
    expectedValue: Optional[Union[bool, float, str]] = None
    maxValue: Optional[Union[bool, float, str]] = None
    minValue: Optional[Union[bool, float, str]] = None

    allOf: Optional[Set[Union[bool, float, str]]] = Field(None, max_items=100)
    anyOf: Optional[Set[Union[bool, float, str]]] = Field(None, max_items=100)
    oneOf: Optional[Set[Union[bool, float, str]]] = Field(None, max_items=100)


class RequirementGroup(BaseModel):
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    description: str = Field(..., min_length=1, max_length=1000)
    requirements: List[Requirement] = Field(..., min_items=1, max_items=100)


class Criteria(BaseModel):
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    title: str = Field(..., min_length=1, max_length=250)
    code: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    description: str = Field(..., min_length=1, max_length=250)
    requirementGroups: List[RequirementGroup] = Field(..., min_items=1, max_items=100)


class Classification(BaseModel):
    id: str = Field(..., regex=r"^[0-9A-Za-z_-]{1,32}$")
    description: str = Field(..., min_length=1, max_length=250)
    scheme: str = Field(..., min_length=1, max_length=10)


class Address(BaseModel):
    countryName: str = Field(..., max_length=80)
    locality: str = Field(..., max_length=80)
    postalCode: str = Field(..., max_length=20)
    region: str = Field(..., max_length=80)
    streetAddress: str = Field(..., max_length=250)


class ContactPoint(BaseModel):
    name: str = Field(..., max_length=250)
    telephone: Optional[str] = Field(None, max_length=250)
    url: Optional[str] = Field(None, max_length=250)
    email: Optional[str] = Field(None, max_length=250)
    faxNumber: Optional[str] = Field(None, max_length=250)


class Identifier(BaseModel):
    id: str = Field(..., max_length=50)
    legalName: str = Field(..., max_length=250)
    scheme: str = Field(..., max_length=20)


class ProcuringEntityKind(str, Enum):
    central = "central"
    regional = "regional"


class ProcuringEntity(BaseModel):
    name: str = Field(..., max_length=250)
    address: Address
    contactPoint: ContactPoint
    identifier: Identifier
    kind: ProcuringEntityKind
