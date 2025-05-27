from datetime import datetime
from typing import Optional, Union, Annotated
from pydantic import Field, field_validator, AnyUrl, model_validator
from pydantic.types import StringConstraints
from catalog.models.base import BaseModel
from catalog.models.api import Response
from catalog.settings import IMG_PATH
from enum import Enum
import standards
import re


UNIT_CODES_DATA = standards.load("unit_codes/recommended.json")
UA_REGIONS = standards.load("classifiers/ua_regions.json")
COUNTRY_NAMES = standards.load("classifiers/countries.json")
ORA_CODES = [i["code"] for i in standards.load("organizations/identifier_scheme.json")["data"]]
LANGUAGE_CODES = standards.load("classifiers/languages.json").keys()

COUNTRY_NAMES_UK = [names.get("name_uk") for names in COUNTRY_NAMES.values()]
UNIT_CODES = UNIT_CODES_DATA.keys()

UKRAINE_COUNTRY_NAME_UK = COUNTRY_NAMES.get("UA").get("name_uk")
AGREEMENT_ID_REGEX = r"^[a-f0-9]{32}$"
ADMINISTRATOR_IDENTIFIERS = [
    cpb["identifier"]["id"]
    for cpb in standards.load("organizations/authorized_cpb.json")
    if cpb.get("marketAdministrator")
]


class DataTypeEnum(str, Enum):
    string = "string"
    datetime = "date-time"
    number = "number"
    integer = "integer"
    boolean = "boolean"


class DataSchemaEnum(str, Enum):
    ISO_639 = "ISO 639-3"
    ISO_3166 = "ISO 3166-1 alpha-2"


ISO_MAPPING = {
    DataSchemaEnum.ISO_639.value: LANGUAGE_CODES,
    DataSchemaEnum.ISO_3166.value: COUNTRY_NAMES.keys(),
}


class Unit(BaseModel):
    code: str = Field(..., min_length=1, max_length=80)
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]

    @model_validator(mode="after")
    @classmethod
    def name_standard(cls, values):
        if values.code not in UNIT_CODES:
            raise ValueError("code must be one of unit_codes/recommended.json keys")
        if values.name != UNIT_CODES_DATA[values.code]["name_uk"]:
            raise ValueError(f'name must be from unit_codes/recommended.json for {values["code"]}')
        return values


class Value(BaseModel):
    amount: Union[float, int]
    currency: str = Field(..., pattern=r"^[A-Z]{3}$")
    valueAddedTaxIncluded: bool = True


class Period(BaseModel):
    durationInDays: Optional[int] = Field(None, example=1)
    startDate: Optional[datetime] = Field(None, example=datetime(2020, 1, 1))
    endDate: Optional[datetime] = Field(None, example=datetime(2020, 1, 1))


class BaseImage(BaseModel):
    url: AnyUrl
    size: Optional[int] = Field(None, example=100)
    hash: Optional[str] = Field(None, pattern=r"^md5:[0-9a-z]{32}$", example="md5:0000000000000000000000000000000")


ImageResponse = Response[BaseImage]


class Image(BaseModel):
    url: str = Field(..., min_length=1)
    sizes: Optional[str] = Field(None, pattern=r"^[0-9]{2,4}x[0-9]{2,4}$", example="string")
    title: Optional[str] = Field(None, min_length=1, max_length=250, example="string")
    format: Optional[str] = Field(None, pattern=r"^image/[a-z]{2,10}$", example="image/immage1")
    hash: Optional[str] = Field(None, pattern=r"^md5:[0-9a-f]{32}$", example="md5:0000000000000000000000000000000")

    @field_validator('url')
    def valid_url(cls, v):
        if not v.startswith(IMG_PATH):
            raise ValueError(f"Invalid url, should start with {IMG_PATH}")
        return v


class Classification(BaseModel):
    id: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=250)
    scheme: str = Field(..., min_length=1, max_length=10)


