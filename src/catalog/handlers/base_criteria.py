import logging

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401
from typing import Union

from catalog import db
from catalog.auth import validate_accreditation, validate_access_token
from catalog.settings import LOCALIZATION_CRITERIA
from catalog.utils import get_now, find_item_by_id, delete_sent_none_values
from catalog.models.api import ErrorResponse
from catalog.models.criteria import (
    CriterionBulkCreateInput,
    CriterionCreateInput,
    CriterionUpdateInput,
    RGCreateInput,
    RGUpdateInput,
    Requirement, CriterionListResponse, CriterionResponse, RGResponse, RGListResponse, RequirementListResponse,
    RequirementResponse, RequirementCreateInput, RequirementUpdateInput,
)
from catalog.serializers.base import RootSerializer
from catalog.validations import (
    validate_criteria_classification_uniq,
    validate_criteria_max_items_on_post,
    validate_requirement_title_uniq,
)

logger = logging.getLogger(__name__)


class BaseCriteriaMixin:

    obj_name: str
    serializer_class = RootSerializer

    async def get_body_from_model(self):
        raise NotImplementedError("provide `get_model_cls` method")

    @classmethod
    async def get_parent_obj(cls, obj_id: str) -> dict:
        return await db.read_obj_criteria(cls.obj_name, obj_id)

    @classmethod
    async def get_criterion(cls, obj_id: str, criterion_id: str) -> dict:
        return await db.read_obj_criterion(cls.obj_name, obj_id, criterion_id)

    @classmethod
    def read_and_update_parent_obj(cls, obj_id: str):
        raise NotImplementedError

    @classmethod
    def read_and_update_criterion(cls, obj_id: str, criterion_id: str):
        return db.read_and_update_obj_criterion(cls.obj_name, obj_id, criterion_id)

    @classmethod
    def delete_obj_criterion(cls, obj_id: str, criterion_id: str, dateModified: str):
        return db.delete_obj_criterion(cls.obj_name, obj_id, criterion_id, dateModified)

    def validations(self):
        validate_accreditation(self.request, self.obj_name)


