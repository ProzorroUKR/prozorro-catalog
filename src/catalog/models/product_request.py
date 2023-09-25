from datetime import datetime
from typing import Optional, List, Union
from pydantic import Field

from catalog.models.base import BaseModel
from catalog.models.api import AuthorizedInput, Input, Response, CreateResponse
from catalog.models.common import MarketAdministrator
from catalog.models.product import ProductCreateData, Product
from catalog.models.document import DocumentPostData, Document


class RequestReviewPostData(BaseModel):
    administrator: MarketAdministrator


class RequestRejectionPostData(RequestReviewPostData):
    reason: str
    description: str


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
