from aiohttp.web import HTTPNotFound
from catalog.context import get_now

from catalog import db
from catalog.models.ban import BanPostInput
from catalog.serializers.base import BaseSerializer
from catalog.state.ban import BanState
from catalog.swagger import class_view_swagger_path
from catalog.handlers.base import BaseView
from catalog.validations import validate_contributor_ban_already_exists


@class_view_swagger_path('/app/swagger/crowd_sourcing/contributors/bans')
class ContributorBanView(BaseView):
    state = BanState

    @classmethod
    async def collection_get(cls, request, **kwargs):
        contributor = await db.read_contributor(kwargs.get("contributor_id"))
        return {"data": [BaseSerializer(ban).data for ban in contributor.get("bans", "")]}

    @classmethod
    async def get(cls, request, **kwargs):
        contributor = await db.read_contributor(kwargs.get("contributor_id"))
        ban_id = kwargs.get("ban_id")
        for ban in contributor.get("bans", ""):
            if ban["id"] == ban_id:
                return {"data": BaseSerializer(ban).data}
        else:
            raise HTTPNotFound(text="Ban not found")

    @classmethod
    async def post(cls, request, **kwargs):
        # import and validate data
        json = await request.json()
        body = BanPostInput(**json)
        data = body.data.dict_without_none()
        async with db.read_and_update_contributor(kwargs.get("contributor_id")) as obj:
            administrator_id = data.get("administrator", {}).get("identifier", {}).get("id")
            validate_contributor_ban_already_exists(obj, administrator_id)
            await cls.state.on_post(data)
            obj["dateModified"] = get_now().isoformat()
            if "bans" not in obj:
                obj["bans"] = []
            obj["bans"].append(data)

        return {"data": BaseSerializer(data).data}
