from aiohttp.web_urldispatcher import View
from catalog import db
from catalog.swagger import class_view_swagger_path
from catalog.utils import pagination_params
from catalog.serializers.base import RootSerializer


@class_view_swagger_path('/app/swagger/offers')
class OfferView(View):

    @classmethod
    async def collection_get(cls, request):
        offset, limit, reverse = pagination_params(request)
        response = await db.find_offers(
            offset=offset,
            limit=limit,
            reverse=reverse,
        )
        return response

    @classmethod
    async def get(cls, request, offer_id):
        data = await db.read_offer(offer_id)
        return {"data": RootSerializer(data).data}
