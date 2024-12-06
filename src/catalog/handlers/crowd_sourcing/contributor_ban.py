from catalog.auth import validate_accreditation

from catalog import db
from catalog.handlers.base_ban import BaseBanView
from catalog.models.ban import ContributorBanPostInput
from catalog.swagger import class_view_swagger_path
from catalog.validations import validate_contributor_ban_already_exists


@class_view_swagger_path('/app/swagger/crowd_sourcing/contributors/bans')
class ContributorBanView(BaseBanView):

    parent_obj_name = "contributor"

    @classmethod
    async def get_parent_obj(cls, **kwargs):
        return await db.read_contributor(kwargs.get("contributor_id"))

    @classmethod
    def read_and_update_object(cls, **kwargs):
        return db.read_and_update_contributor(kwargs.get("contributor_id"))

    @classmethod
    async def validate_data(cls, request, body, parent_obj, **kwargs):
        data = body.data.dict_without_none()
        administrator_id = data.get("administrator", {}).get("identifier", {}).get("id")
        validate_contributor_ban_already_exists(parent_obj, administrator_id)

    @classmethod
    async def get_body_from_model(cls, request):
        json = await request.json()
        return ContributorBanPostInput(**json)

    @classmethod
    async def collection_get(cls, request, **kwargs):
        return await super().collection_get(request, **kwargs)

    @classmethod
    async def get(cls, request, **kwargs):
        return await super().get(request, **kwargs)

    @classmethod
    async def post(cls, request, **kwargs):
        validate_accreditation(request, "category")
        return await super().post(request, **kwargs)
