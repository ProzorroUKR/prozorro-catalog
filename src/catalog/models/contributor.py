from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from pydantic import Field, validator, model_validator

from catalog.models.ban import Ban
from catalog.models.base import BaseModel
from catalog.models.api import Input, Response
from catalog.models.common import UKRAINE_COUNTRY_NAME_UK
from catalog.models.vendor import PostVendorOrganization, VendorOrganization, PostVendorAddress
from catalog.models.document import Document, DocumentPostData


class PostContributorAddress(PostVendorAddress):
    region: Optional[str] = Field(None, min_length=1, max_length=80, example="string")

    @model_validator(mode="before")
    @classmethod
    def check_ua_region(cls, values):
        if values.get("countryName") == UKRAINE_COUNTRY_NAME_UK and not values.get("region"):
            raise ValueError(f"region is required for countryName {UKRAINE_COUNTRY_NAME_UK}")
        return values


class PostContributorOrganization(PostVendorOrganization):
    address: PostContributorAddress


class ContributorPostData(BaseModel):
    contributor: PostContributorOrganization
    documents: Optional[List[DocumentPostData]] = Field(
        None,
        example=[{
            "id": uuid4().hex,
            "title": "name.doc",
            "url": "/documents/name.doc",
            "hash": f"md5:{uuid4().hex}",
            "format": "application/msword",
        }]
    )

    @property
    def id(self):
        return uuid4().hex


class Contributor(BaseModel):
    id: str = Field(..., min_length=32, max_length=32)
    contributor: VendorOrganization
    dateModified: datetime
    dateCreated: datetime
    owner: str
    bans: Optional[List[Ban]] = Field(
        None,
        example=[{
            "id": "string",
            "reason": "string",
            "marketAdministrator": {
                "identifier": {
                    "id": "string",
                    "scheme": "string",
                }
            }
        }],
    )
    documents: Optional[List[Document]] = Field(
        None,
        example=[{
            "id": uuid4().hex,
            "title": "name.doc",
            "url": "/documents/name.doc",
            "hash": f"md5:{uuid4().hex}",
            "format": "application/msword",
        }]
    )


ContributorPostInput = Input[ContributorPostData]
ContributorResponse = Response[Contributor]
