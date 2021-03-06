import random
from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPBadRequest, HTTPNotFound, HTTPConflict
from pymongo.errors import OperationFailure
from catalog import db
from catalog.models.offer import OfferCreateData, OfferUpdateInput, Offer
from catalog.models.api import AnyInput
from catalog.swagger import class_view_swagger_path
from catalog.utils import pagination_params, get_now, async_retry
from catalog.auth import validate_access_token, validate_accreditation, set_access_token
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

    @classmethod
    async def put(cls, request, offer_id):
        validate_accreditation(request, "offer")
        # import and validate data
        json_data = await request.json()
        body = AnyInput(**json_data)
        # export data back to dict
        body.data["id"] = offer_id
        data = OfferCreateData(**body.data).dict_without_none()

        # validations between objects
        product = await db.read_product(data['relatedProduct'])  # ensure exists
        # --

        try:
            Offer.validate_offer(data)
        except ValueError as e:
            raise HTTPBadRequest(text=e.args[0])

        access = set_access_token(request, data)
        data['dateModified'] = get_now().isoformat()
        await db.insert_offer(data)

        response = {"data": RootSerializer(data).data,
                    "access": access}
        return response

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def patch(cls, request, offer_id):
        validate_accreditation(request, "offer")
        async with db.read_and_update_offer(offer_id) as obj:
            # import and validate data
            json = await request.json()
            body = OfferUpdateInput(**json)

            validate_access_token(request, obj, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            data['dateModified'] = get_now().isoformat()
            obj.update(data)

        return {"data": RootSerializer(obj).data}
