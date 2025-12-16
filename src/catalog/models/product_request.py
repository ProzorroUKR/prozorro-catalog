from datetime import datetime
from typing import Optional, List, Union
from uuid import uuid4

from pydantic import Field, field_validator

from catalog.models.base import BaseModel
from catalog.models.api import Input, Response, CreateResponse
from catalog.models.common import MarketAdministrator, MarketAdministratorIdentifier, CategoryMarketAdministrator
from catalog.models.product import ProductCreateData, Product
from catalog.models.document import DocumentPostData, Document, DOCUMENT_EXAMPLE
from catalog.models.vendor import VendorOrganization
import standards


REJECT_REASONS = standards.load("market/product_reject_reason.json")


class RequestReviewPostData(BaseModel):
    administrator: MarketAdministrator


class RequestRejectionPostData(RequestReviewPostData):
    reason: List[str] = Field(..., min_length=1)
    description: Optional[str] = Field(None, min_length=1, max_length=2000, example="description")

    @field_validator('reason')
    def reason_standard(cls, v):
        for reason in v:
            if reason not in REJECT_REASONS:
                raise ValueError(f"invalid value: '{reason}'. Must be one of market/product_reject_reason.json keys")
        if len(v) != len(set(v)):
            raise ValueError("there are duplicated reasons")
        return v


class RequestReview(RequestReviewPostData):
    date: datetime


REQUEST_REVIEW_EXAMPLE = RequestReview(
    date=datetime.now().isoformat(),
    administrator=MarketAdministrator(
        identifier=MarketAdministratorIdentifier(
            id="42574629",
            scheme="UA-EDR",
            legalName_en="STATE ENTERPRISE \"MEDICAL PROCUREMENT OF UKRAINE\"",
            legalName_uk="ДЕРЖАВНЕ ПІДПРИЄМСТВО \"МЕДИЧНІ ЗАКУПІВЛІ УКРАЇНИ\""
        )
    )
).model_dump(exclude_none=True)


class RequestRejection(RequestRejectionPostData, RequestReview):
    pass


REQUEST_REJECTION_EXAMPLE = RequestRejection(
    date=datetime.now().isoformat(),
    administrator=MarketAdministrator(
        identifier=MarketAdministratorIdentifier(
            id="42574629",
            scheme="UA-EDR",
            legalName_en="STATE ENTERPRISE \"MEDICAL PROCUREMENT OF UKRAINE\"",
            legalName_uk="ДЕРЖАВНЕ ПІДПРИЄМСТВО \"МЕДИЧНІ ЗАКУПІВЛІ УКРАЇНИ\""
        )
    ),
    reason=["invalidTitle",],
).model_dump(exclude_none=True)


class ProductRequestPostData(BaseModel):
    product: ProductCreateData
    documents: Optional[List[DocumentPostData]] = Field(None, example=[DOCUMENT_EXAMPLE])

    @property
    def id(self):
        return uuid4().hex


class ProductRequest(BaseModel):
    id: str = Field(..., min_length=32, max_length=32)
    dateModified: datetime
    dateCreated: datetime
    owner: str
    acception: Optional[RequestReview] = Field(None, example=[REQUEST_REVIEW_EXAMPLE])
    rejection: Optional[RequestRejection] = Field(None, example=[REQUEST_REJECTION_EXAMPLE])
    documents: Optional[List[Document]] = Field(None, example=[DOCUMENT_EXAMPLE])
    product: ProductCreateData


class ProductRequestSwaggerResponse(ProductRequest):
    contributor: VendorOrganization
    marketAdministrator: CategoryMarketAdministrator


class ProductRequestSuccessful(ProductRequest):
    contributor_id: str = Field(..., min_length=32, max_length=32)
    product: Product


ProductRequestPostInput = Input[ProductRequestPostData]
ProductRequestResponse = Response[ProductRequestSwaggerResponse]
ProductRequestAcceptionPostInput = Input[RequestReviewPostData]
ProductRequestRejectionPostInput = Input[RequestRejectionPostData]
ProductRequestReviewCreateResponse = CreateResponse[ProductRequestSuccessful]
