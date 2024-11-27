from aiohttp.web import HTTPNotFound

from catalog.context import get_now

from catalog.serializers.ban import BanSerializer
from catalog.state.ban import BanState
from catalog.handlers.base import BaseView


class BaseBanView(BaseView):
    state = BanState

    @classmethod
    async def get_parent_obj(cls, **kwargs):
        pass

    @classmethod
    def read_and_update_object(cls, **kwargs):
        pass

    @classmethod
    async def validate_data(cls, request, body, parent_obj, **kwargs):
        pass

    @classmethod
    async def get_body_from_model(cls, request):
        raise NotImplementedError("provide `get_model_cls` method")

    @classmethod
    async def collection_get(cls, request, **kwargs):
        obj = await cls.get_parent_obj(**kwargs)
        return {"data": [BanSerializer(ban).data for ban in obj.get("bans", "")]}

    @classmethod
    async def get(cls, request, **kwargs):
        obj = await cls.get_parent_obj(**kwargs)
        ban_id = kwargs.get("ban_id")
        for ban in obj.get("bans", ""):
            if ban["id"] == ban_id:
                return {"data": BanSerializer(ban).data}
        else:
            raise HTTPNotFound(text="Ban not found")

    @classmethod
    async def post(cls, request, **kwargs):
        # import and validate data
        body = await cls.get_body_from_model(request)
        data = body.data.dict_without_none()
        async with cls.read_and_update_object(**kwargs) as obj:
            await cls.validate_data(request, body, obj, **kwargs)
            await cls.state.on_post(data, obj)
            obj["dateModified"] = get_now().isoformat()
            if "bans" not in obj:
                obj["bans"] = []
            obj["bans"].append(data)

        return {"data": BanSerializer(data).data}
