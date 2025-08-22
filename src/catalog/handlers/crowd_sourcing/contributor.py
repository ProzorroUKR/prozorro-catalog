import logging
from typing import Union, Optional

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401

from catalog import db
from catalog.auth import validate_accreditation
from catalog.models.api import ErrorResponse, PaginatedList
from catalog.models.contributor import ContributorPostInput, ContributorResponse
from catalog.serializers.contributor import ContributorSerializer
from catalog.state.contributor import ContributorState
from catalog.utils import pagination_params, get_revision_changes


logger = logging.getLogger(__name__)


class ContributorView(PydanticView):
    state = ContributorState

    async def get(
        self, /, offset: Optional[str] = None, limit: Optional[int] = 100, descending: Optional[Union[int, str]] = 0,
    ) -> r200[PaginatedList]:
        """
        Get a list of contributors

        Tags: Contributors
        """
        offset, limit, reverse = pagination_params(self.request)
        response = await db.find_contributors(
            offset=offset,
            limit=limit,
            reverse=reverse,
        )
        return response

    async def post(
        self, /, body: ContributorPostInput
    ) -> Union[r201[ContributorResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Create contributor

        Security: Basic: []
        Tags: Contributors
        """
        validate_accreditation(self.request, "contributors")

        data = body.data.dict_without_none()
        await self.state.on_post(data)
        get_revision_changes(self.request, new_obj=data)
        await db.insert_contributor(data)

        logger.info(
            f"Created contributor {data['id']}",
            extra={
                "MESSAGE_ID": f"contributor_create",
                "contributor_id": data["id"],
            },
        )
        return {"data": ContributorSerializer(data).data}


class ContributorItemView(PydanticView):
    state = ContributorState

    async def get(
        self, contributor_id: str, /,
    ) -> Union[r200[ContributorResponse], r400[ErrorResponse], r404[ErrorResponse]]:
        """
        Get contributor

        Tags: Contributors
        """
        obj = await db.read_contributor(contributor_id)
        return {"data": ContributorSerializer(obj).data}
