from aiohttp.web import HTTPBadRequest
from uuid import uuid4

from catalog import db
from catalog.state.base import BaseState
from catalog.context import get_now, get_request


class ContributorState(BaseState):

    @classmethod
    async def on_post(cls, data):
        await cls.validate_contributor_identifier(identifier_id=data["contributor"]["identifier"]["id"])
        data['id'] = uuid4().hex
        data['dateCreated'] = data['dateModified'] = get_now().isoformat()
        data['owner'] = get_request().user.name
        for doc in data.get("documents", []):
            doc["datePublished"] = doc["dateModified"] = get_now().isoformat()

        super().on_post(data)

    @staticmethod
    async def validate_contributor_identifier(identifier_id):
        existing = await db.find_contributors(
            offset=None,
            limit=1,
            reverse=False,
            filters={"contributor.identifier.id": identifier_id},
        )
        if existing["data"]:
            dup_id = existing["data"][0]["id"]
            raise HTTPBadRequest(
                text=f"Cannot create contributor.identifier.id {identifier_id} already exists: {dup_id}"
            )
