from catalog import db
from catalog.models.contributor import ContributorPostInput
from catalog.serializers.contributor import ContributorSerializer
from catalog.state.contributor import ContributorState
from catalog.swagger import class_view_swagger_path
from catalog.handlers.base import BaseView
from catalog.auth import set_access_token
from catalog.utils import pagination_params


@class_view_swagger_path('/app/swagger/crowd_sourcing/contributors')
class ContributorView(BaseView):
    state = ContributorState

    @classmethod
    async def collection_get(cls, request):
        offset, limit, reverse = pagination_params(request)
        response = await db.find_contributors(
            offset=offset,
            limit=limit,
            reverse=reverse,
        )
        return response

    @classmethod
    async def get(cls, request, contributor_id):
        obj = await db.read_contributor(contributor_id)
        return {"data": ContributorSerializer(obj).data}

    @classmethod
    async def post(cls, request):
        # import and validate data
        json = await request.json()
        body = ContributorPostInput(**json)
        data = body.data.dict_without_none()
        await cls.state.on_post(data)
        access = set_access_token(request, data)
        await db.insert_contributor(data)
        response = {
            "data": ContributorSerializer(data).data,
            "access": access,
        }
        return response
