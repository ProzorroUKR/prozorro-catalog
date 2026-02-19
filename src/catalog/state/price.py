from catalog.context import get_now
from catalog.state.base import BaseState


class PriceState(BaseState):
    @classmethod
    def on_post(cls, data):
        cls.validate_quartiles(data)
        now = get_now().isoformat()
        data.setdefault("dateCreated", now)
        data.setdefault("dateModified", now)

    @classmethod
    def on_patch(cls, before, after):
        now = get_now().isoformat()
        if before != after:
            cls.validate_quartiles(after)
            after["dateModified"] = now

        super().on_patch(before, after)

    @classmethod
    def validate_quartiles(cls, data):
        lower = data.get("lowerQuartile")
        median = data.get("medianQuartile")
        upper = data.get("upperQuartile")

        if lower is not None and median is not None and median < lower:
            raise ValueError("medianQuartile must be greater than or equal to lowerQuartile")
        if median is not None and upper is not None and upper < median:
            raise ValueError("upperQuartile must be greater than or equal to medianQuartile")
