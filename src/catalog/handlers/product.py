import random
from copy import deepcopy

from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPConflict, HTTPNotFound
from pymongo.errors import OperationFailure

from catalog import db
from catalog.models.product import ProductCreateInput, ProductUpdateInput
from catalog.swagger import class_view_swagger_path
from catalog.utils import pagination_params, get_now, async_retry
from catalog.auth import validate_access_token, validate_accreditation, set_access_token
from catalog.serializers.product import ProductSerializer
from catalog.validations import validate_patch_vendor_product
from catalog.state.product import ProductState


@class_view_swagger_path('/app/swagger/products')
class ProductView(View):

    state_class = ProductState

    @classmethod
    async def collection_get(cls, request):
        offset, limit, reverse = pagination_params(request)
        response = await db.find_products(
            offset=offset,
            limit=limit,
            reverse=reverse,
        )
        return response

    @classmethod
    async def get(cls, request, product_id):
        product = await db.read_product(product_id)
        category = await db.read_category(
            category_id=product.get("relatedCategory"),
            projection={"criteria": 1},
        )

        vendor = None
        if "vendor" in product:
            try:
                vendor = await db.read_vendor(product["vendor"]["id"])
            except HTTPNotFound:
                pass

        return {"data": ProductSerializer(product, vendor=vendor, category=category).data}

    @classmethod
    async def post(cls, request):
        validate_accreditation(request, "product")
        # import and validate data
        json = await request.json()
        body = ProductCreateInput(**json)
        # export data back to dict
        data = body.data.dict_without_none()

        category_id = data["relatedCategory"]
        category = await db.read_category(category_id)  # ensure exists
        validate_access_token(request, category, body.access)

        await cls.state_class.on_post(data, category)

        access = set_access_token(request, data)
        data["dateModified"] = get_now().isoformat()
        await db.insert_product(data)

        return {"data": ProductSerializer(data, category=category).data,
                "access": access}

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def patch(cls, request, product_id):
        validate_accreditation(request, "product")
        async with db.read_and_update_product(product_id) as product:
            # import and validate data
            json = await request.json()
            body = ProductUpdateInput(**json)
            validate_patch_vendor_product(product)
            validate_access_token(request, product, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            product_before = deepcopy(product)
            data['dateModified'] = get_now().isoformat()
            product.update(data)
            category = await db.read_category(product["relatedCategory"])
            await cls.state_class.on_patch(product_before, product)

        return {"data": ProductSerializer(product, category=category).data}
