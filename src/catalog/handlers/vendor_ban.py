from typing import Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401
from catalog.auth import validate_access_token

from catalog import db
from catalog.handlers.base_ban import BaseBanViewMixin, BaseBanViewItemMixin
from catalog.models.api import ErrorResponse
from catalog.models.ban import VendorBanPostInput, BanResponse, BanList
from catalog.state.vendor_ban import VendorBanState
from catalog.validations import validate_active_vendor


class VendorBanView(BaseBanViewMixin, PydanticView):
    state = VendorBanState

    parent_obj_name = "vendor"

    async def get_parent_obj(self, parent_obj_id):
        return await db.read_vendor(parent_obj_id)

    def read_and_update_object(cls, parent_obj_id):
        return db.read_and_update_vendor(parent_obj_id)

    async def validate_data(self, body, parent_obj):
        validate_access_token(self.request, parent_obj, parent_obj["access"])
        validate_active_vendor(parent_obj)

    async def get(self, vendor_id: str, /) -> r200[BanList]:
        """
        Get a list of vendor bans

        Tags: Vendor/Bans
        """
        return await BaseBanViewMixin.get(self, vendor_id)

    async def post(
        self, vendor_id: str, /, body: VendorBanPostInput
    ) -> Union[r201[BanResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Create a vendor ban

        Security: Basic: []
        Tags: Vendor/Bans
        """
        return await BaseBanViewMixin.post(self, vendor_id, body)


class VendorBanItemView(BaseBanViewItemMixin, PydanticView):
    state = VendorBanState

    parent_obj_name = "vendor"

    async def get_parent_obj(self, parent_obj_id):
        return await db.read_vendor(parent_obj_id)

    async def get(
        self, vendor_id: str, ban_id: str, /,
    ) -> Union[r200[BanResponse], r400[ErrorResponse], r404[ErrorResponse]]:
        """
        Get a vendor ban

        Tags: Vendor/Bans
        """
        return await BaseBanViewItemMixin.get(self, vendor_id, ban_id)
