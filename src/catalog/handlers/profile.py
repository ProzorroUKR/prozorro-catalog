import random
from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPBadRequest, HTTPNotFound, HTTPConflict
from pymongo.errors import OperationFailure
from catalog import db
from catalog.models.profile import ProfileCreateInput, ProfileUpdateInput
from catalog.models.criteria import (
    CriterionCreateInput,
    CriterionUpdateInput,
    RGCreateInput,
    RGUpdateInput,
    RequirementCreateInput,
    RequirementUpdateInput,
    BulkRequirementCreateInput,
    Requirement,
)
from catalog.swagger import class_view_swagger_path
from catalog.utils import pagination_params, get_now, async_retry, find_item_by_id
from catalog.auth import validate_access_token, validate_accreditation, set_access_token
from catalog.serializers.base import RootSerializer, BaseSerializer


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


@class_view_swagger_path('/app/swagger/profiles/criteria')
class ProfileCriteriaView(View):
    @classmethod
    async def collection_get(cls, request, profile_id):
        profile_criteria = await db.read_profile_criteria(profile_id=profile_id)
        data = RootSerializer(profile_criteria, show_owner=False).data
        return {"data": data["criteria"]}

    @classmethod
    async def get(cls, request, profile_id, criterion_id):
        profile_criterion = await db.read_profile_criterion(profile_id, criterion_id)
        data = RootSerializer(profile_criterion, show_owner=False).data
        return {"data": data["criteria"]}

    @classmethod
    async def post(cls, request, profile_id):
        validate_accreditation(request, "profile")
        async with db.read_and_update_profile(profile_id) as profile:
            # import and validate data
            json = await request.json()
            body = CriterionCreateInput(**json)

            validate_access_token(request, profile, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data

            profile["criteria"].append(data)
            profile["dateModified"] = get_now().isoformat()
        return {"data": BaseSerializer(data).data}

    @classmethod
    async def patch(cls, request, profile_id, criterion_id):
        validate_accreditation(request, "profile")
        async with db.read_and_update_profile_criterion(profile_id, criterion_id) as profile:
            # import and validate data
            json = await request.json()
            body = CriterionUpdateInput(**json)

            validate_access_token(request, profile, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            # mongo unwinded criteria, so here is only one item in `criteria`
            profile["criteria"].update(data)
            profile["dateModified"] = get_now().isoformat()

        return {"data": BaseSerializer(profile["criteria"]).data}

    @classmethod
    async def delete(cls, request, profile_id, criterion_id):
        validate_accreditation(request, "profile")
        profile = await db.get_access_token(profile_id)
        validate_access_token(request, profile, None)
        dateModified = get_now().isoformat()
        await db.delete_profile_criterion(profile_id, criterion_id, dateModified)
        return {"result": "success"}


@class_view_swagger_path('/app/swagger/profiles/criteria/requirementGroups')
class ProfileCriteriaRGView(View):
    @classmethod
    async def collection_get(cls, request, profile_id, criterion_id):
        profile_criteria = await db.read_profile_criterion(profile_id, criterion_id)
        data = RootSerializer(profile_criteria, show_owner=False).data
        return {"data": data["criteria"]["requirementGroups"]}

    @classmethod
    async def get(cls, request, profile_id, criterion_id, rg_id):
        profile_criterion = await db.read_profile_criterion(profile_id, criterion_id)
        data = RootSerializer(profile_criterion, show_owner=False).data
        response = find_item_by_id(data["criteria"]["requirementGroups"], rg_id, "requirementGroups")
        return {"data": response}

    @classmethod
    async def post(cls, request, profile_id, criterion_id):
        validate_accreditation(request, "profile")
        async with db.read_and_update_profile_criterion(profile_id, criterion_id) as profile:
            # import and validate data
            json = await request.json()
            body = RGCreateInput(**json)

            validate_access_token(request, profile, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            profile["criteria"]["requirementGroups"].append(data)
            profile["dateModified"] = get_now().isoformat()
        return {"data": BaseSerializer(data).data}

    @classmethod
    async def patch(cls, request, profile_id, criterion_id, rg_id):
        validate_accreditation(request, "profile")
        async with db.read_and_update_profile_criterion(profile_id, criterion_id) as profile:
            # import and validate data
            json = await request.json()
            body = RGUpdateInput(**json)

            validate_access_token(request, profile, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            rg = find_item_by_id(profile["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            rg.update(data)
            profile["dateModified"] = get_now().isoformat()

        return {"data": BaseSerializer(rg).data}

    @classmethod
    async def delete(cls, request, profile_id, criterion_id, rg_id):
        validate_accreditation(request, "profile")
        async with db.read_and_update_profile_criterion(profile_id, criterion_id) as profile:
            validate_access_token(request, profile, None)
            rg = find_item_by_id(profile["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            profile["criteria"]["requirementGroups"].remove(rg)
            profile["dateModified"] = get_now().isoformat()
        return {"result": "success"}


@class_view_swagger_path('/app/swagger/profiles/criteria/requirementGroups/requirements')
class ProfileCriteriaRGRequirementView(View):
    @classmethod
    async def collection_get(cls, request, profile_id, criterion_id, rg_id):
        profile_criteria = await db.read_profile_criterion(profile_id, criterion_id)
        data = RootSerializer(profile_criteria, show_owner=False).data
        rg = find_item_by_id(data["criteria"]["requirementGroups"], rg_id, "requirementGroups")
        return {"data": rg.get("requirements", [])}

    @classmethod
    async def get(cls, request, profile_id, criterion_id, rg_id, requirement_id):
        profile_criterion = await db.read_profile_criterion(profile_id, criterion_id)
        data = RootSerializer(profile_criterion, show_owner=False).data
        rg = find_item_by_id(data["criteria"]["requirementGroups"], rg_id, "requirementGroups")
        requirement = find_item_by_id(rg["requirements"], requirement_id, "requirements")
        return {"data": requirement}

    @classmethod
    async def post(cls, request, profile_id, criterion_id, rg_id):
        validate_accreditation(request, "profile")
        async with db.read_and_update_profile_criterion(profile_id, criterion_id) as profile:
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
    async def patch(cls, request, profile_id, criterion_id, rg_id, requirement_id):
        validate_accreditation(request, "profile")
        async with db.read_and_update_profile_criterion(profile_id, criterion_id) as profile:
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
    async def delete(cls, request, profile_id, criterion_id, rg_id, requirement_id):
        validate_accreditation(request, "profile")
        async with db.read_and_update_profile_criterion(profile_id, criterion_id) as profile:
            validate_access_token(request, profile, None)
            rg = find_item_by_id(profile["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            requirement = find_item_by_id(rg["requirements"], requirement_id, "requirements")
            rg["requirements"].remove(requirement)
            profile["dateModified"] = get_now().isoformat()
        return {"result": "success"}
