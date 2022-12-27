from aiohttp.web_urldispatcher import View as BaseView

from catalog import db
from catalog.auth import validate_accreditation, validate_access_token
from catalog.utils import get_now, find_item_by_id
from catalog.models.criteria import (
    CriterionCreateInput,
    CriterionUpdateInput,
    RGCreateInput,
    RGUpdateInput,
    RequirementCreateInput,
    BulkRequirementCreateInput,
    RequirementUpdateInput,
    Requirement,
)
from catalog.serializers.base import RootSerializer, BaseSerializer


class View(BaseView):

    obj_name: str

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
    async def collection_get(cls, request, obj_id):
        obj_criteria = await cls.get_parent_obj(obj_id=obj_id)
        data = RootSerializer(obj_criteria, show_owner=False).data
        return {"data": data["criteria"]}

    @classmethod
    async def get(cls, request, obj_id, criterion_id):
        criterion = await cls.get_criterion(obj_id, criterion_id)
        data = RootSerializer(criterion, show_owner=False).data
        return {"data": data["criteria"]}

    @classmethod
    async def post(cls, request, obj_id):
        cls.validations(request)
        async with cls.read_and_update_parent_obj(obj_id) as parent_obj:
            # import and validate data
            json = await request.json()
            body = CriterionCreateInput(**json)

            validate_access_token(request, parent_obj, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data

            parent_obj["criteria"].append(data)
            parent_obj["dateModified"] = get_now().isoformat()
        return {"data": BaseSerializer(data).data}

    @classmethod
    async def patch(cls, request, obj_id, criterion_id):
        cls.validations(request)
        async with cls.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            # import and validate data
            json = await request.json()
            body = CriterionUpdateInput(**json)

            validate_access_token(request, parent_obj, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update obj with valid data
            # mongo unwinded criteria, so here is only one item in `criteria`
            parent_obj["criteria"].update(data)
            parent_obj["dateModified"] = get_now().isoformat()

        return {"data": BaseSerializer(parent_obj["criteria"]).data}

    @classmethod
    async def delete(cls, request, obj_id, criterion_id):
        cls.validations(request)
        obj = await db.get_access_token(cls.obj_name, obj_id)
        validate_access_token(request, obj, None)
        dateModified = get_now().isoformat()
        await cls.delete_obj_criterion(obj_id, criterion_id, dateModified)
        return {"result": "success"}


class BaseCriteriaRGView(View):
    """
    Base view for criterion requirement group
    """

    @classmethod
    async def collection_get(cls, request, obj_id, criterion_id):
        parent_criteria = await cls.get_criterion(obj_id, criterion_id)
        data = RootSerializer(parent_criteria, show_owner=False).data
        return {"data": data["criteria"]["requirementGroups"]}

    @classmethod
    async def get(cls, request, obj_id, criterion_id, rg_id):
        parent_criterion = await cls.get_criterion(obj_id, criterion_id)
        data = RootSerializer(parent_criterion, show_owner=False).data
        response = find_item_by_id(data["criteria"]["requirementGroups"], rg_id, "requirementGroups")
        return {"data": response}

    @classmethod
    async def post(cls, request, obj_id, criterion_id):
        cls.validations(request)
        async with cls.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            # import and validate data
            json = await request.json()
            body = RGCreateInput(**json)

            validate_access_token(request, parent_obj, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            parent_obj["criteria"]["requirementGroups"].append(data)
            parent_obj["dateModified"] = get_now().isoformat()
        return {"data": BaseSerializer(data).data}

    @classmethod
    async def patch(cls, request, obj_id, criterion_id, rg_id):
        cls.validations(request)
        async with cls.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            # import and validate data
            json = await request.json()
            body = RGUpdateInput(**json)

            validate_access_token(request, parent_obj, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            rg = find_item_by_id(parent_obj["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            rg.update(data)
            parent_obj["dateModified"] = get_now().isoformat()

        return {"data": BaseSerializer(rg).data}

    @classmethod
    async def delete(cls, request, obj_id, criterion_id, rg_id):
        cls.validations(request)
        async with cls.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            validate_access_token(request, parent_obj, None)
            rg = find_item_by_id(parent_obj["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            parent_obj["criteria"]["requirementGroups"].remove(rg)
            parent_obj["dateModified"] = get_now().isoformat()
        return {"result": "success"}


class BaseCriteriaRGRequirementView(View):
    """
    Base view for criterion requirement
    """

    @classmethod
    async def collection_get(cls, request, obj_id, criterion_id, rg_id):
        criteria = await cls.get_criterion(obj_id, criterion_id)
        data = RootSerializer(criteria, show_owner=False).data
        rg = find_item_by_id(data["criteria"]["requirementGroups"], rg_id, "requirementGroups")
        return {"data": rg.get("requirements", [])}

    @classmethod
    async def get(cls, request, obj_id, criterion_id, rg_id, requirement_id):
        criterion = await cls.get_criterion(obj_id, criterion_id)
        data = RootSerializer(criterion, show_owner=False).data
        rg = find_item_by_id(data["criteria"]["requirementGroups"], rg_id, "requirementGroups")
        requirement = find_item_by_id(rg["requirements"], requirement_id, "requirements")
        return {"data": requirement}

    @classmethod
    async def post(cls, request, obj_id, criterion_id, rg_id):
        cls.validations(request)
        async with cls.read_and_update_criterion(obj_id, criterion_id) as profile:
            # import and validate data
            json = await request.json()
            if isinstance(json.get("data", {}), dict):
                body = RequirementCreateInput(**json)
                body.data = [body.data]
            elif isinstance(json["data"], list):
                body = BulkRequirementCreateInput(**json)

            validate_access_token(request, profile, body.access)
            # export data back to dict
            data = [r.dict_without_none() for r in body.data]
            # update profile with valid data
            rg = find_item_by_id(profile["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            rg["requirements"].extend(data)
            profile["dateModified"] = get_now().isoformat()
        return {"data": [BaseSerializer(r).data for r in data]}

    @classmethod
    async def patch(cls, request, obj_id, criterion_id, rg_id, requirement_id):
        cls.validations(request)
        async with cls.read_and_update_criterion(obj_id, criterion_id) as profile:
            # import and validate data
            json = await request.json()
            body = RequirementUpdateInput(**json)

            validate_access_token(request, profile, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            rg = find_item_by_id(profile["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            requirement = find_item_by_id(rg["requirements"], requirement_id, "requirements")
            requirement.update(data)
            Requirement(**requirement)
            profile["dateModified"] = get_now().isoformat()

        return {"data": BaseSerializer(requirement).data}

    @classmethod
    async def delete(cls, request, obj_id, criterion_id, rg_id, requirement_id):
        cls.validations(request)
        async with cls.read_and_update_criterion(obj_id, criterion_id) as profile:
            validate_access_token(request, profile, None)
            rg = find_item_by_id(profile["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            requirement = find_item_by_id(rg["requirements"], requirement_id, "requirements")
            rg["requirements"].remove(requirement)
            profile["dateModified"] = get_now().isoformat()
        return {"result": "success"}
