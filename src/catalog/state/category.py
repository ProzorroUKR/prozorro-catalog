import aiohttp
from aiohttp.web import HTTPBadRequest
from pymongo import UpdateOne

from catalog.state.base import BaseState
from catalog.context import get_now
from catalog.db import get_profiles_collection
from catalog.models.profile import ProfileStatus
from catalog.settings import OPENPROCUREMENT_API_URL


class CategoryState(BaseState):

    @classmethod
    async def on_put(cls, data):
        if "agreementID" in data:
            await cls.validate_agreement(data)
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
                await cls.validate_agreement(after)
                await cls.update_profiles_agreement_id(after)

        super().on_patch(before, after)

    @classmethod
    async def validate_agreement(cls, category):
        async with aiohttp.ClientSession() as session:
            async with session.get(f'{OPENPROCUREMENT_API_URL}/agreements/{category["agreementID"]}') as resp:
                if resp.status == 404:
                    raise HTTPBadRequest(text="Agreement doesn't exist")
                if resp.status != 200:
                    raise HTTPBadRequest(text="Can't get agreement from openprocurement api, "
                                              "plz make request later")
                data = await resp.json()
                agreement = data["data"]
                if agreement.get("status", "") != "active":
                    raise HTTPBadRequest(text="Agreement not in `active` status")
                agr_clas_id = agreement["classification"]["id"]
                cat_clas_id = category["classification"]["id"]
                if agr_clas_id[0:3] != cat_clas_id[0:3]:
                    raise HTTPBadRequest(text="Agreement:classification:id first three numbers "
                                              "should be equal to Category:classification:id")

    @classmethod
    async def update_profiles_agreement_id(cls, category):
        agreement_id = category["agreementID"]
        bulk = []
        profiles_collection = get_profiles_collection()
        async for profile in profiles_collection.find({"relatedCategory": category["id"]}):
            bulk.append(
                UpdateOne(
                    filter={"_id": profile["_id"]},
                    update={"$set": {
                        "agreementID": agreement_id, "dateModified": get_now().isoformat()}
                    }
                )
            )

        if bulk:
            result = await profiles_collection.bulk_write(bulk)
