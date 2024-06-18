from datetime import datetime
from typing import Optional, List
from uuid import uuid4

from pydantic import Field, validator

from catalog.models.base import BaseModel
from catalog.models.api import Input, Response, ListResponse
from catalog.models.common import MarketAdministrator
from catalog.models.document import DocumentPostData, Document
from catalog.utils import get_now
import standards


BAN_REASONS = standards.load("market/ban_reason.json")


class BanPostData(BaseModel):
    reason: str
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    dueDate: Optional[datetime]
    administrator: MarketAdministrator
    documents: Optional[List[DocumentPostData]]

    @property
    def id(self):
        return uuid4().hex

    @validator('dueDate')
    def validate_date(cls, v):
        if v and isinstance(v, datetime):
            if v < get_now():
                raise ValueError("should be greater than now")
            return v.isoformat()

    @validator('reason')
    def reason_standard(cls, v):
        if v not in BAN_REASONS:
            raise ValueError("must be one of market/ban_reason.json keys")
        return v


class Ban(BaseModel):
    id: str = Field(..., min_length=32, max_length=32)
    reason: str
    description: Optional[str] = Field(None, min_length=1, max_length=500)
    dueDate: Optional[datetime]
    administrator: MarketAdministrator
    dateCreated: datetime
    dateModified: datetime
    owner: str
    documents: Optional[List[Document]]


BanPostInput = Input[BanPostData]
BanResponse = Response[Ban]
BanList = ListResponse[Ban]
