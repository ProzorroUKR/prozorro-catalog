from typing import Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401

from catalog.auth import validate_accreditation

from catalog import db
from catalog.handlers.base_ban import BaseBanViewMixin, BaseBanViewItemMixin
from catalog.models.api import ErrorResponse
from catalog.models.ban import ContributorBanPostInput, BanResponse, BanList
from catalog.validations import validate_contributor_ban_already_exists


class ContributorBanMixin:

    parent_obj_name = "contributor"

    async def get_parent_obj(self, parent_obj_id):
        return await db.read_contributor(parent_obj_id)

    def read_and_update_object(self, parent_obj_id):
        return db.read_and_update_contributor(parent_obj_id)

    async def validate_data(self, body, parent_obj):
        data = body.data.dict_without_none()
        administrator_id = data.get("administrator", {}).get("identifier", {}).get("id")
        validate_contributor_ban_already_exists(parent_obj, administrator_id)


class ContributorBanView(ContributorBanMixin, BaseBanViewMixin, PydanticView):

    async def get(self, contributor_id: str, /) -> r200[BanList]:
        """
        Get a list of contributor bans

        Tags: Contributor/Bans
        """
        return await BaseBanViewMixin.get(self, contributor_id)

    async def post(
        self, contributor_id: str, /, body: ContributorBanPostInput
    ) -> Union[r201[BanResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Create a contributor ban

        Security: Basic: []
        Tags: Contributor/Bans
        """
        validate_accreditation(self.request, "category")
        return await BaseBanViewMixin.post(self, contributor_id, body)


class ContributorBanItemView(ContributorBanMixin, BaseBanViewItemMixin, PydanticView):
    async def get(
        self, contributor_id: str, ban_id: str, /,
    ) -> Union[r200[BanResponse], r400[ErrorResponse], r404[ErrorResponse]]:
        """
        Get a contributor ban

        Tags: Contributor/Bans
        """
        return await BaseBanViewItemMixin.get(self, contributor_id, ban_id)
