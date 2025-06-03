import logging
from typing import Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401

from catalog import db
from catalog.models.api import ErrorResponse
from catalog.models.product import VendorProductCreateInput, ProductResponse
from catalog.auth import validate_access_token, validate_accreditation
from catalog.serializers.product import ProductSerializer
from catalog.state.vendor_product import VendorProductState


logger = logging.getLogger(__name__)


class VendorProductView(PydanticView):

    state_class = VendorProductState

    async def post(
        self, vendor_id: str, /, body: VendorProductCreateInput
    ) -> Union[r201[ProductResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Create vendor product

        Security: Basic: []
        Tags: Vendor/Products
        """
        validate_accreditation(self.request, "vendor_products")
        vendor = await db.read_vendor(vendor_id)
        validate_access_token(self.request, vendor, body.access)
        data = body.data.dict_without_none()

        category = await db.read_category(data["relatedCategory"])
        await self.state_class.on_post(data, vendor, category)

        data['vendor'] = {"id": vendor_id}
        data['access'] = {'owner': self.request.user.name}
        await db.insert_product(data)

        logger.info(
            f"Created vendor product {data['id']}",
            extra={
                "MESSAGE_ID": f"vendor_product_create",
                "vendor_product_id": data["id"]
            },
        )
        return {'data': ProductSerializer(data, vendor=vendor, category=category).data}
