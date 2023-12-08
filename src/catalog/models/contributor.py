from datetime import datetime
from typing import Optional, List
from pydantic import Field, validator, root_validator

from catalog.models.ban import Ban
from catalog.models.base import BaseModel
from catalog.models.api import Input, Response
from catalog.models.common import UKRAINE_COUNTRY_NAME_UK, UA_REGIONS, COUNTRY_NAMES_UK
from catalog.models.vendor import PostVendorOrganization, VendorOrganization, PostVendorAddress
from catalog.models.document import Document, DocumentPostData


class PostContributorAddress(PostVendorAddress):
    region: Optional[str] = Field(None, min_length=1, max_length=80)

    @root_validator(pre=True)
    def check_ua_region(cls, values):
        if values["countryName"] == UKRAINE_COUNTRY_NAME_UK and not values.get("region"):
            raise ValueError(f"region is required for countryName {UKRAINE_COUNTRY_NAME_UK}")
        return values


class PostContributorOrganization(PostVendorOrganization):
    address: PostContributorAddress


class ContributorPostData(BaseModel):
    contributor: PostContributorOrganization
    documents: Optional[List[DocumentPostData]]


class Contributor(ContributorPostData):
    id: str = Field(..., min_length=32, max_length=32)
    contributor: VendorOrganization
    dateModified: datetime
    dateCreated: datetime
    owner: str
    bans: Optional[List[Ban]]
    documents: Optional[List[Document]]


ContributorPostInput = Input[ContributorPostData]
ContributorResponse = Response[Contributor]
