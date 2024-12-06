from catalog.auth import validate_access_token

from catalog import db
from catalog.handlers.base_ban import BaseBanView
from catalog.models.ban import VendorBanPostInput
from catalog.state.vendor_ban import VendorBanState
from catalog.swagger import class_view_swagger_path
from catalog.validations import validate_active_vendor


@class_view_swagger_path('/app/swagger/vendors/bans')
class VendorBanView(BaseBanView):
    state = VendorBanState

    parent_obj_name = "vendor"

    @classmethod
    async def get_parent_obj(cls, **kwargs):
        return await db.read_vendor(kwargs.get("vendor_id"))

    @classmethod
    def read_and_update_object(cls, **kwargs):
        return db.read_and_update_vendor(kwargs.get("vendor_id"))

    @classmethod
    async def validate_data(cls, request, body, parent_obj, **kwargs):
        validate_access_token(request, parent_obj, parent_obj["access"])
        validate_active_vendor(parent_obj)

    @classmethod
    async def get_body_from_model(cls, request):
        json = await request.json()
        return VendorBanPostInput(**json)

    @classmethod
    async def collection_get(cls, request, **kwargs):
        return await super().collection_get(request, **kwargs)

    @classmethod
    async def get(cls, request, **kwargs):
        return await super().get(request, **kwargs)

    @classmethod
    async def post(cls, request, **kwargs):
        return await super().post(request, **kwargs)
