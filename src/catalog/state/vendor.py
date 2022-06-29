from catalog.state.base import BaseState
from aiohttp.web import HTTPBadRequest
from catalog.context import get_now
from catalog import db
from uuid import uuid4


class VendorState(BaseState):

    @classmethod
    async def on_post(cls, data):
        for cat in data.get("categories", ""):
            category = await db.read_category(cat["id"], projection={"status": 1})
            if category["status"] != "active":
                raise HTTPBadRequest(text=f"Category {cat['id']} is not active")
        await cls.validate_vendor_identifier(
            action="create",
            identifier_id=data["vendor"]["identifier"]["id"],
        )
        data['id'] = uuid4().hex
        data['isActivated'] = False
        data['dateCreated'] = data['dateModified'] = get_now().isoformat()

        super().on_post(data)

    @classmethod
    async def on_patch(cls, before, after):
        if before != after:
            after['dateModified'] = get_now().isoformat()

            # validate activation is allowed
            if after.get("isActivated") and not before.get("isActivated"):
                await cls.validate_vendor_identifier(action="activate",
                                                     identifier_id=after["vendor"]["identifier"]["id"])
        super().on_patch(before, after)

    @staticmethod
    async def validate_vendor_identifier(action, identifier_id):
        existing = await db.find_vendors(
            offset=None,
            limit=1,
            reverse=False,
            filters={
                "isActivated": True,
                "vendor.identifier.id": identifier_id,
            }
        )
        if existing["data"]:
            dup_id = existing["data"][0]["id"]
            raise HTTPBadRequest(
                text=f"Cannot {action} vendor.identifier.id {identifier_id} already exists: {dup_id}"
            )

    @classmethod
    def always(cls, data):
        data["status"] = "active" if data.get("isActivated") else "pending"