class Address(BaseModel):
    countryName: str = Field(..., min_length=1, max_length=80)
    locality: str = Field(..., min_length=1, max_length=80)
    postalCode: str = Field(..., min_length=1, max_length=20)
    region: str = Field(..., min_length=1, max_length=80)
    streetAddress: str = Field(..., min_length=1, max_length=250)

    @field_validator('region')
    def region_standard(cls, v, values):
        country_name = values.data.get("countryName")
        if country_name == UKRAINE_COUNTRY_NAME_UK and v not in UA_REGIONS:
            raise ValueError("must be one of classifiers/ua_regions.json")
        return v

    @field_validator('countryName')
    def country_standard(cls, v):
        if v not in COUNTRY_NAMES_UK:
            raise ValueError("must be one of classifiers/countries.json")
        return v


class OfferSuppliersAddress(Address):
    locality: Optional[Annotated[str, StringConstraints(max_length=80)]] = Field(None, example="string")


class OfferDeliveryAddress(Address):  # only countryName is required
    locality: Optional[Annotated[str, StringConstraints(max_length=80)]] = Field(None, example="string")
    postalCode: Optional[Annotated[str, StringConstraints(max_length=20)]] = Field(None, example="string")
    region: Optional[Annotated[str, StringConstraints(max_length=80)]] = Field(None, example="string")
    streetAddress: Optional[Annotated[str, StringConstraints(max_length=250)]] = Field(None, example="string")

    @field_validator('region')
    def region_for_ukraine_only(cls, v, values):
        country_name = values.data.get("countryName")
        if country_name != UKRAINE_COUNTRY_NAME_UK and v:
            raise ValueError("can be provided only for Ukraine")
        return v


class ContactPoint(BaseModel):
    name: str = Field(..., min_length=1, max_length=250)
    telephone: str = Field(..., max_length=250)
    url: Optional[str] = Field(None, max_length=250, example="string")
    email: Optional[str] = Field(None, max_length=250, example="string")
    faxNumber: Optional[str] = Field(None, max_length=250, example="string")

    @field_validator('telephone')
    def telephone_format(cls, v):
        if not re.match(r"^(\+)?[0-9]{2,}(,( )?(\+)?[0-9]{2,})*$", v):
            raise ValueError("Invalid phone format")
        return v


class Identifier(BaseModel):
    id: str = Field(..., min_length=4, max_length=50)
    legalName: str = Field(..., min_length=1, max_length=250)
    scheme: str = Field(..., min_length=1, max_length=20)


class ProcuringEntityKind(str, Enum):
    central = "central"
    regional = "regional"


class Organization(BaseModel):
    name: str = Field(..., min_length=1, max_length=250)
    address: Address
    contactPoint: ContactPoint
    identifier: Identifier


class ProcuringEntity(Organization):
    kind: ProcuringEntityKind


class BaseAdministratorIdentifier(BaseModel):
    id: str = Field(..., min_length=4, max_length=50)
    scheme: str = Field(..., min_length=1, max_length=20)

    @field_validator("scheme")
    def scheme_standard(cls, v):
        if v not in ORA_CODES:
            raise ValueError("must be one of organizations/identifier_scheme.json codes")
        return v


class MarketAdministratorIdentifier(BaseAdministratorIdentifier):
    legalName_en: str = Field(..., min_length=1, max_length=250)
    legalName_uk: str = Field(..., min_length=1, max_length=250)


class CategoryAdministratorIdentifier(BaseAdministratorIdentifier):
    legalName: str = Field(..., min_length=1, max_length=250)


class MarketAdministrator(BaseModel):
    identifier: MarketAdministratorIdentifier

    @field_validator('identifier')
    def entity_is_market_administrator(cls, value):
        identifier = value.id
        if identifier not in ADMINISTRATOR_IDENTIFIERS:
            raise ValueError("must be one of market administrators")
        return value


class CategoryMarketAdministrator(MarketAdministrator, ProcuringEntity):
    identifier: CategoryAdministratorIdentifier


class SuccessResponse(BaseModel):
    result: str = Field(..., example="success")
