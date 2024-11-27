from catalog.state.base import BaseState
from catalog.context import get_now, get_request


class BanState(BaseState):

    @classmethod
    async def on_post(cls, data, parent_obj):
        data['dateCreated'] = get_now().isoformat()
        data["owner"] = get_request().user.name
        for doc in data.get("documents", []):
            doc["datePublished"] = doc["dateModified"] = get_now().isoformat()

        super().on_post(data)
