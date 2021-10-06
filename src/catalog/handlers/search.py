from aiohttp.web_urldispatcher import View
from catalog import db
from catalog.models.search import SearchInput
from catalog.swagger import class_view_swagger_path
from catalog.serializers.base import RootSerializer


COLLECTIONS = {
    "category": db.get_category_collection,
    "profile": db.get_profiles_collection,
    "product": db.get_products_collection,
    "offer": db.get_offers_collection,
}


@class_view_swagger_path('/app/swagger/search')
class SearchView(View):

    @classmethod
    async def post(cls, request):
        json = await request.json()
        body = SearchInput(**json)

        get_collection = COLLECTIONS[body.data.resource]
        items = await db.find_objects(get_collection(), body.data.ids)

        response = {"data": [RootSerializer(item).data for item in items]}
        return response
