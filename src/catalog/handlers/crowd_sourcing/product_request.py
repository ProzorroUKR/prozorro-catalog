import logging

from aiohttp.web_urldispatcher import View
from catalog.auth import set_access_token, validate_accreditation

from catalog import db
from catalog.models.product_request import (
    ProductRequestPostInput,
    ProductRequestRejectionPostInput,
    ProductRequestAcceptionPostInput,
)
from catalog.serializers.product_request import ProductRequestSerializer
from catalog.settings import CRITERIA_LIST
from catalog.state.product_request import ProductRequestState
from catalog.swagger import class_view_swagger_path
from catalog.handlers.base import BaseView
from catalog.validations import (
    validate_product_to_category,
    validate_contributor_banned_categories,
    validate_previous_product_reviews,
    validate_category_administrator,
)
from catalog.utils import pagination_params, get_now


logger = logging.getLogger(__name__)


@class_view_swagger_path('/app/swagger/crowd_sourcing/contributors/product_request')
class ContributorProductRequestView(BaseView):
    state = ProductRequestState

    @classmethod
    async def post(cls, request, **kwargs):
        validate_accreditation(request, "contributors")
        contributor = await db.read_contributor(kwargs.get("contributor_id"))
        # import and validate data
        json = await request.json()
        body = ProductRequestPostInput(**json)
        data = body.data.dict_without_none()

        # category validations
        category = await db.read_category(data["product"]["relatedCategory"])
        validate_product_to_category(category, data["product"], required_criteria=CRITERIA_LIST)
        validate_contributor_banned_categories(category, contributor)

        data["contributor_id"] = contributor["id"]
        await cls.state.on_post(data, category)
        await db.insert_product_request(data)

        logger.info(
            f"Created contributor product request {data['id']}",
            extra={
                "MESSAGE_ID": f"contributor_product_request_create",
                "contributor_product_request_id": data["id"],
            },
        )

        return {"data": ProductRequestSerializer(data, category=category).data}


@class_view_swagger_path('/app/swagger/crowd_sourcing/product_requests')
class ProductRequestView(View):
    @classmethod
    async def collection_get(cls, request):
        opt_fields = request.query.get("opt_fields")
        if opt_fields:
            opt_fields = opt_fields.split(",")
        offset, limit, reverse = pagination_params(request)
        response = await db.find_product_requests(
            offset=offset,
            limit=limit,
            reverse=reverse,
            opt_fields=opt_fields,
        )
        return response

    @classmethod
    async def get(cls, request, request_id):
        obj = await db.read_product_request(request_id)
        category = await db.read_category(
            category_id=obj["product"].get("relatedCategory"),
            projection={"criteria": 1},
        )
        return {"data": ProductRequestSerializer(obj, category=category).data}


@class_view_swagger_path('/app/swagger/crowd_sourcing/product_requests/accept')
class ProductRequestAcceptionView(BaseView):
    state = ProductRequestState

    @classmethod
    async def post(cls, request, **kwargs):
        validate_accreditation(request, "category")
        request_id = kwargs.get("request_id")
        async with db.read_and_update_product_request(request_id) as product_request:
            # import and validate data
            json = await request.json()
            body = ProductRequestAcceptionPostInput(**json)
            validate_previous_product_reviews(product_request)
            # export data back to dict
            data = body.data.dict_without_none()
            category = await db.read_category(product_request.get("product", {}).get("relatedCategory"))
            validate_category_administrator(data, category)
            # update product request with valid data
            acceptation_date = get_now().isoformat()
            data["date"] = acceptation_date
            product_request.update({"acception": data})
            await cls.state.on_accept(product_request, category, acceptation_date)

            logger.info(
                f"Updated product request {request_id}",
                extra={"MESSAGE_ID": f"product_request_acception_update"},
            )

        # add product to the market
        access = set_access_token(request, product_request["product"])
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


@class_view_swagger_path('/app/swagger/crowd_sourcing/product_requests/reject')
class ProductRequestRejectionView(BaseView):
    state = ProductRequestState

    @classmethod
    async def post(cls, request, **kwargs):
        validate_accreditation(request, "category")
        request_id = kwargs.get("request_id")
        async with db.read_and_update_product_request(request_id) as product_request:
            # import and validate data
            json = await request.json()
            body = ProductRequestRejectionPostInput(**json)
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
