from catalog.context import get_now
from catalog.models.vendor import VendorStatus
from catalog.state.ban import BanState


class VendorBanState(BanState):

    @classmethod
    async def on_post(cls, data, parent_obj):
        now = get_now()
        data["dueDate"] = (now.replace(year=now.year + 1)).isoformat()
        parent_obj["status"] = VendorStatus.banned
        await super().on_post(data, parent_obj)
