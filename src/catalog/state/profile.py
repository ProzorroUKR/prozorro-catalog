from aiohttp.web import HTTPBadRequest

from catalog.state.base import BaseState
from catalog.context import get_now
from catalog.validations import validate_medicine_additional_classifications, validate_agreement


class LocalizationProfileState(BaseState):
    @classmethod
    async def on_put(cls, data, category):
        await validate_medicine_additional_classifications(data)
        data['dateCreated'] = data['dateModified'] = get_now().isoformat()
        super().on_post(data)

    @classmethod
    async def on_patch(cls, before, after):
        if before != after:
            if before.get("additionalClassifications", "") != after.get("additionalClassifications", ""):
                await validate_medicine_additional_classifications(after)
            if before.get("agreementID", "") != after.get("agreementID", ""):
                await validate_agreement(after)
            after['dateModified'] = get_now().isoformat()

        super().on_patch(before, after)


class ProfileState(LocalizationProfileState):

    @classmethod
    async def on_put(cls, data, category):
        fields_from_category = ["unit", "classification", "agreementID"]

        for i in fields_from_category:
            if category.get(i):
                data[i] = category[i]
            else:
                raise HTTPBadRequest(text=f"Related category doesn't have {i}")
        await super().on_put(data, category)
