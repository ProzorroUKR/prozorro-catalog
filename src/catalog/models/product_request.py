from datetime import datetime
from typing import Optional, List, Union
from uuid import uuid4

from pydantic import Field, validator

from catalog.models.base import BaseModel
from catalog.models.api import Input, Response, CreateResponse
from catalog.models.common import MarketAdministrator
from catalog.models.product import ProductCreateData, Product
from catalog.models.document import DocumentPostData, Document
import standards


REJECT_REASONS = standards.load("market/product_reject_reason.json")


class RequestReviewPostData(BaseModel):
    administrator: MarketAdministrator


class RequestRejectionPostData(RequestReviewPostData):
    reason: List[str] = Field(..., min_items=1)
    description: Optional[str] = Field(None, min_length=1, max_length=2000)

    @validator('reason')
    def reason_standard(cls, values):
        for reason in values:
            if reason not in REJECT_REASONS:
                raise ValueError(f"invalid value: '{reason}'. Must be one of market/product_reject_reason.json keys")
        if len(values) != len(set(values)):
            raise ValueError("there are duplicated reasons")
        return values


class RequestReview(RequestReviewPostData):
    date: datetime


class RequestRejection(RequestRejectionPostData, RequestReview):
    pass


class ProductRequestPostData(BaseModel):
    product: ProductCreateData
    documents: Optional[List[DocumentPostData]]

    @property
    def id(self):
        return uuid4().hex


class ProductRequest(BaseModel):
    id: str = Field(..., min_length=32, max_length=32)
    contributor_id: str = Field(..., min_length=32, max_length=32)
    dateModified: datetime
    dateCreated: datetime
    owner: str
    acception: Optional[RequestReview]
    rejection: Optional[RequestRejection]
    documents: Optional[List[Document]]
    product: ProductCreateData


class ProductRequestSuccessful(ProductRequest):
    product: Product


ProductRequestPostInput = Input[ProductRequestPostData]
ProductRequestResponse = Response[ProductRequest]
ProductRequestAcceptionPostInput = Input[RequestReviewPostData]
ProductRequestRejectionPostInput = Input[RequestRejectionPostData]
ProductRequestReviewCreateResponse = CreateResponse[ProductRequestSuccessful]
