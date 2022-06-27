import random
from uuid import uuid4
from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPConflict
from pymongo.errors import OperationFailure
from catalog import db
from catalog.swagger import class_view_swagger_path
from catalog.auth import set_access_token, validate_accreditation, validate_access_token
from catalog.utils import pagination_params, get_now, async_retry
from catalog.models.vendor import VendorPostInput, VendorPatchInput
from catalog.serializers.base import RootSerializer


@class_view_swagger_path('/app/swagger/vendors')
class VendorView(View):

    @classmethod
    async def collection_get(cls, request):
        offset, limit, reverse = pagination_params(request)
        response = await db.find_vendors(
            offset=offset,
            limit=limit,
            reverse=reverse,
        )
        return response

    @classmethod
    async def get(cls, request, vendor_id):
        obj = await db.read_vendor(vendor_id)
        return {"data": RootSerializer(obj).data}

    @classmethod
    async def post(cls, request):
        # validate_accreditation(request, "vendor")
        # import and validate data
        json = await request.json()
        body = VendorPostInput(**json)

        data = body.data.dict_without_none()
        access = set_access_token(request, data)
        data['id'] = uuid4().hex
        data['dateCreated'] = data['dateModified'] = get_now().isoformat()
        await db.insert_vendor(data)
        response = {"data": RootSerializer(data).data,
                    "access": access}
        return response

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def patch(cls, request, vendor_id):
        # validate_accreditation(request, "category")
        async with db.read_and_update_vendor(vendor_id) as vendor:
            # import and validate data
            json = await request.json()
            body = VendorPatchInput(**json)

            validate_access_token(request, vendor, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            initial_data = dict(vendor)
            vendor.update(data)

            if initial_data != vendor:
                data['dateModified'] = get_now().isoformat()
        return {"data": RootSerializer(vendor).data}
