from catalog.auth import validate_access_token

from catalog import db
from catalog.models.product_request import ProductRequestPostInput
from catalog.serializers.product_request import ProductRequestSerializer
from catalog.state.product_request import ProductRequestState
from catalog.swagger import class_view_swagger_path
from catalog.handlers.base import BaseView
from catalog.validations import validate_product_to_category, validate_contributor_banned_categories


@class_view_swagger_path('/app/swagger/crowd_sourcing/contributors/product_request')
class ProductRequestView(BaseView):
    state = ProductRequestState

    @classmethod
    async def post(cls, request, **kwargs):
        contributor = await db.read_contributor(kwargs.get("contributor_id"))
        # import and validate data
        json = await request.json()
        body = ProductRequestPostInput(**json)
        validate_access_token(request, contributor, body.access)
        data = body.data.dict_without_none()

        # category validations
        category = await db.read_category(data["product"]["relatedCategory"])
        validate_product_to_category(category, data["product"])
        validate_contributor_banned_categories(category, contributor)

        data["contributor_id"] = contributor["id"]
        await cls.state.on_post(data)
        await db.insert_product_request(data)

        return {"data": ProductRequestSerializer(data).data}
