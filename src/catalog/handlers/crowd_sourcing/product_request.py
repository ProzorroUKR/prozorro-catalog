import logging
from typing import Union, Optional

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401
from catalog.auth import set_access_token, validate_accreditation

from catalog import db
from catalog.models.api import ErrorResponse, PaginatedList
from catalog.models.product_request import (
    ProductRequestPostInput,
    ProductRequestRejectionPostInput,
    ProductRequestAcceptionPostInput, ProductRequestResponse, ProductRequestReviewCreateResponse,
)
from catalog.serializers.product_request import ProductRequestSerializer
from catalog.state.product_request import ProductRequestState
from catalog.validations import (
    validate_product_to_category,
    validate_contributor_banned_categories,
    validate_previous_product_reviews,
    validate_category_administrator,
)
from catalog.utils import pagination_params, get_now


logger = logging.getLogger(__name__)


class ContributorProductRequestView(PydanticView):
    state = ProductRequestState

    async def post(
        self, contributor_id: str, /, body: ProductRequestPostInput,
    ) -> Union[r201[ProductRequestResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Create a contributor product request

        Security: Basic: []
        Tags: Contributor/ProductRequest
        """
        validate_accreditation(self.request, "contributors")
        contributor = await db.read_contributor(contributor_id)
        data = body.data.dict_without_none()

        # category validations
        category = await db.read_category(data["product"]["relatedCategory"])
        validate_product_to_category(category, data["product"])
        validate_contributor_banned_categories(category, contributor)

        data["contributor_id"] = contributor["id"]
        await self.state.on_post(data, category)
        await db.insert_product_request(data)

        logger.info(
            f"Created contributor product request {data['id']}",
            extra={
                "MESSAGE_ID": f"contributor_product_request_create",
                "contributor_product_request_id": data["id"],
            },
        )

        return {"data": ProductRequestSerializer(data, category=category).data}


class ProductRequestView(PydanticView):

    async def get(
        self, /, offset: Optional[str] = None,  limit: Optional[int] = 100, descending: Optional[int] = 0, opt_fields: Optional[str] = None,
    ) -> r200[PaginatedList]:
        """
        Get list of product requests

        Tags: Contributor/ProductRequest
        """
        if opt_fields:
            opt_fields = opt_fields.split(",")
        offset, limit, reverse = pagination_params(self.request)
        response = await db.find_product_requests(
            offset=offset,
            limit=limit,
            reverse=reverse,
            opt_fields=opt_fields,
        )
        return response


class ProductRequestItemView(PydanticView):
    async def get(
        self, request_id: str, /,
    ) -> Union[r200[ProductRequestResponse], r400[ErrorResponse], r404[ErrorResponse]]:
        """
        Get product request

        Tags: Contributor/ProductRequest
        """
        obj = await db.read_product_request(request_id)
        category = await db.read_category(
            category_id=obj["product"].get("relatedCategory"),
            projection={"criteria": 1},
        )
        return {"data": ProductRequestSerializer(obj, category=category).data}


class ProductRequestAcceptionView(PydanticView):
    state = ProductRequestState

    async def post(
        self, request_id: str, /, body: ProductRequestAcceptionPostInput,
    ) -> Union[r201[ProductRequestReviewCreateResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Accept product request

        Security: Basic: []
        Tags: Contributor/ProductRequest
        """
        validate_accreditation(self.request, "category")
        async with db.read_and_update_product_request(request_id) as product_request:
            validate_previous_product_reviews(product_request)
            # export data back to dict
            data = body.data.dict_without_none()
            category = await db.read_category(product_request.get("product", {}).get("relatedCategory"))
            validate_category_administrator(data, category)
            # update product request with valid data
            acceptation_date = get_now().isoformat()
            data["date"] = acceptation_date
            product_request.update({"acception": data})
            await self.state.on_accept(product_request, category, acceptation_date)

            logger.info(
                f"Updated product request {request_id}",
                extra={"MESSAGE_ID": f"product_request_acception_update"},
            )

        # add product to the market
        access = set_access_token(self.request, product_request["product"])
        await db.insert_product(product_request["product"])

        logger.info(
            f"Created product {product_request['product']['id']}",
            extra={
                "MESSAGE_ID": f"product_request_product_create",
                "product_id": product_request['product']['id'],
            },
        )

        return {
            "data": ProductRequestSerializer(product_request, category=category).data,
            "access": access,
        }


class ProductRequestRejectionView(PydanticView):
    state = ProductRequestState

    async def post(
        self, request_id: str, /, body: ProductRequestRejectionPostInput,
    ) -> Union[r201[ProductRequestResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Reject product request

        Security: Basic: []
        Tags: Contributor/ProductRequest
        """
        validate_accreditation(self.request, "category")
        async with db.read_and_update_product_request(request_id) as product_request:
            validate_previous_product_reviews(product_request)
            # export data back to dict
            data = body.data.dict_without_none()
            category = await db.read_category(product_request.get("product", {}).get("relatedCategory"))
            validate_category_administrator(data, category)
            # update product request with valid data
            modified_date = get_now().isoformat()
            data["date"] = modified_date
            product_request.update({"rejection": data, "dateModified": modified_date})

            logger.info(
                f"Updated product request {request_id}",
                extra={"MESSAGE_ID": f"product_request_rejection_update"},
            )

        return {"data": ProductRequestSerializer(product_request, category=category).data}
