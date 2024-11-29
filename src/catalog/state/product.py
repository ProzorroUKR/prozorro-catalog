from aiohttp.web import HTTPBadRequest
from aiohttp.web_exceptions import HTTPForbidden

from catalog import db
from catalog.state.base import BaseState
from catalog.context import get_now
from catalog.validations import (
    validate_product_to_category,
    validate_product_to_profile,
    validate_medicine_additional_classifications
)
from catalog.models.product import ProductStatus


class ProductState(BaseState):

    category_fields_to_copy = ["marketAdministrator"]
    check_classification = True
    required_criteria = []

    @classmethod
    async def on_post(cls, data, category):
        validate_product_to_category(
            category,
            data,
            check_classification=cls.check_classification,
            required_criteria=cls.required_criteria,
        )
        await cls.validate_product_to_profiles(data)
        await validate_medicine_additional_classifications(data)
        cls.copy_data_from_category(data, category)
        data["dateCreated"] = data["dateModified"] = get_now().isoformat()

    @classmethod
    async def on_patch(cls, before, after):
        if before.get("status", ProductStatus.active) != ProductStatus.active:
            raise HTTPForbidden(text=f"Patch product in {before['status']} status is disallowed")
        now = get_now().isoformat()
        if before != after:
            category_id = after["relatedCategory"]
            category = await db.read_category(category_id)

            if after.get("status", ProductStatus.active) != ProductStatus.hidden:
                validate_product_to_category(
                    category,
                    after,
                    before,
                    check_classification=(after.get("vendor") is None),
                    required_criteria=cls.required_criteria,
                )
                await cls.validate_product_to_profiles(after)
            if before.get("additionalClassifications", "") != after.get("additionalClassifications", ""):
                await validate_medicine_additional_classifications(after)
            cls.copy_data_from_category(after, category)
            if after.get("status") != ProductStatus.active:
                after["expirationDate"] = now
            for doc in after.get("documents", []):
                doc["datePublished"] = doc["dateModified"] = now
        after["dateModified"] = now

        super().on_patch(before, after)

    @classmethod
    async def validate_product_to_profiles(cls, product):
        profile_ids = product.get("relatedProfiles", "")
        for profile_id in profile_ids:
            profile = await db.read_profile(profile_id)
            validate_product_to_profile(profile, product)

    @classmethod
    def copy_data_from_category(cls, product, category):
        for i in cls.category_fields_to_copy:
            if category.get(i):
                product[i] = category[i]
            else:
                raise HTTPBadRequest(text=f"Related category doesn't have {i}")
