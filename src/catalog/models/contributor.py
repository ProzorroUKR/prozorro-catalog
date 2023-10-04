from datetime import datetime
from typing import Optional, List
from pydantic import Field

from catalog.models.ban import Ban
from catalog.models.base import BaseModel
from catalog.models.api import Input, Response, CreateResponse
from catalog.models.common import ContactPoint
from catalog.models.vendor import VendorOrganization
from catalog.models.document import Document, DocumentPostData


class ContributorContactPoint(ContactPoint):
    email: str = Field(..., min_length=1, max_length=250)


class ContributorOrganization(VendorOrganization):
    contactPoint: ContributorContactPoint


class ContributorPostData(BaseModel):
    contributor: ContributorOrganization
    documents: Optional[List[DocumentPostData]]


class Contributor(ContributorPostData):
    id: str = Field(..., min_length=32, max_length=32)
    dateModified: datetime
    dateCreated: datetime
    owner: str
    bans: Optional[List[Ban]]
    documents: Optional[List[Document]]


ContributorPostInput = Input[ContributorPostData]
ContributorResponse = Response[Contributor]
ContributorCreateResponse = CreateResponse[Contributor]
