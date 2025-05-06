from copy import deepcopy
import logging
from typing import Union, Optional
from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401
from aiohttp.web import HTTPBadRequest
from catalog import db
from catalog.models.api import PaginatedList, ErrorResponse
from catalog.auth import set_access_token, validate_accreditation, validate_access_token
from catalog.utils import pagination_params, get_revision_changes
from catalog.models.category import CategoryCreateInput, CategoryUpdateInput, DeprecatedCategoryCreateInput, \
    CategoryResponse
from catalog.models.criteria import (
    CategoryRequirementCreateInput,
    CategoryBulkRequirementCreateInput,
    CategoryRequirementUpdateInput,
    CategoryRequirement,
    CriterionCreateInput,
    CriterionListResponse,
    CriterionResponse,
    CriterionUpdateInput,
    RGResponse,
    RGCreateInput,
    RGListResponse,
    RGUpdateInput,
    RequirementListResponse,
    RequirementResponse,
    RequestCategoryRequirementCreateInput,
)
from catalog.serializers.base import RootSerializer
from catalog.state.category import CategoryState
from catalog.handlers.base_criteria import (
    BaseCriteriaViewMixin,
    BaseCriteriaItemViewMixin,
    BaseCriteriaRGViewMixin,
    BaseCriteriaRGItemViewMixin,
    BaseCriteriaRGRequirementViewMixin,
    BaseCriteriaRGRequirementItemViewMixin,
)


logger = logging.getLogger(__name__)


