from aiohttp.web_urldispatcher import View as BaseView

from catalog import db
from catalog.auth import validate_accreditation, validate_access_token
from catalog.utils import get_now, find_item_by_id, delete_sent_none_values
from catalog.models.criteria import (
    CriterionCreateInput,
    CriterionUpdateInput,
    RGCreateInput,
    RGUpdateInput,
    Requirement,
)
from catalog.serializers.base import RootSerializer
from catalog.validations import validate_requirement_title_uniq, validate_criteria_max_items_on_post


class View(BaseView):

    obj_name: str
    serializer_class = RootSerializer

    @classmethod
    async def get_body_from_model(cls, request):
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
    def delete_obj_criterion(cls, obj_id: str, criterion_id: str, dateModified):
        return db.delete_obj_criterion(cls.obj_name, obj_id, criterion_id, dateModified)

    @classmethod
    def validations(cls, request):
        validate_accreditation(request, cls.obj_name)


class BaseCriteriaView(View):
    """
    Base view for criterion
    """

    @classmethod
    async def get_body_from_model(cls, request):
        json = await request.json()
        if request.method == "POST":
            return CriterionCreateInput(**json)
        elif request.method == "PATCH":
            return CriterionUpdateInput(**json)

    @classmethod
    async def collection_get(cls, request, obj_id):
        obj_criteria = await cls.get_parent_obj(obj_id=obj_id)
        data = cls.serializer_class(obj_criteria, show_owner=False).data
        return {"data": data["criteria"]}

    @classmethod
    async def get(cls, request, obj_id, criterion_id):
        criterion = await cls.get_criterion(obj_id, criterion_id)
        data = cls.serializer_class(criterion, show_owner=False).data
        return {"data": data["criteria"]}

    @classmethod
    async def post(cls, request, obj_id):
        cls.validations(request)
        async with cls.read_and_update_parent_obj(obj_id) as parent_obj:
            # import and validate data
            body = await cls.get_body_from_model(request)

            validate_access_token(request, parent_obj, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            if "criteria" not in parent_obj:
                parent_obj["criteria"] = []

            parent_obj["criteria"].append(data)
            validate_criteria_max_items_on_post(parent_obj, "criteria")
            parent_obj["dateModified"] = get_now().isoformat()
        return {"data": cls.serializer_class(data).data}

    @classmethod
    async def patch(cls, request, obj_id, criterion_id):
        cls.validations(request)
        async with cls.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            # import and validate data
            json = await request.json()
            body = await cls.get_body_from_model(request)

            validate_access_token(request, parent_obj, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update obj with valid data
            # mongo unwinded criteria, so here is only one item in `criteria`
            parent_obj["criteria"].update(data)
            parent_obj["dateModified"] = get_now().isoformat()

        return {"data": cls.serializer_class(parent_obj["criteria"]).data}


class BaseCriteriaRGView(View):
    """
    Base view for criterion requirement group
    """

    @classmethod
    async def get_body_from_model(cls, request):
        json = await request.json()
        if request.method == "POST":
            return RGCreateInput(**json)
        elif request.method == "PATCH":
            return RGUpdateInput(**json)

    @classmethod
    async def collection_get(cls, request, obj_id, criterion_id):
        parent_criteria = await cls.get_criterion(obj_id, criterion_id)
        data = RootSerializer(parent_criteria, show_owner=False).data
        return {"data": [
            cls.serializer_class(rg, show_owner=False).data
            for rg in data["criteria"]["requirementGroups"]
        ]}

    @classmethod
    async def get(cls, request, obj_id, criterion_id, rg_id):
        parent_criterion = await cls.get_criterion(obj_id, criterion_id)
        rg = find_item_by_id(parent_criterion, rg_id, "requirementGroups")
        return {"data": cls.serializer_class(rg, show_owner=False).data}

    @classmethod
    async def post(cls, request, obj_id, criterion_id):
        cls.validations(request)
        async with cls.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            # import and validate data
            body = await cls.get_body_from_model(request)

            validate_access_token(request, parent_obj, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update obj with valid data
            parent_obj["criteria"]["requirementGroups"].append(data)
            validate_criteria_max_items_on_post(parent_obj["criteria"], "requirementGroups")
            parent_obj["dateModified"] = get_now().isoformat()
        return {"data": cls.serializer_class(data).data}

    @classmethod
    async def patch(cls, request, obj_id, criterion_id, rg_id):
        cls.validations(request)
        async with cls.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            # import and validate data
            body = await cls.get_body_from_model(request)

            validate_access_token(request, parent_obj, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update object with valid data
            rg = find_item_by_id(parent_obj["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            rg.update(data)
            parent_obj["dateModified"] = get_now().isoformat()

        return {"data": cls.serializer_class(rg).data}


class BaseCriteriaRGRequirementView(View):
    """
    Base view for criterion requirement
    """

    @classmethod
    async def get_body_from_model(cls, request):
        pass

    @classmethod
    def get_main_model_class(cls):
        return Requirement

    @classmethod
    async def requirement_validations(cls, parent_obj, data):
        pass

    @classmethod
    async def collection_get(cls, request, obj_id, criterion_id, rg_id):
        criteria = await cls.get_criterion(obj_id, criterion_id)
        rg = find_item_by_id(criteria["criteria"]["requirementGroups"], rg_id, "requirementGroups")
        return {"data": [cls.serializer_class(i, show_owner=False).data for i in rg.get("requirements", [])]}

    @classmethod
    async def get(cls, request, obj_id, criterion_id, rg_id, requirement_id):
        criterion = await cls.get_criterion(obj_id, criterion_id)
        rg = find_item_by_id(criterion["criteria"]["requirementGroups"], rg_id, "requirementGroups")
        requirement = find_item_by_id(rg["requirements"], requirement_id, "requirements")
        return {"data": cls.serializer_class(requirement, show_owner=False).data}

    @classmethod
    async def post(cls, request, obj_id, criterion_id, rg_id):
        cls.validations(request)
        async with cls.read_and_update_parent_obj(obj_id) as obj:
            # import and validate data
            criterion = find_item_by_id(obj["criteria"], criterion_id, "criteria")
            rg = find_item_by_id(criterion["requirementGroups"], rg_id, "requirementGroups")
            body = await cls.get_body_from_model(request)
            validate_access_token(request, obj, body.access)
            # export data back to dict
            data = [r.dict_without_none() for r in body.data]
            # update obj with valid data
            await cls.requirement_validations(obj, data)
            rg["requirements"].extend(data)
            validate_requirement_title_uniq(obj)
            obj["dateModified"] = get_now().isoformat()
        return {"data": [cls.serializer_class(r).data for r in data]}

    @classmethod
    async def patch(cls, request, obj_id, criterion_id, rg_id, requirement_id):
        cls.validations(request)
        async with cls.read_and_update_parent_obj(obj_id) as obj:
            # import and validate data
            criterion = find_item_by_id(obj["criteria"], criterion_id, "criteria")
            rg = find_item_by_id(criterion["requirementGroups"], rg_id, "requirementGroups")
            requirement = find_item_by_id(rg["requirements"], requirement_id, "requirements")
            body = await cls.get_body_from_model(request)
            json = await request.json()

            validate_access_token(request, obj, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            requirement.update(data)
            delete_sent_none_values(requirement, json["data"])

            requirement_model = cls.get_main_model_class()
            requirement_model(**requirement)

            await cls.requirement_validations(obj, [requirement])
            validate_requirement_title_uniq(obj)
            obj["dateModified"] = get_now().isoformat()

        return {"data": cls.serializer_class(requirement).data}
