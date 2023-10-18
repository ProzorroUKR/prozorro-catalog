from catalog.state.base import BaseState
from catalog.context import get_now, get_request
from uuid import uuid4


class BanState(BaseState):

    @classmethod
    async def on_post(cls, data):
        data['id'] = uuid4().hex
        data['dateCreated'] = get_now().isoformat()
        data["owner"] = get_request().user.name
        for doc in data.get("documents", []):
            doc["datePublished"] = get_now().isoformat()

        super().on_post(data)