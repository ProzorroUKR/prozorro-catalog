from typing import Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r201, r400
from catalog import db
from catalog.models.api import ErrorResponse
from catalog.models.search import SearchInput, SearchResponse
from catalog.serializers.base import RootSerializer


COLLECTIONS = {
    "category": db.get_category_collection,
    "profile": db.get_profiles_collection,
    "product": db.get_products_collection,
    "offer": db.get_offers_collection,
}


class SearchView(PydanticView):

    async def post(self, /, body: SearchInput) -> Union[r201[SearchResponse], r400[ErrorResponse]]:
        """
        Find resources by their ids

        Tags: Search
        """
        get_collection = COLLECTIONS[body.data.resource]
        items = await db.find_objects(get_collection(), body.data.ids)

        response = {"data": [RootSerializer(item).data for item in items]}
        return response
