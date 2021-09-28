import ast
import random
from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPBadRequest, HTTPNotFound, HTTPConflict
from aiohttp_swagger import swagger_path
from pymongo.errors import OperationFailure

from catalog import db
from catalog.models import Profile
from catalog.models.base import unchanged
from catalog.models.profile import ProfileCreateInput, ProfileUpdateInput
from catalog.swagger import class_view_swagger_path
from catalog.utils import pagination_params, get_now, requests_sequence_params, async_retry
from catalog.auth import validate_access_token, validate_accreditation, set_access_token


@class_view_swagger_path('/swagger/profiles')
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
        if not profile:
            raise HTTPNotFound(text="Not found")
        return {"data": profile}

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

        data.pop("access")
        response = {"data": data, "access": access}
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
            profile.update(data)
            data['dateModified'] = get_now().isoformat()

        profile.pop("access")
        return {"data": profile}
