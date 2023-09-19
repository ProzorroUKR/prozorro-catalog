from datetime import datetime
from typing import Optional, List
from pydantic import Field, validator

from catalog.models.base import BaseModel
from catalog.models.api import Input, Response, CreateResponse
from catalog.models.common import MarketAdministrator
from catalog.models.document import DocumentPostData, PublishedDocument


class BanPostData(BaseModel):
    reason: str
    description: str
    dueDate: Optional[datetime]
    administrator: MarketAdministrator
    documents: List[DocumentPostData]

    @validator('dueDate')
    def validate_date(cls, v):
        if v and isinstance(v, datetime):
            return v.isoformat()


class Ban(BanPostData):
    id: str = Field(..., min_length=32, max_length=32)
    dateCreated: datetime
    owner: str
    documents: List[PublishedDocument]


BanPostInput = Input[BanPostData]
BanResponse = Response[Ban]
BanCreateResponse = CreateResponse[Ban]
