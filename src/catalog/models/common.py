from datetime import datetime
from typing import Optional, Union
from pydantic import Field, validator, AnyUrl, constr, root_validator
from catalog.models.base import BaseModel
from catalog.models.api import Response
from catalog.settings import IMG_PATH
from enum import Enum
import standards
import re


UNIT_CODES = standards.load("unit_codes/recommended.json")
UA_REGIONS = standards.load("classifiers/ua_regions.json")
COUNTRY_NAMES = standards.load("classifiers/countries.json")

COUNTRY_NAMES_UK = [names.get("name_uk") for names in COUNTRY_NAMES.values()]
UNIT_CODES = UNIT_CODES.keys()

UKRAINE_COUNTRY_NAME_UK = COUNTRY_NAMES.get("UA").get("name_uk")


class DataTypeEnum(str, Enum):
    string = "string"
    datetime = "date-time"
    number = "number"
    integer = "integer"
    boolean = "boolean"


class Unit(BaseModel):
    code: str = Field(..., min_length=1, max_length=80)
    name: str = Field(..., min_length=1, max_length=250)

    @validator('code')
    def code_standard(cls, v):
        if v not in UNIT_CODES:
            raise ValueError("must be one of unit_codes/recommended.json keys")
        return v


class Value(BaseModel):
    amount: Union[float, int]
    currency: str = Field(..., regex=r"^[A-Z]{3}$")
    valueAddedTaxIncluded: bool = True


class Period(BaseModel):
    durationInDays: Optional[int] = None
    startDate: Optional[datetime] = None
    endDate: Optional[datetime] = None


class BaseImage(BaseModel):
    url: AnyUrl
    size: Optional[int]
    hash: Optional[str] = Field(None, regex=r"^md5:[0-9a-z]{32}$")


ImageResponse = Response[BaseImage]


class Image(BaseModel):
    url: str = Field(..., min_length=1)
    sizes: Optional[str] = Field(None, regex=r"^[0-9]{2,4}x[0-9]{2,4}$")
    title: Optional[str] = Field(None, min_length=1, max_length=250)
    format: Optional[str] = Field(None, regex=r"^image/[a-z]{2,10}$")
    hash: Optional[str] = Field(None, regex=r"^md5:[0-9a-f]{32}$")

    @validator('url')
    def valid_url(cls, v):
        if not v.startswith(IMG_PATH):
            raise ValueError(f"Invalid url, should start with {IMG_PATH}")
        return v


class Classification(BaseModel):
    id: str = Field(..., min_length=1, max_length=32)
    description: str = Field(..., min_length=1, max_length=250)
    scheme: str = Field(..., min_length=1, max_length=10)


class Address(BaseModel):
    countryName: str = Field(..., max_length=80)
    locality: str = Field(..., max_length=80)
    postalCode: str = Field(..., max_length=20)
    region: str = Field(..., max_length=80)
    streetAddress: str = Field(..., max_length=250)

    @validator('region')
    def region_standard(cls, v, values):
        country_name = values.get("countryName")
        if country_name == UKRAINE_COUNTRY_NAME_UK and v not in UA_REGIONS:
            raise ValueError("must be one of classifiers/ua_regions.json")
        return v

    @validator('countryName')
    def country_standard(cls, v):
        if v not in COUNTRY_NAMES_UK:
            raise ValueError("must be one of classifiers/countries.json")
        return v


class OfferSuppliersAddress(Address):
    locality: Optional[constr(max_length=80)]


class OfferDeliveryAddress(Address):  # only countryName is required
    locality: Optional[constr(max_length=80)]
    postalCode: Optional[constr(max_length=20)]
    region: Optional[constr(max_length=80)]
    streetAddress: Optional[constr(max_length=250)]

    @validator('region')
    def region_for_ukraine_only(cls, v, values):
        country_name = values.get("countryName")
        if country_name != UKRAINE_COUNTRY_NAME_UK and v:
            raise ValueError("can be provided only for Ukraine")
        return v


class ContactPoint(BaseModel):
    name: str = Field(..., max_length=250)
    telephone: str = Field(..., max_length=250)
    url: Optional[str] = Field(None, max_length=250)
    email: Optional[str] = Field(None, max_length=250)
    faxNumber: Optional[str] = Field(None, max_length=250)

    @validator('telephone')
    def telephone_format(cls, v):
        if not re.match(r"^(\+)?[0-9]{2,}(,( )?(\+)?[0-9]{2,})*$", v):
            raise ValueError("Invalid phone format")
        return v


class Identifier(BaseModel):
    id: str = Field(..., min_length=4, max_length=50)
    legalName: str = Field(..., max_length=250)
    scheme: str = Field(..., max_length=20)


class ProcuringEntityKind(str, Enum):
    central = "central"
    regional = "regional"


class ProcuringEntity(BaseModel):
    name: constr(max_length=250)
    address: Address
    contactPoint: ContactPoint
    identifier: Identifier
    kind: ProcuringEntityKind
