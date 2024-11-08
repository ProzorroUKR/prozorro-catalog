from catalog import db
from catalog.state.product import ProductState
from catalog.validations import (
    validate_product_related_category,
    validate_product_active_vendor,
)


class VendorProductState(ProductState):

    check_classification = False

    @classmethod
    async def on_post(cls, data, vendor, category):
        validate_product_active_vendor(vendor)
        validate_product_related_category(category)
        await super().on_post(data, category)
