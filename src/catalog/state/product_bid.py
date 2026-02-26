from catalog.context import get_now
from catalog.state.base import BaseState


class ProductBidState(BaseState):
    @classmethod
    def on_post(cls, data):
        now = get_now().isoformat()
        data.setdefault("dateCreated", now)
        data.setdefault("dateModified", now)

    @classmethod
    def on_post(cls, data):
        data["dateCreated"] = data["dateModified"] = get_now().isoformat()

    @classmethod
    def on_patch(cls, before, after):
        now = get_now().isoformat()
        if before != after:
            after["dateModified"] = now

        super().on_patch(before, after)
