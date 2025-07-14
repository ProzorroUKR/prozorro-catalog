from typing import Optional, Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r400, r404
from catalog import db
from catalog.models.api import PaginatedList, ErrorResponse
from catalog.models.offer import OfferResponse
from catalog.utils import pagination_params
from catalog.serializers.base import RootSerializer


class OfferView(PydanticView):

    async def get(
        self, /, offset: Optional[str] = None, limit: Optional[int] = 100, descending: Optional[Union[int, str]] = 0,
    ) -> r200[PaginatedList]:
        """
        Get a list of offers

        Tags: Offers
        """
        offset, limit, reverse = pagination_params(self.request)
        response = await db.find_offers(
            offset=offset,
            limit=limit,
            reverse=reverse,
        )
        return response


class OfferItemView(PydanticView):

    async def get(self, offer_id: str, /) -> Union[r200[OfferResponse], r400[ErrorResponse], r404[ErrorResponse]]:
        """
        Get an offer

        Tags: Offers
        """
        data = await db.read_offer(offer_id)
        return {"data": RootSerializer(data).data}
