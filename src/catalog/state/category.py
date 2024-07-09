from aiohttp.web import HTTPBadRequest
from pymongo import UpdateOne

from catalog.state.base import BaseState
from catalog.context import get_now
from catalog.db import get_profiles_collection
from catalog.validations import validate_medicine_additional_classifications, validate_agreement


class CategoryState(BaseState):

    @classmethod
    async def on_put(cls, data):
        if "agreementID" in data:
            await validate_agreement(data)
        await validate_medicine_additional_classifications(data)
        data['dateModified'] = get_now().isoformat()
        super().on_post(data)

    @classmethod
    async def on_patch(cls, before, after):
        if before != after:
            if (
                before.get("unit")
                and after.get("unit")
                and before["unit"] != after["unit"]
            ):
                raise HTTPBadRequest(text="Forbidden to update an existing unit")

            after['dateModified'] = get_now().isoformat()

            if before.get("agreementID", "") != after.get("agreementID", ""):
                await validate_agreement(after)
                await cls.update_profiles_agreement_id(before, after)

            if before.get("additionalClassifications", "") != after.get("additionalClassifications", ""):
                await validate_medicine_additional_classifications(after)

        super().on_patch(before, after)

    @classmethod
    async def update_profiles_agreement_id(cls, before, after):
        agreement_id = after["agreementID"]
        bulk = []
        profiles_collection = get_profiles_collection()
        async for profile in profiles_collection.find({"relatedCategory": after["id"]}):
            bulk.append(
                UpdateOne(
                    filter={"_id": profile["_id"], "agreementID": before.get("agreementID")},
                    update={"$set": {
                        "agreementID": agreement_id, "dateModified": get_now().isoformat()}
                    }
                )
            )

        if bulk:
            result = await profiles_collection.bulk_write(bulk)
