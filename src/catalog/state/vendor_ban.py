from catalog.context import get_now
from catalog.state.ban import BanState


class VendorBanState(BanState):

    @classmethod
    async def on_post(cls, data):
        now = get_now()
        data["dueDate"] = (now.replace(year=now.year + 1)).isoformat()
        await super().on_post(data)
