from datetime import datetime
from typing import Optional, List
from pydantic import Field, validator

from catalog.models.base import BaseModel
from catalog.models.api import Input, Response, CreateResponse
from catalog.models.common import MarketAdministrator
from catalog.models.document import DocumentPostData, Document
from catalog.utils import get_now
import standards


BAN_REASONS = standards.load("market/ban_reason.json")


class BanPostData(BaseModel):
    reason: str
    description: str
    dueDate: Optional[datetime]
    administrator: MarketAdministrator
    documents: Optional[List[DocumentPostData]]

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

    @validator('description')
    def validate_description(cls, v, values):
        reason_description = BAN_REASONS.get(values.get("reason"), {})
        if reason_description.get("title_uk") and v != reason_description["title_uk"]:
            raise ValueError(f"must equal {reason_description['title_uk']}")
        return v


class Ban(BanPostData):
    id: str = Field(..., min_length=32, max_length=32)
    dateCreated: datetime
    dateModified: datetime
    owner: str
    documents: Optional[List[Document]]


BanPostInput = Input[BanPostData]
BanResponse = Response[Ban]
BanCreateResponse = CreateResponse[Ban]
