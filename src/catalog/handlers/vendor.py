import random
from uuid import uuid4
from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPConflict, HTTPBadRequest
from pymongo.errors import OperationFailure
from catalog import db
from catalog.swagger import class_view_swagger_path
from catalog.auth import set_access_token, validate_accreditation, validate_access_token
from catalog.utils import pagination_params, get_now, async_retry
from catalog.models.vendor import VendorPostInput, VendorPatchInput
from catalog.serializers.vendor import VendorSignSerializer, VendorSerializer


async def validate_vendor_identifier(action, identifier_id):
    existing = await db.find_vendors(
        offset=None,
        limit=1,
        reverse=False,
        filters={
            "isActive": True,
            "vendor.identifier.id": identifier_id,
        }
    )
    if existing["data"]:
        dup_id = existing["data"][0]["id"]
        raise HTTPBadRequest(
            text=f"Cannot {action} vendor.identifier.id {identifier_id} already exists: {dup_id}"
        )


@class_view_swagger_path('/app/swagger/vendors')
class VendorView(View):

    @classmethod
    async def collection_get(cls, request):
        offset, limit, reverse = pagination_params(request)
        response = await db.find_vendors(
            offset=offset,
            limit=limit,
            reverse=reverse,
            filters={"isActive": True}
        )
        return response

    @classmethod
    async def get(cls, request, vendor_id):
        obj = await db.read_vendor(vendor_id)
        return {"data": VendorSerializer(obj).data}

    @classmethod
    async def sign_get(cls, request, vendor_id):
        obj = await db.read_vendor(vendor_id)
        return {"data": VendorSignSerializer(obj).data}

    @classmethod
    async def post(cls, request):
        # validate_accreditation(request, "vendor")
        # import and validate data
        json = await request.json()
        body = VendorPostInput(**json)

        data = body.data.dict_without_none()

        for cat in data.get("categories", ""):
            category = await db.read_category(cat["id"], projection={"status": 1})
            if category["status"] != "active":
                raise HTTPBadRequest(text=f"Category {cat['id']} is not active")
        await validate_vendor_identifier(
            action="create",
            identifier_id=data["vendor"]["identifier"]["id"],
        )

        access = set_access_token(request, data)
        data['id'] = uuid4().hex
        data['isActive'] = False
        data['dateCreated'] = data['dateModified'] = get_now().isoformat()
        await db.insert_vendor(data)
        response = {"data": VendorSerializer(data).data,
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
                vendor['dateModified'] = get_now().isoformat()

                # validate activation is allowed
                if vendor.get("isActive") and not initial_data.get("isActive"):
                    await validate_vendor_identifier(action="activate",
                                                     identifier_id=vendor["vendor"]["identifier"]["id"])
        return {"data": VendorSerializer(vendor).data}
