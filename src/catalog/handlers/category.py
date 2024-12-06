import random
from copy import deepcopy
import logging

from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPBadRequest, HTTPConflict
from pymongo.errors import OperationFailure
from catalog import db
from catalog.swagger import class_view_swagger_path
from catalog.auth import set_access_token, validate_accreditation, validate_access_token
from catalog.utils import pagination_params, async_retry
from catalog.models.category import CategoryCreateInput, CategoryUpdateInput, DeprecatedCategoryCreateInput
from catalog.models.criteria import (
    CategoryRequirementCreateInput,
    CategoryBulkRequirementCreateInput,
    CategoryRequirementUpdateInput,
    CategoryRequirement,
)
from catalog.serializers.base import RootSerializer
from catalog.state.category import CategoryState
from catalog.handlers.base_criteria import (
    BaseCriteriaView,
    BaseCriteriaRGView,
    BaseCriteriaRGRequirementView,
)


logger = logging.getLogger(__name__)


@class_view_swagger_path('/app/swagger/categories')
class CategoryView(View):
    state = CategoryState

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
        obj = await db.read_category(category_id)
        return {"data": RootSerializer(obj, show_owner=False).data}

    @classmethod
    async def put(cls, request, category_id):
        validate_accreditation(request, "category")

        # import and validate data
        json = await request.json()
        body = DeprecatedCategoryCreateInput(**json)
        if category_id != body.data.id:
            raise HTTPBadRequest(text='id mismatch')

        data = body.data.dict_without_none()
        await cls.state.on_put(data)
        access = set_access_token(request, data)
        await db.insert_category(data)

        logger.info(
            f"Created category {data['id']}",
            extra={"MESSAGE_ID": "category_create_put"},
        )
        response = {"data": RootSerializer(data, show_owner=False).data,
                    "access": access}
        return response

    @classmethod
    async def post(cls, request):
        validate_accreditation(request, "category")

        # import and validate data
        json = await request.json()
        body = CategoryCreateInput(**json)

        # export data back to dict
        data = body.data.dict_without_none()
        await cls.state.on_put(data)
        access = set_access_token(request, data)
        await db.insert_category(data)

        logger.info(
            f"Created category {data['id']}",
            extra={
                "MESSAGE_ID": "category_create_post",
                "category_id": data["id"],
            },
        )

        response = {
            "data": RootSerializer(data, show_owner=False).data,
            "access": access,
        }
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
            old_category = deepcopy(category)
            category.update(data)
            await cls.state.on_patch(old_category, category)

            logger.info(
                f"Updated category {category_id}",
                extra={"MESSAGE_ID": "category_patch"},
            )

        return {"data": RootSerializer(category, show_owner=False).data}


class CategoryCriteriaViewMixin:

    obj_name = "category"

    @classmethod
    def read_and_update_parent_obj(cls, obj_id):
        return db.read_and_update_category(obj_id)


@class_view_swagger_path('/app/swagger/categories/criterion')
class CategoryCriteriaView(CategoryCriteriaViewMixin, BaseCriteriaView):
    pass


@class_view_swagger_path('/app/swagger/categories/criterion/requirementGroups')
class CategoryCriteriaRGView(CategoryCriteriaViewMixin, BaseCriteriaRGView):
    pass


@class_view_swagger_path('/app/swagger/categories/criterion/requirementGroups/requirements')
class CategoryCriteriaRGRequirementView(CategoryCriteriaViewMixin, BaseCriteriaRGRequirementView):
    @classmethod
    async def get_body_from_model(cls, request):
        json = await request.json()
        body = None
        if request.method == "POST":
            if isinstance(json.get("data", {}), dict):
                body = CategoryRequirementCreateInput(**json)
                body.data = [body.data]
            elif isinstance(json["data"], list):
                body = CategoryBulkRequirementCreateInput(**json)
        elif request.method == "PATCH":
            return CategoryRequirementUpdateInput(**json)
        return body

    @classmethod
    def get_main_model_class(cls):
        return CategoryRequirement
