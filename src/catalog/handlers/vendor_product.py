from uuid import uuid4

from aiohttp.web_urldispatcher import View

from catalog import db
from catalog.models.product import VendorProductCreateInput
from catalog.swagger import class_view_swagger_path
from catalog.utils import get_now
from catalog.auth import validate_access_token, validate_accreditation
from catalog.serializers.product import ProductSerializer
from catalog.validations import (
    validate_product_related_profile,
    validate_product_active_vendor,
    validate_product_to_profile,
)


@class_view_swagger_path('/app/swagger/vendors/products')
class VendorProductView(View):

    @classmethod
    async def post(cls, request, vendor_id: str) -> dict:
        validate_accreditation(request, "vendor_products")
        vendor = await db.read_vendor(vendor_id)
        json = await request.json()
        body = VendorProductCreateInput(**json)
        validate_access_token(request, vendor, body.access)
        data = body.data.dict_without_none()
        profile = await db.read_profile(data["relatedProfiles"][0])
        # validations
        validate_product_active_vendor(vendor)
        validate_product_related_profile(profile)
        validate_product_to_profile(profile, data)

        data['id'] = uuid4().hex
        data['vendor'] = {"id": vendor_id}
        data['dateCreated'] = data['dateModified'] = get_now().isoformat()
        data['access'] = {'owner': request.user.name}
        await db.insert_product(data)

        return {'data': ProductSerializer(data, vendor=vendor).data}
