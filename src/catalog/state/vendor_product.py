from datetime import datetime

from catalog.context import get_now
from catalog.settings import CRITERIA_LIST
from catalog.state.product import ProductState
from catalog.validations import (
    validate_product_related_category,
    validate_active_vendor,
)


class VendorProductState(ProductState):

    check_classification = False
    required_criteria = CRITERIA_LIST
    @classmethod
    async def on_post(cls, data, vendor, category):
        validate_active_vendor(vendor)
        validate_product_related_category(category)
        await super().on_post(data, category)
        now = get_now()
        data['expirationDate'] = datetime(
            year=now.year + 1, month=3, day=31, hour=23, minute=59, second=59, tzinfo=now.tzinfo,
        ).isoformat()
