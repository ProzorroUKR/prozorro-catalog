import re
import random
from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPBadRequest, HTTPNotFound, HTTPConflict
from pymongo.errors import OperationFailure

from catalog import db
from catalog.models.base import unchanged
from catalog.models.product import ProductCreateInput, ProductUpdateInput, Product
from catalog.models.profile import Profile
from catalog.swagger import class_view_swagger_path
from catalog.utils import pagination_params, get_now, requests_sequence_params, async_retry
from catalog.auth import validate_access_token, validate_accreditation, set_access_token


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
        if not product:
            raise HTTPNotFound(text="Not found")
        return {"data": product}

    @classmethod
    async def put(cls, request, product_id):
        validate_accreditation(request, "product")
        # import and validate data
        json = await request.json()
        body = ProductCreateInput(**json)
        # export data back to dict
        data = body.data.dict_without_none()
        if product_id != data['id']:
            raise HTTPBadRequest(text='id mismatch')

        profile_id = data['relatedProfile']
        profile = await db.read_profile(profile_id)  # ensure exists
        if data['classification']['id'][:4] != profile['classification']['id'][:4]:
            raise HTTPBadRequest(text='product and profile classification mismatch')

        ###
        try:
            Profile.validate_product(profile, data)
        except ValueError as e:
            raise HTTPBadRequest(text=e.args[0])
        ##

        access = set_access_token(request, data)
        data['dateModified'] = get_now().isoformat()
        await db.insert_product(data)

        data.pop("access")
        response = {"data": data, "access": access}
        return response

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def patch(cls, request, product_id):
        validate_accreditation(request, "product")
        async with db.read_and_update_product(product_id) as product:
            # import and validate data
            json = await request.json()
            body = ProductUpdateInput(**json)

            validate_access_token(request, product, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            product.update(data)
            data['dateModified'] = get_now().isoformat()

        product.pop("access")
        return {"data": product}
