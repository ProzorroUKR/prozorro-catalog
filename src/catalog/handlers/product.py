import random
from copy import deepcopy
from uuid import uuid4

from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPConflict, HTTPNotFound
from pymongo.errors import OperationFailure

from catalog import db
from catalog.models.product import ProductStatus, ProductCreateInput, ProductUpdateInput
from catalog.swagger import class_view_swagger_path
from catalog.utils import pagination_params, get_now, async_retry
from catalog.auth import validate_access_token, validate_accreditation, set_access_token
from catalog.serializers.product import ProductSerializer
from catalog.validations import (
    validate_product_to_category,
    validate_product_to_profile,
    validate_patch_vendor_product,
    validate_medicine_additional_classifications,
)


@class_view_swagger_path('/app/swagger/products')
class ProductView(View):

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
        vendor = None
        if "vendor" in product:
            try:
                vendor = await db.read_vendor(product["vendor"]["id"])
            except HTTPNotFound:
                pass

        return {"data": ProductSerializer(product, vendor=vendor).data}

    @classmethod
    async def post(cls, request):
        validate_accreditation(request, "product")
        # import and validate data
        json = await request.json()
        body = ProductCreateInput(**json)
        # export data back to dict
        data = body.data.dict_without_none()
        data["id"] = uuid4().hex

        category_id = data["relatedCategory"]
        profile_ids = data.get("relatedProfiles", "")
        category = await db.read_category(category_id)  # ensure exists
        validate_access_token(request, category, body.access)
        validate_product_to_category(category, data)
        for profile_id in profile_ids:
            profile = await db.read_profile(profile_id)
            validate_product_to_profile(profile, data)
        await validate_medicine_additional_classifications(data)

        access = set_access_token(request, data)
        data["dateModified"] = get_now().isoformat()
        await db.insert_product(data)

        return {"data": ProductSerializer(data).data,
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
            category_id = data.get("relatedCategory") or product['relatedCategory']
            category = await db.read_category(category_id)

            # update profile with valid data
            data['dateModified'] = get_now().isoformat()
            product_before = deepcopy(product)
            product.update(data)
            if product.get("status", ProductStatus.active) != ProductStatus.hidden:
                validate_product_to_category(category, product, product_before)
                profile_ids = product.get("relatedProfiles", "")
                for profile_id in profile_ids:
                    profile = await db.read_profile(profile_id)
                    validate_product_to_profile(profile, product)
            if product_before.get("additionalClassifications", "") != product.get("additionalClassifications", ""):
                await validate_medicine_additional_classifications(product)

        return {"data": ProductSerializer(product).data}