class CategoryView(PydanticView):
    state = CategoryState

    async def get(
        self, /, offset: Optional[str] = None,  limit: Optional[int] = 100, descending: Optional[int] = 0,
    ) -> r200[PaginatedList]:
        """
        Get a list of categories

        Tags: Categories
        """
        offset, limit, reverse = pagination_params(self.request)
        response = await db.find_categories(
            offset=offset,
            limit=limit,
            reverse=reverse,
        )
        return response

    async def post(
        self, /, body: CategoryCreateInput
    ) -> Union[r201[CategoryResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Create category

        Security: Basic: []
        Tags: Categories
        """
        validate_accreditation(self.request, "category")

        # export data back to dict
        data = body.data.dict_without_none()
        await self.state.on_put(data)
        access = set_access_token(self.request, data)
        get_revision_changes(self.request, new_obj=data)
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


class CategoryItemView(PydanticView):
    state = CategoryState

    async def get(self, category_id: str, /) -> Union[r200[CategoryResponse], r400[ErrorResponse], r404[ErrorResponse]]:
        """
        Get category

        Tags: Categories
        """
        obj = await db.read_category(category_id)
        return {"data": RootSerializer(obj, show_owner=False).data}

    async def put(
        self, category_id: str, /, body: DeprecatedCategoryCreateInput
    ) -> Union[r201[CategoryResponse], r400[ErrorResponse]]:
        """
        Create category

        Security: Basic: []
        Tags: Categories
        """

        validate_accreditation(self.request, "category")
        if category_id != body.data.id:
            raise HTTPBadRequest(text='id mismatch')

        data = body.data.dict_without_none()
        await self.state.on_put(data)
        access = set_access_token(self.request, data)
        get_revision_changes(self.request, new_obj=data)
        await db.insert_category(data)

        logger.info(
            f"Created category {data['id']}",
            extra={"MESSAGE_ID": "category_create_put"},
        )
        response = {"data": RootSerializer(data, show_owner=False).data,
                    "access": access}
        return response

    async def patch(
        self, category_id: str, /, body: CategoryUpdateInput
    ) -> Union[r200[CategoryResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Category update

        Security: Basic: []
        Tags: Categories
        """
        validate_accreditation(self.request, "category")
        async with db.read_and_update_category(category_id) as category:
            validate_access_token(self.request, category, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            old_category = deepcopy(category)
            category.update(data)
            await self.state.on_patch(old_category, category)
            get_revision_changes(self.request, new_obj=category, old_obj=old_category)

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


class CategoryCriteriaView(CategoryCriteriaViewMixin, BaseCriteriaViewMixin, PydanticView):
    async def get(self, obj_id: str, /) -> r200[CriterionListResponse]:
        """
        Get a list of object criteria

        Tags: Category/Criteria
        """
        return await BaseCriteriaViewMixin.get(self, obj_id)

    async def post(
        self, obj_id: str, /, body: CriterionCreateInput
    ) -> Union[r201[CriterionListResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Object criteria create

        Security: Basic: []
        Tags: Category/Criteria
        """
        return await BaseCriteriaViewMixin.post(self, obj_id, body)


class CategoryCriteriaItemView(CategoryCriteriaViewMixin, BaseCriteriaItemViewMixin, PydanticView):
    async def get(self, obj_id: str, criterion_id: str, /) -> Union[r200[CriterionResponse], r404[ErrorResponse]]:
        """
        Get an object criterion

        Tags: Category/Criteria
        """
        return await BaseCriteriaItemViewMixin.get(self, obj_id, criterion_id)

    async def patch(
        self, obj_id: str, criterion_id: str, /, body: CriterionUpdateInput
    ) -> Union[r200[CriterionResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Object criterion update

        Security: Basic: []
        Tags: Category/Criteria
        """
        return await BaseCriteriaItemViewMixin.patch(self, obj_id, criterion_id, body)


class CategoryCriteriaRGView(CategoryCriteriaViewMixin, BaseCriteriaRGViewMixin, PydanticView):
    async def get(self, obj_id: str, criterion_id: str, /) -> r200[RGListResponse]:
        """
        Get a list of requirementGroups

        Tags: Category/Criteria/RequirementGroups
        """
        return await BaseCriteriaRGViewMixin.get(self, obj_id, criterion_id)

    async def post(
        self, obj_id: str, criterion_id: str, /, body: RGCreateInput
    ) -> Union[r201[RGResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        RequirementGroup create

        Security: Basic: []
        Tags: Category/Criteria/RequirementGroups
        """
        return await BaseCriteriaRGViewMixin.post(self, obj_id, criterion_id, body)


class CategoryCriteriaRGItemView(CategoryCriteriaViewMixin, BaseCriteriaRGItemViewMixin, PydanticView):
    async def get(self, obj_id: str, criterion_id: str, rg_id: str, /) -> Union[r200[RGResponse], r404[ErrorResponse]]:
        """
        Get a requirementGroup

        Tags: Category/Criteria/RequirementGroups
        """
        return await BaseCriteriaRGItemViewMixin.get(self, obj_id, criterion_id, rg_id)

    async def patch(
            self, obj_id: str, criterion_id: str, rg_id: str, /, body: RGUpdateInput
    ) -> Union[r200[RGResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        RequirementGroup update

        Security: Basic: []
        Tags: Category/Criteria/RequirementGroups
        """
        return await BaseCriteriaRGItemViewMixin.patch(self, obj_id, criterion_id, rg_id, body)


class CategoryCriteriaRGRequirementView(CategoryCriteriaViewMixin, BaseCriteriaRGRequirementViewMixin, PydanticView):
    async def get_body_from_model(self):
        json = await self.request.json()
        body = None
        if self.request.method == "POST":
            if isinstance(json.get("data", {}), dict):
                body = CategoryRequirementCreateInput(**json)
                body.data = [body.data]
            elif isinstance(json["data"], list):
                body = CategoryBulkRequirementCreateInput(**json)
        return body

    @classmethod
    def get_main_model_class(cls):
        return CategoryRequirement

    async def get(self, obj_id: str, criterion_id: str, rg_id: str, /) -> r200[RequirementListResponse]:
        """
        Get a list of requirements

        Tags: Category/Criteria/RequirementGroups/Requirements
        """
        return await BaseCriteriaRGRequirementViewMixin.get(self, obj_id, criterion_id, rg_id)


    async def post(
        self, obj_id: str, criterion_id: str, rg_id: str, /, body: RequestCategoryRequirementCreateInput
    ) -> Union[r201[RequirementResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Requirement create

        Security: Basic: []
        Tags: Category/Criteria/RequirementGroups/Requirements
        """
        return await BaseCriteriaRGRequirementViewMixin.post(self, obj_id, criterion_id, rg_id, body)


class CategoryCriteriaRGRequirementItemView(CategoryCriteriaViewMixin, BaseCriteriaRGRequirementItemViewMixin, PydanticView):
    async def get_body_from_model(self):
        json = await self.request.json()
        return CategoryRequirementUpdateInput(**json)

    @classmethod
    def get_main_model_class(cls):
        return CategoryRequirement

    async def get(
        self, obj_id: str, criterion_id: str, rg_id: str, requirement_id: str, /
    ) -> Union[r200[RequirementResponse], r404[ErrorResponse]]:
        """
        Get a requirement

        Tags: Category/Criteria/RequirementGroups/Requirements
        """
        return await BaseCriteriaRGRequirementItemViewMixin.get(self, obj_id, criterion_id, rg_id, requirement_id)

    async def patch(
        self, obj_id: str, criterion_id: str, rg_id: str, requirement_id: str, /, body: CategoryRequirementUpdateInput
    ) -> Union[r200[RequirementResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Requirement update

        Security: Basic: []
        Tags: Category/Criteria/RequirementGroups/Requirements
        """
        return await BaseCriteriaRGRequirementItemViewMixin.patch(self, obj_id, criterion_id, rg_id, requirement_id, body)
