import random
from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPBadRequest, HTTPNotFound, HTTPConflict
from pymongo.errors import OperationFailure
from catalog import db
from catalog.swagger import class_view_swagger_path
from catalog.auth import set_access_token, validate_accreditation, validate_access_token
from catalog.utils import pagination_params, get_now, async_retry
from catalog.models.category import CategoryCreateInput, CategoryUpdateInput


@class_view_swagger_path('/app/swagger/categories')
class CategoryView(View):

    @classmethod
    async def collection_get(cls, request):
        offset, limit, reverse = pagination_params(request)
        response = await db.find_categories(
            offset=offset,
            limit=limit,
            reverse=reverse,
        )
        return response

    @classmethod
    async def get(cls, request, category_id):
        profile = await db.read_category(category_id)
        if not profile:
            raise HTTPNotFound(text="Not found")
        return {"data": profile}

    @classmethod
    async def put(cls, request, category_id):
        validate_accreditation(request, "category")

        # import and validate data
        json = await request.json()
        body = CategoryCreateInput(**json)
        if category_id != body.data.id:
            raise HTTPBadRequest(text='id mismatch')

        data = body.data.dict_without_none()
        access = set_access_token(request, data)
        data['dateModified'] = get_now().isoformat()
        await db.insert_category(data)

        data.pop("access")
        response = {"data": data, "access": access}
        return response

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def patch(cls, request, category_id):
        validate_accreditation(request, "category")
        async with db.read_and_update_category(category_id) as category:
            # import and validate data
            json = await request.json()
            body = CategoryUpdateInput(**json)

            validate_access_token(request, category, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            category.update(data)
            data['dateModified'] = get_now().isoformat()

        category.pop("access")
        return {"data": category}
