import logging

from aiohttp.web_urldispatcher import View

from catalog import db
from catalog.models.product import VendorProductCreateInput
from catalog.swagger import class_view_swagger_path
from catalog.auth import validate_access_token, validate_accreditation
from catalog.serializers.product import ProductSerializer
from catalog.state.vendor_product import VendorProductState


logger = logging.getLogger(__name__)


@class_view_swagger_path('/app/swagger/vendors/products')
class VendorProductView(View):

    state_class = VendorProductState

    @classmethod
    async def post(cls, request, vendor_id: str) -> dict:
        validate_accreditation(request, "vendor_products")
        vendor = await db.read_vendor(vendor_id)
        json = await request.json()
        body = VendorProductCreateInput(**json)
        validate_access_token(request, vendor, body.access)
        data = body.data.dict_without_none()

        category = await db.read_category(data["relatedCategory"])
        await cls.state_class.on_post(data, vendor, category)

        data['vendor'] = {"id": vendor_id}
        data['access'] = {'owner': request.user.name}
        await db.insert_product(data)

        logger.info(
            f"Created vendor product {data['id']}",
            extra={
                "MESSAGE_ID": f"vendor_product_create",
                "vendor_product_id": data["id"]
            },
        )
        return {'data': ProductSerializer(data, vendor=vendor, category=category).data}
