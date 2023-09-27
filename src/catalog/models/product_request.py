from datetime import datetime
from typing import Optional, List, Union
from pydantic import Field, validator

from catalog.models.base import BaseModel
from catalog.models.api import AuthorizedInput, Input, Response, CreateResponse
from catalog.models.common import MarketAdministrator
from catalog.models.product import ProductCreateData, Product
from catalog.models.document import DocumentPostData, Document
import standards


REJECT_REASONS = standards.load("market/product_reject_reason.json")


class RequestReviewPostData(BaseModel):
    administrator: MarketAdministrator


class RequestRejectionPostData(RequestReviewPostData):
    reason: str
    description: str

    @validator('reason')
    def reason_standard(cls, v):
        if v not in REJECT_REASONS:
            raise ValueError("must be one of market/product_reject_reason.json keys")
        return v

    @validator('description')
    def validate_description(cls, v, values):
        reason_description = REJECT_REASONS.get(values.get("reason"), {})
        if reason_description.get("title_uk") and v != reason_description["title_uk"]:
            raise ValueError(f"must equal {reason_description['title_uk']}")
        return v


class RequestReview(RequestReviewPostData):
    date: datetime


class RequestRejection(RequestRejectionPostData, RequestReview):
    pass


class ProductRequestPostData(BaseModel):
    product: ProductCreateData
    documents: Optional[List[DocumentPostData]]


class ProductRequest(ProductRequestPostData):
    id: str = Field(..., min_length=32, max_length=32)
    contributor_id: str = Field(..., min_length=32, max_length=32)
    dateModified: datetime
    dateCreated: datetime
    owner: str
    acception: Optional[RequestReview]
    rejection: Optional[RequestRejection]
    documents: Optional[List[Document]]
    product: Union[ProductCreateData, Product]


ProductRequestPostInput = AuthorizedInput[ProductRequestPostData]
ProductRequestResponse = Response[ProductRequest]
ProductRequestAcceptionPostInput = Input[RequestReviewPostData]
ProductRequestRejectionPostInput = Input[RequestRejectionPostData]
ProductRequestReviewCreateResponse = CreateResponse[ProductRequest]