class BaseCriteriaViewMixin(BaseCriteriaMixin):
    """
    Base view mixin for criterion
    """

    async def get_body_from_model(self):
        json = await self.request.json()
        if isinstance(json.get("data", {}), dict):
            body = CriterionCreateInput(**json)
            body.data = [body.data]
        elif isinstance(json["data"], list):
            body = CriterionBulkCreateInput(**json)
        return body

    async def get(self, obj_id: str, /) -> r200[CriterionListResponse]:
        obj_criteria = await self.get_parent_obj(obj_id=obj_id)
        data = self.serializer_class(obj_criteria, show_owner=False).data
        return {"data": data["criteria"]}


    async def post(self, obj_id: str, /, body: CriterionCreateInput) -> Union[r201[CriterionListResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        self.validations()
        async with self.read_and_update_parent_obj(obj_id) as parent_obj:
            # import and validate data
            body = await self.get_body_from_model()

            validate_access_token(self.request, parent_obj, body.access)
            # export data back to dict
            data = [criterion.dict_without_none() for criterion in body.data]
            # update profile with valid data
            if "criteria" not in parent_obj:
                parent_obj["criteria"] = []

            parent_obj["criteria"].extend(data)
            validate_criteria_classification_uniq(parent_obj)
            parent_obj["dateModified"] = get_now().isoformat()
            for criterion in data:
                logger.info(
                    f"Created {self.obj_name} criterion {criterion['id']}",
                    extra={
                        "MESSAGE_ID": f"{self.obj_name}_criterion_create",
                        f"{self.obj_name}_criterion_id": criterion['id']
                    },
                )
        return {"data": [self.serializer_class(criterion).data for criterion in data]}


class BaseCriteriaItemViewMixin(BaseCriteriaMixin):

    async def get(self, obj_id: str, criterion_id: str, /) -> Union[r200[CriterionResponse], r404[ErrorResponse]]:
        criterion = await self.get_criterion(obj_id, criterion_id)
        data = self.serializer_class(criterion, show_owner=False).data
        return {"data": data["criteria"]}

    async def patch(
        self, obj_id: str, criterion_id: str, /, body: CriterionUpdateInput
    ) -> Union[r200[CriterionResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        self.validations()
        async with self.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            validate_access_token(self.request, parent_obj, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update obj with valid data
            # mongo unwinded criteria, so here is only one item in `criteria`
            parent_obj["criteria"].update(data)
            criteria_parent = await self.get_parent_obj(obj_id)
            validate_criteria_classification_uniq(criteria_parent, updated_criterion=parent_obj["criteria"])
            parent_obj["dateModified"] = get_now().isoformat()

            logger.info(
                f"Updated {self.obj_name} criterion {criterion_id}",
                extra={"MESSAGE_ID": f"{self.obj_name}_criterion_patch"},
            )

        return {"data": self.serializer_class(parent_obj["criteria"]).data}


class BaseCriteriaRGViewMixin(BaseCriteriaMixin):
    """
    Base view mixin for criterion requirement group
    """

    async def get(self, obj_id: str, criterion_id: str, /) -> r200[RGListResponse]:
        parent_criteria = await self.get_criterion(obj_id, criterion_id)
        data = RootSerializer(parent_criteria, show_owner=False).data
        return {"data": [
            self.serializer_class(rg, show_owner=False).data
            for rg in data["criteria"]["requirementGroups"]
        ]}

    async def post(
        self, obj_id: str, criterion_id: str, /, body: RGCreateInput
    ) -> Union[r201[RGResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        self.validations()
        async with self.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            validate_access_token(self.request, parent_obj, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update obj with valid data
            parent_obj["criteria"]["requirementGroups"].append(data)
            if parent_obj["criteria"].get("classification", {}).get("id") != LOCALIZATION_CRITERIA:
                validate_criteria_max_items_on_post(parent_obj["criteria"], "requirementGroups")
            parent_obj["dateModified"] = get_now().isoformat()

            logger.info(
                f"Created {self.obj_name} criteria requirement group {data['id']}",
                extra={
                    "MESSAGE_ID": f"{self.obj_name}_requirement_group_create",
                    "requirement_group_id": data["id"]
                },
            )
        return {"data": self.serializer_class(data).data}


class BaseCriteriaRGItemViewMixin(BaseCriteriaMixin):

    async def get(self, obj_id: str, criterion_id: str, rg_id: str, /) -> Union[r200[RGResponse], r404[ErrorResponse]]:
        parent_criterion = await self.get_criterion(obj_id, criterion_id)
        rg = find_item_by_id(parent_criterion["criteria"]["requirementGroups"], rg_id, "requirementGroups")
        return {"data": self.serializer_class(rg, show_owner=False).data}

    async def patch(
        self, obj_id: str, criterion_id: str, rg_id: str, /, body: RGUpdateInput
    ) -> Union[r200[RGResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        self.validations()
        async with self.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            validate_access_token(self.request, parent_obj, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update object with valid data
            rg = find_item_by_id(parent_obj["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            rg.update(data)
            parent_obj["dateModified"] = get_now().isoformat()

            logger.info(
                f"Updated {self.obj_name} criteria requirement group {rg_id}",
                extra={"MESSAGE_ID": f"{self.obj_name}_requirement_group_patch"},
            )

        return {"data": self.serializer_class(rg).data}


class BaseCriteriaRGRequirementViewMixin(BaseCriteriaMixin):
    """
    Base view mixin for criterion requirement
    """

    async def get_body_from_model(self):
        pass

    @classmethod
    def get_main_model_class(cls):
        return Requirement

    @classmethod
    async def requirement_validations(cls, parent_obj, data):
        pass

    async def get(self, obj_id: str, criterion_id: str, rg_id: str, /) -> r200[RequirementListResponse]:
        criteria = await self.get_criterion(obj_id, criterion_id)
        rg = find_item_by_id(criteria["criteria"]["requirementGroups"], rg_id, "requirementGroups")
        return {"data": [self.serializer_class(i, show_owner=False).data for i in rg.get("requirements", [])]}


    async def post(
        self, obj_id: str, criterion_id: str, rg_id: str, /, body: RequirementCreateInput
    ) -> Union[r201[RequirementResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        self.validations()
        async with self.read_and_update_parent_obj(obj_id) as obj:
            # import and validate data
            criterion = find_item_by_id(obj["criteria"], criterion_id, "criteria")
            rg = find_item_by_id(criterion["requirementGroups"], rg_id, "requirementGroups")
            body = await self.get_body_from_model()
            validate_access_token(self.request, obj, body.access)
            # export data back to dict
            data = [r.dict_without_none() for r in body.data]
            # update obj with valid data
            await self.requirement_validations(obj, data)
            rg["requirements"].extend(data)
            validate_requirement_title_uniq(obj)
            obj["dateModified"] = get_now().isoformat()

            for i in data:

                logger.info(
                    f"Created {self.obj_name} criteria requirement {i['id']}",
                    extra={
                        "MESSAGE_ID": f"{self.obj_name}_requirement_create",
                        "requirement_group_id": i["id"],
                    },
                )
        return {"data": [self.serializer_class(r).data for r in data]}


class BaseCriteriaRGRequirementItemViewMixin(BaseCriteriaMixin):
    @classmethod
    async def requirement_validations(cls, parent_obj, data):
        pass

    async def get(
        self, obj_id: str, criterion_id: str, rg_id: str, requirement_id: str, /
    ) -> Union[r200[RequirementResponse], r404[ErrorResponse]]:
        criterion = await self.get_criterion(obj_id, criterion_id)
        rg = find_item_by_id(criterion["criteria"]["requirementGroups"], rg_id, "requirementGroups")
        requirement = find_item_by_id(rg["requirements"], requirement_id, "requirements")
        return {"data": self.serializer_class(requirement, show_owner=False).data}

    async def patch(
        self, obj_id: str, criterion_id: str, rg_id: str, requirement_id: str, /, body: RequirementUpdateInput
    ) -> Union[r200[RequirementResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        self.validations()
        async with self.read_and_update_parent_obj(obj_id) as obj:
            # import and validate data
            criterion = find_item_by_id(obj["criteria"], criterion_id, "criteria")
            rg = find_item_by_id(criterion["requirementGroups"], rg_id, "requirementGroups")
            requirement = find_item_by_id(rg["requirements"], requirement_id, "requirements")
            body = await self.get_body_from_model()
            json = await self.request.json()

            validate_access_token(self.request, obj, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            requirement.update(data)
            delete_sent_none_values(requirement, json["data"])

            requirement_model = self.get_main_model_class()
            requirement_model(**requirement)

            await self.requirement_validations(obj, [requirement])
            validate_requirement_title_uniq(obj)
            obj["dateModified"] = get_now().isoformat()

            logger.info(
                f"Updated {self.obj_name} criteria requirement {requirement_id}",
                extra={"MESSAGE_ID": f"{self.obj_name}_requirement_create"},
            )

        return {"data": self.serializer_class(requirement).data}
