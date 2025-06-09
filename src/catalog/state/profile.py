from aiohttp.web import HTTPBadRequest

from catalog.db import validate_tags_exist
from catalog.state.base import BaseState
from catalog.context import get_now
from catalog.validations import validate_medicine_additional_classifications, validate_agreement


class LocalizationProfileState(BaseState):
    @classmethod
    async def on_put(cls, data, category):
        await validate_medicine_additional_classifications(data)
        await validate_tags_exist(data.get("tags", []))
        data['dateCreated'] = data['dateModified'] = get_now().isoformat()
        super().on_post(data)

    @classmethod
    async def on_patch(cls, before, after):
        if before != after:
            if before.get("additionalClassifications", "") != after.get("additionalClassifications", ""):
                await validate_medicine_additional_classifications(after)
            if before.get("agreementID", "") != after.get("agreementID", ""):
                await validate_agreement(after)
            await validate_tags_exist(after.get("tags", []))
            after['dateModified'] = get_now().isoformat()

        super().on_patch(before, after)


class ProfileState(LocalizationProfileState):

    @classmethod
    async def on_put(cls, data, category):
        fields_from_category = ["unit", "classification", "marketAdministrator"]

        if not (agreement_id := data.get("agreementID")):
            fields_from_category.append("agreementID")

        for i in fields_from_category:
            if category.get(i):
                data[i] = category[i]
            else:
                raise HTTPBadRequest(text=f"Related category doesn't have {i}")

        if agreement_id:
            await validate_agreement(data)

        await super().on_put(data, category)
