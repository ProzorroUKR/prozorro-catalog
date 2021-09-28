from aiohttp.web import HTTPForbidden
from pydantic import BaseModel
from catalog.settings import AUTH_DATA


class User(BaseModel):
    name: str = "anonymous"

    def check_item_write_allowed(self, item_name):
        if self.name not in AUTH_DATA.get("item_name", ""):
            raise HTTPForbidden(text=f'Not permitted: {item_name}')

