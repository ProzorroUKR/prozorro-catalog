import logging

from aiohttp.web import HTTPNotFound

from catalog.context import get_now
from catalog.models.ban import RequestBanPostInput

from catalog.serializers.ban import BanSerializer
from catalog.state.ban import BanState


logger = logging.getLogger(__name__)


class BaseBanMixin:
    state = BanState

    parent_obj_name = None

    async def get_parent_obj(self, parent_obj_id):
        pass

    def read_and_update_object(self, parent_obj_id):
        pass

    async def validate_data(self, body, parent_obj):
        pass

    async def get_body_from_model(self):
        raise NotImplementedError("provide `get_model_cls` method")


class BaseBanViewMixin(BaseBanMixin):
    async def get(self, parent_obj_id: str, /):
        obj = await self.get_parent_obj(parent_obj_id)
        return {"data": [BanSerializer(ban).data for ban in obj.get("bans", "")]}

    async def post(self, parent_obj_id: str, /, body: RequestBanPostInput):
        data = body.data.dict_without_none()
        async with self.read_and_update_object(parent_obj_id) as obj:
            await self.validate_data(body, obj)
            await self.state.on_post(data, obj)
            obj["dateModified"] = get_now().isoformat()
            if "bans" not in obj:
                obj["bans"] = []
            obj["bans"].append(data)

            logger.info(
                f"Created {self.parent_obj_name} ban {data['id']}",
                extra={
                    "MESSAGE_ID": f"{self.parent_obj_name}_ban_create",
                    "document_id": data["id"]
                },
            )

        return {"data": BanSerializer(data).data}


class BaseBanViewItemMixin(BaseBanMixin):
    async def get(self, parent_obj_id: str, ban_id: str, /):
        obj = await self.get_parent_obj(parent_obj_id)
        for ban in obj.get("bans", ""):
            if ban["id"] == ban_id:
                return {"data": BanSerializer(ban).data}
        else:
            raise HTTPNotFound(text="Ban not found")
