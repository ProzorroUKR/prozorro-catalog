import logging
from typing import Optional, Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r400, r404

from catalog import db
from catalog.models.api import ErrorResponse, PaginatedList
from catalog.models.price import PriceResponse
from catalog.serializers.price import PriceSerializer
from catalog.utils import pagination_params

logger = logging.getLogger(__name__)


class PriceView(PydanticView):
    async def get(
        self,
        /,
        offset: Optional[str] = None,
        limit: Optional[int] = 100,
        descending: Optional[Union[int, str]] = 0,
    ) -> r200[PaginatedList]:
        """
        Get a list of price records

        Tags: Prices
        """
        offset, limit, reverse = pagination_params(self.request)
        response = await db.find_prices(
            offset=offset,
            limit=limit,
            reverse=reverse,
        )
        return response


class PriceItemView(PydanticView):
    async def get(self, price_id: str, /) -> Union[r200[PriceResponse], r400[ErrorResponse], r404[ErrorResponse]]:
        """
        Get price record

        Tags: Prices
        """
        price = await db.read_price(price_id)
        return {"data": PriceSerializer(price).data}


class ProductPriceView(PydanticView):
    async def get(
        self,
        product_id: str,
        /,
        offset: Optional[str] = None,
        limit: Optional[int] = 100,
        descending: Optional[Union[int, str]] = 1,
    ) -> r200[PaginatedList]:
        """
        Get a list of prices for a specific product

        Tags: Prices
        """
        await db.read_product(product_id)
        offset, limit, reverse = pagination_params(self.request, default_reverse=True)
        response = await db.find_prices_by_product(
            product_id,
            offset=offset,
            limit=limit,
            reverse=reverse,
        )
        return response
