import random
from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPBadRequest, HTTPConflict
from pymongo.errors import OperationFailure
from catalog import db
from catalog.models.profile import ProfileCreateInput, ProfileUpdateInput
from catalog.swagger import class_view_swagger_path
from catalog.utils import pagination_params, get_now, async_retry, find_item_by_id
from catalog.auth import validate_access_token, validate_accreditation, set_access_token
from catalog.serializers.base import RootSerializer
from catalog.handlers.base_criteria import (
    BaseCriteriaView,
    BaseCriteriaRGView,
    BaseCriteriaRGRequirementView,
)
from catalog.models.criteria import (
    ProfileRequirementCreateInput,
    ProfileBulkRequirementCreateInput,
    ProfileRequirementUpdateInput,
)
from catalog.validations import validate_profile_requirements


@class_view_swagger_path('/app/swagger/profiles')
class ProfileView(View):

    @classmethod
    async def collection_get(cls, request):
        offset, limit, reverse = pagination_params(request)
        response = await db.find_profiles(
            offset=offset,
            limit=limit,
            reverse=reverse,
        )
        return response

    @classmethod
    async def get(cls, request, profile_id):
        profile = await db.read_profile(profile_id)
        return {"data": RootSerializer(profile).data}

    @classmethod
    async def put(cls, request, profile_id):
        validate_accreditation(request, "profile")
        # import and validate data
        json = await request.json()
        body = ProfileCreateInput(**json)
        # export data back to dict
        data = body.data.dict_without_none()
        if profile_id != data['id']:
            raise HTTPBadRequest(text='id mismatch')

        category_id = data['relatedCategory']
        category = await db.read_category(category_id)  # ensure exists
        validate_access_token(request, category, body.access)

        access = set_access_token(request, data)
        data['dateModified'] = get_now().isoformat()
        await db.insert_profile(data)

        response = {"data": RootSerializer(data).data,
                    "access": access}
        return response

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def patch(cls, request, profile_id):
        validate_accreditation(request, "profile")
        async with db.read_and_update_profile(profile_id) as profile:
            # import and validate data
            json = await request.json()
            body = ProfileUpdateInput(**json)

            validate_access_token(request, profile, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            data['dateModified'] = get_now().isoformat()
            profile.update(data)

        return {"data": RootSerializer(profile).data}


class ProfileCriteriaMixin:

    obj_name = "profile"

    @classmethod
    def read_and_update_parent_obj(cls, obj_id):
        return db.read_and_update_profile(obj_id)


@class_view_swagger_path('/app/swagger/profiles/criteria')
class ProfileCriteriaView(ProfileCriteriaMixin, BaseCriteriaView):
    @classmethod
    async def delete(cls, request, obj_id, criterion_id):
        cls.validations(request)
        obj = await db.get_access_token(cls.obj_name, obj_id)
        validate_access_token(request, obj, None)
        dateModified = get_now().isoformat()
        await cls.delete_obj_criterion(obj_id, criterion_id, dateModified)
        return {"result": "success"}


@class_view_swagger_path('/app/swagger/profiles/criteria/requirementGroups')
class ProfileCriteriaRGView(ProfileCriteriaMixin, BaseCriteriaRGView):
    @classmethod
    async def delete(cls, request, obj_id, criterion_id, rg_id):
        cls.validations(request)
        async with cls.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            validate_access_token(request, parent_obj, None)
            rg = find_item_by_id(parent_obj["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            parent_obj["criteria"]["requirementGroups"].remove(rg)
            parent_obj["dateModified"] = get_now().isoformat()
        return {"result": "success"}


@class_view_swagger_path('/app/swagger/profiles/criteria/requirementGroups/requirements')
class ProfileCriteriaRGRequirementView(ProfileCriteriaMixin, BaseCriteriaRGRequirementView):

    @classmethod
    async def get_body_from_model(cls, request):
        json = await request.json()
        body = None
        if request.method == "POST":
            if isinstance(json.get("data", {}), dict):
                body = ProfileRequirementCreateInput(**json)
                body.data = [body.data]
            elif isinstance(json["data"], list):
                body = ProfileBulkRequirementCreateInput(**json)
        elif request.method == "PATCH":
            return ProfileRequirementUpdateInput(**json)
        return body

    @classmethod
    async def requirement_validations(cls, parent_obj, data):
        category = await db.read_category(parent_obj["relatedCategory"])
        validate_profile_requirements(data, category)

    @classmethod
    async def delete(cls, request, obj_id, criterion_id, rg_id, requirement_id):
        validate_accreditation(request, "profile")
        async with cls.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            validate_access_token(request, parent_obj, None)
            rg = find_item_by_id(parent_obj["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            requirement = find_item_by_id(rg["requirements"], requirement_id, "requirements")
            rg["requirements"].remove(requirement)
            parent_obj["dateModified"] = get_now().isoformat()
        return {"result": "success"}

