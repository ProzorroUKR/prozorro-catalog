import random
from copy import deepcopy
import logging

from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPBadRequest, HTTPConflict
from pymongo.errors import OperationFailure

from catalog import db
from catalog.models.profile import (
    LocalizationProfileInput,
    LocalizationProfileUpdateInput,
    ProfileCreateInput,
    ProfileUpdateInput,
    DeprecatedProfileCreateInput,
    DeprecatedLocProfileInput,
)
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
    ProfileRequirement,
)
from catalog.validations import validate_profile_requirements
from catalog.state.profile import ProfileState, LocalizationProfileState


logger = logging.getLogger(__name__)


@class_view_swagger_path('/app/swagger/profiles')
class ProfileView(View):

    @classmethod
    def is_localized(cls, data):
        return data.get("relatedCategory", "").startswith("99999999")

    @classmethod
    def get_state_class(cls, data):
        if cls.is_localized(data):
            return LocalizationProfileState
        return ProfileState

    @classmethod
    async def get_input(cls, request, profile=None):
        json = await request.json()
        if not profile:
            if cls.is_localized(json.get("data", {})):
                input_class = DeprecatedLocProfileInput if request.method == 'PUT' else LocalizationProfileInput
            else:
                input_class = DeprecatedProfileCreateInput if request.method == 'PUT' else ProfileCreateInput
        else:
            if cls.is_localized(profile):
                input_class = LocalizationProfileUpdateInput
            else:
                input_class = ProfileUpdateInput

        return input_class(**json)

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

        body = await cls.get_input(request)
        # export data back to dict
        data = body.data.dict_without_none()
        if profile_id != data['id']:
            raise HTTPBadRequest(text='id mismatch')

        category_id = data['relatedCategory']
        category = await db.read_category(category_id)  # ensure exists
        validate_access_token(request, category, body.access)

        await cls.get_state_class(data).on_put(data, category)

        access = set_access_token(request, data)
        await db.insert_profile(data)

        logger.info(
            f"Created profile {data['id']}",
            extra={
                "MESSAGE_ID": "profile_create_put",
                "profile_id": data['id'],
            },
        )
        response = {"data": RootSerializer(data).data,
                    "access": access}
        return response

    @classmethod
    async def post(cls, request):
        validate_accreditation(request, "profile")
        # import and validate data

        body = await cls.get_input(request)
        # export data back to dict
        data = body.data.dict_without_none()

        category_id = data['relatedCategory']
        category = await db.read_category(category_id)  # ensure exists
        validate_access_token(request, category, body.access)

        await cls.get_state_class(data).on_put(data, category)

        access = set_access_token(request, data)
        await db.insert_profile(data)

        logger.info(
            f"Created profile {data['id']}",
            extra={
                "MESSAGE_ID": "profile_create_post",
                "profile_id": data['id']
            },
        )

        response = {
            "data": RootSerializer(data).data,
            "access": access,
        }
        return response

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def patch(cls, request, profile_id):
        validate_accreditation(request, "profile")
        async with db.read_and_update_profile(profile_id) as profile:
            body = await cls.get_input(request, profile)

            validate_access_token(request, profile, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            old_profile = deepcopy(profile)
            profile.update(data)
            await cls.get_state_class(data).on_patch(old_profile, profile)

            logger.info(
                f"Updated profile {profile_id}",
                extra={"MESSAGE_ID": "profile_patch"},
            )

        return {"data": RootSerializer(profile).data}


class ProfileCriteriaMixin:

    obj_name = "profile"

    @classmethod
    def read_and_update_parent_obj(cls, obj_id):
        return db.read_and_update_profile(obj_id)


@class_view_swagger_path('/app/swagger/profiles/criterion')
class ProfileCriteriaView(ProfileCriteriaMixin, BaseCriteriaView):

    @classmethod
    async def collection_get(cls, request, obj_id):
        # That was made for swagger, maybe exist better solution
        return await super().collection_get(request, obj_id)

    @classmethod
    async def get(cls, request, obj_id, criterion_id):
        return await super().get(request, obj_id, criterion_id)

    @classmethod
    async def post(cls, request, obj_id):
        return await super().post(request, obj_id)

    @classmethod
    async def patch(cls, request, obj_id, criterion_id):
        return await super().patch(request, obj_id, criterion_id)

    @classmethod
    async def delete(cls, request, obj_id, criterion_id):
        cls.validations(request)
        obj = await db.get_access_token(cls.obj_name, obj_id)
        validate_access_token(request, obj, None)
        dateModified = get_now().isoformat()
        await cls.delete_obj_criterion(obj_id, criterion_id, dateModified)
        return {"result": "success"}


@class_view_swagger_path('/app/swagger/profiles/criterion/requirementGroups')
class ProfileCriteriaRGView(ProfileCriteriaMixin, BaseCriteriaRGView):

    @classmethod
    async def collection_get(cls, request, obj_id, criterion_id):
        return await super().collection_get(request, obj_id, criterion_id)

    @classmethod
    async def get(cls, request, obj_id, criterion_id, rg_id):
        return await super().get(request, obj_id, criterion_id, rg_id)

    @classmethod
    async def post(cls, request, obj_id, criterion_id):
        return await super().post(request, obj_id, criterion_id)

    @classmethod
    async def patch(cls, request, obj_id, criterion_id, rg_id):
        return await super().patch(request, obj_id, criterion_id, rg_id)

    @classmethod
    async def delete(cls, request, obj_id, criterion_id, rg_id):
        cls.validations(request)
        async with cls.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            validate_access_token(request, parent_obj, None)
            rg = find_item_by_id(parent_obj["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            parent_obj["criteria"]["requirementGroups"].remove(rg)
            parent_obj["dateModified"] = get_now().isoformat()
        return {"result": "success"}


@class_view_swagger_path('/app/swagger/profiles/criterion/requirementGroups/requirements')
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
    def get_main_model_class(cls):
        return ProfileRequirement

    @classmethod
    async def requirement_validations(cls, parent_obj, data):
        category = await db.read_category(parent_obj["relatedCategory"])
        validate_profile_requirements(data, category)

    @classmethod
    async def collection_get(cls, request, obj_id, criterion_id, rg_id):
        return await super().collection_get(request, obj_id, criterion_id, rg_id)

    @classmethod
    async def get(cls, request, obj_id, criterion_id, rg_id, requirement_id):
        return await super().get(request, obj_id, criterion_id, rg_id, requirement_id)

    @classmethod
    async def post(cls, request, obj_id, criterion_id, rg_id):
        return await super().post(request, obj_id, criterion_id, rg_id)

    @classmethod
    async def patch(cls, request, obj_id, criterion_id, rg_id, requirement_id):
        return await super().patch(request, obj_id, criterion_id, rg_id, requirement_id)

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

