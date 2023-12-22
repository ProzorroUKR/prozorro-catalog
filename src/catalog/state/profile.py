from aiohttp.web import HTTPBadRequest

from catalog.state.base import BaseState
from catalog.context import get_now


class LocalizationProfileState(BaseState):
    @classmethod
    async def on_put(cls, data, category):
        data['dateCreated'] = data['dateModified'] = get_now().isoformat()
        super().on_post(data)

    @classmethod
    async def on_patch(cls, before, after):
        if before != after:
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
