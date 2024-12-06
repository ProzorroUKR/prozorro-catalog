import logging

from catalog import db
from catalog.auth import validate_accreditation
from catalog.models.contributor import ContributorPostInput
from catalog.serializers.contributor import ContributorSerializer
from catalog.state.contributor import ContributorState
from catalog.swagger import class_view_swagger_path
from catalog.handlers.base import BaseView
from catalog.utils import pagination_params


logger = logging.getLogger(__name__)


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
        validate_accreditation(request, "contributors")
        # import and validate data
        json = await request.json()
        body = ContributorPostInput(**json)
        data = body.data.dict_without_none()
        await cls.state.on_post(data)
        await db.insert_contributor(data)

        logger.info(
            f"Created contributor {data['id']}",
            extra={
                "MESSAGE_ID": f"contributor_create",
                "contributor_id": data["id"],
            },
        )
        return {"data": ContributorSerializer(data).data}
