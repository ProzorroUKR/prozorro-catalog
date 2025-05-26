import random
from copy import deepcopy
import logging
from typing import Optional, Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401
from aiohttp.web import HTTPBadRequest, HTTPConflict
from pymongo.errors import OperationFailure

from catalog import db
from catalog.models.api import PaginatedList, ErrorResponse
from catalog.models.common import SuccessResponse
from catalog.models.profile import (
    LocalizationProfileInput,
    LocalizationProfileUpdateInput,
    ProfileCreateInput,
    ProfileUpdateInput,
    DeprecatedProfileCreateInput,
    DeprecatedLocProfileInput, ProfileCreateResponse, ProfileResponse, RequestProfileCreateInput,
    DeprecatedRequestProfileCreateInput, RequestProfileUpdateInput,
)
from catalog.swagger import class_view_swagger_path
from catalog.utils import pagination_params, get_now, async_retry, find_item_by_id
from catalog.auth import validate_access_token, validate_accreditation, set_access_token
from catalog.serializers.base import RootSerializer
from catalog.handlers.base_criteria import (
    BaseCriteriaViewMixin,
    BaseCriteriaItemViewMixin,
    BaseCriteriaRGViewMixin,
    BaseCriteriaRGItemViewMixin,
    BaseCriteriaRGRequirementViewMixin,
    BaseCriteriaRGRequirementItemViewMixin,
)
from catalog.models.criteria import (
    ProfileRequirementCreateInput,
    ProfileBulkRequirementCreateInput,
    ProfileRequirementUpdateInput,
    ProfileRequirement, CriterionListResponse, CriterionCreateInput, CriterionResponse, CriterionUpdateInput,
    RGListResponse, RGCreateInput, RGResponse, RGUpdateInput, RequirementListResponse, RequirementResponse,
    RequirementCreateInput, RequirementUpdateInput,
)
from catalog.validations import validate_profile_requirements
from catalog.state.profile import ProfileState, LocalizationProfileState


logger = logging.getLogger(__name__)


class ProfileViewMixin:

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


class ProfileView(ProfileViewMixin, PydanticView):
    async def get(
        self, /, offset: Optional[str] = None, limit: Optional[int] = 100, descending: Optional[int] = 0,
    ) -> r200[PaginatedList]:
        """
        Get a list of profiles

        Tags: Profiles
        """
        offset, limit, reverse = pagination_params(self.request)
        response = await db.find_profiles(
            offset=offset,
            limit=limit,
            reverse=reverse,
        )
        return response

    async def post(
            self, /, body: RequestProfileCreateInput
    ) -> Union[r201[ProfileCreateResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Create profile

        Security: Basic: []
        Tags: Profiles
        """
        validate_accreditation(self.request, "profile")
        # import and validate data

        body = await self.get_input(self.request)
        # export data back to dict
        data = body.data.dict_without_none()

        category_id = data['relatedCategory']
        category = await db.read_category(category_id)  # ensure exists
        validate_access_token(self.request, category, body.access)

        await self.get_state_class(data).on_put(data, category)

        access = set_access_token(self.request, data)
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


class ProfileItemView(ProfileViewMixin, PydanticView):

    async def get(self, profile_id: str, /) -> Union[r201[ProfileResponse], r400[ErrorResponse], r404[ErrorResponse]]:
        """
        Get profile

        Tags: Profiles
        """
        profile = await db.read_profile(profile_id)
        return {"data": RootSerializer(profile).data}

    async def put(
        self, profile_id: str, /, body: DeprecatedRequestProfileCreateInput
    ) -> Union[r201[ProfileResponse], r400[ErrorResponse]]:
        """
        Create profile

        Security: Basic: []
        Tags: Profiles
        """
        validate_accreditation(self.request, "profile")
        # import and validate data

        body = await self.get_input(self.request)
        # export data back to dict
        data = body.data.dict_without_none()
        if profile_id != data['id']:
            raise HTTPBadRequest(text='id mismatch')

        category_id = data['relatedCategory']
        category = await db.read_category(category_id)  # ensure exists
        validate_access_token(self.request, category, body.access)

        await self.get_state_class(data).on_put(data, category)

        access = set_access_token(self.request, data)
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

    async def patch(
            self, profile_id: str, /, body: RequestProfileUpdateInput
    ) -> Union[r200[ProfileResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Profile update

        Security: Basic: []
        Tags: Profiles
        """
        validate_accreditation(self.request, "profile")
        async with db.read_and_update_profile(profile_id) as profile:
            body = await self.get_input(self.request, profile)

            validate_access_token(self.request, profile, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            old_profile = deepcopy(profile)
            profile.update(data)
            await self.get_state_class(data).on_patch(old_profile, profile)

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


class ProfileCriteriaView(ProfileCriteriaMixin, BaseCriteriaViewMixin, PydanticView):
    async def get(self, obj_id: str, /) -> r200[CriterionListResponse]:
        """
        Get a list of object criteria

        Tags: Profile/Criteria
        """
        return await BaseCriteriaViewMixin.get(self, obj_id)

    async def post(
        self, obj_id: str, /, body: CriterionCreateInput
    ) -> Union[r201[CriterionListResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Object criteria create

        Security: Basic: []
        Tags: Profile/Criteria
        """
        return await BaseCriteriaViewMixin.post(self, obj_id, body)


class ProfileCriteriaItemView(ProfileCriteriaMixin, BaseCriteriaItemViewMixin, PydanticView):
    async def get(self, obj_id: str, criterion_id: str, /) -> Union[r200[CriterionResponse], r404[ErrorResponse]]:
        """
        Get an object criterion

        Tags: Profile/Criteria
        """
        return await BaseCriteriaItemViewMixin.get(self, obj_id, criterion_id)

    async def patch(
        self, obj_id: str, criterion_id: str, /, body: CriterionUpdateInput
    ) -> Union[r200[CriterionResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Object criterion update

        Security: Basic: []
        Tags: Profile/Criteria
        """
        return await BaseCriteriaItemViewMixin.patch(self, obj_id, criterion_id, body)

    async def delete(self, obj_id: str, criterion_id: str, /) -> Union[r200[SuccessResponse], r404[ErrorResponse]]:
        """
        Object criterion delete

        Security: Basic: []
        Tags: Profile/Criteria
        """
        self.validations()
        obj = await db.get_access_token(self.obj_name, obj_id)
        validate_access_token(self.request, obj, None)
        dateModified = get_now().isoformat()
        await self.delete_obj_criterion(obj_id, criterion_id, dateModified)
        return {"result": "success"}


class ProfileCriteriaRGView(ProfileCriteriaMixin, BaseCriteriaRGViewMixin, PydanticView):
    async def get(self, obj_id: str, criterion_id: str, /) -> r200[RGListResponse]:
        """
        Get a list of requirementGroups

        Tags: Profile/Criteria/RequirementGroups
        """
        return await BaseCriteriaRGViewMixin.get(self, obj_id, criterion_id)

    async def post(
        self, obj_id: str, criterion_id: str, /, body: RGCreateInput
    ) -> Union[r201[RGResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        RequirementGroup create

        Security: Basic: []
        Tags: Profile/Criteria/RequirementGroups
        """
        return await BaseCriteriaRGViewMixin.post(self, obj_id, criterion_id, body)


class ProfileCriteriaRGItemView(ProfileCriteriaMixin, BaseCriteriaRGItemViewMixin, PydanticView):
    async def get(self, obj_id: str, criterion_id: str, rg_id: str, /) -> Union[r200[RGResponse], r404[ErrorResponse]]:
        """
        Get a requirementGroup

        Tags: Profile/Criteria/RequirementGroups
        """
        return await BaseCriteriaRGItemViewMixin.get(self, obj_id,criterion_id,  rg_id)

    async def patch(
            self, obj_id: str, criterion_id: str, rg_id: str, /, body: RGUpdateInput
    ) -> Union[r200[RGResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        RequirementGroup update

        Security: Basic: []
        Tags: Profile/Criteria/RequirementGroups
        """
        return await BaseCriteriaRGItemViewMixin.patch(self, obj_id, criterion_id, rg_id, body)

    async def delete(
        self, obj_id: str, criterion_id: str, rg_id: str, /
    ) -> Union[r200[SuccessResponse], r404[ErrorResponse]]:
        """
        Object criterion requirement group delete

        Security: Basic: []
        Tags: Profile/Criteria/RequirementGroups
        """
        self.validations()
        async with self.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            validate_access_token(self.request, parent_obj, None)
            rg = find_item_by_id(parent_obj["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            parent_obj["criteria"]["requirementGroups"].remove(rg)
            parent_obj["dateModified"] = get_now().isoformat()
        return {"result": "success"}


class ProfileCriteriaRGRequirementView(ProfileCriteriaMixin, BaseCriteriaRGRequirementViewMixin, PydanticView):

    async def get_body_from_model(self):
        json = await self.request.json()
        body = None
        if isinstance(json.get("data", {}), dict):
            body = ProfileRequirementCreateInput(**json)
            body.data = [body.data]
        elif isinstance(json["data"], list):
            body = ProfileBulkRequirementCreateInput(**json)
        return body

    @classmethod
    def get_main_model_class(cls):
        return ProfileRequirement

    @classmethod
    async def requirement_validations(cls, parent_obj, data):
        category = await db.read_category(parent_obj["relatedCategory"])
        validate_profile_requirements(data, category)

    async def get(self, obj_id: str, criterion_id: str, rg_id: str, /) -> r200[RequirementListResponse]:
        """
        Get a list of requirements

        Tags: Profile/Criteria/RequirementGroups/Requirements
        """
        return await BaseCriteriaRGRequirementViewMixin.get(self, obj_id, criterion_id, rg_id)

    async def post(
            self, obj_id: str, criterion_id: str, rg_id: str, /, body: RequirementCreateInput
    ) -> Union[r201[RequirementResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Requirement create

        Security: Basic: []
        Tags: Profile/Criteria/RequirementGroups/Requirements
        """
        return await BaseCriteriaRGRequirementViewMixin.post(self, obj_id, criterion_id, rg_id, body)


class ProfileCriteriaRGRequirementItemView(ProfileCriteriaMixin, BaseCriteriaRGRequirementItemViewMixin, PydanticView):
    async def get_body_from_model(self):
        json = await self.request.json()
        return ProfileRequirementUpdateInput(**json)

    @classmethod
    def get_main_model_class(cls):
        return ProfileRequirement

    @classmethod
    async def requirement_validations(cls, parent_obj, data):
        category = await db.read_category(parent_obj["relatedCategory"])
        validate_profile_requirements(data, category)

    async def get(
            self, obj_id: str, criterion_id: str, rg_id: str, requirement_id: str, /
    ) -> Union[r200[RequirementResponse], r404[ErrorResponse]]:
        """
        Get a requirement

        Tags: Profile/Criteria/RequirementGroups/Requirements
        """
        return await BaseCriteriaRGRequirementItemViewMixin.get(self, obj_id, criterion_id, rg_id, requirement_id)

    async def patch(
            self, obj_id: str, criterion_id: str, rg_id: str, requirement_id: str, /, body: RequirementUpdateInput
    ) -> Union[r200[RequirementResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Requirement update

        Security: Basic: []
        Tags: Profile/Criteria/RequirementGroups/Requirements
        """
        return await BaseCriteriaRGRequirementItemViewMixin.patch(self, obj_id, criterion_id, rg_id, requirement_id, body)

    async def delete(
        self, obj_id: str, criterion_id: str, rg_id: str, requirement_id: str, /
    ) -> Union[r200[SuccessResponse], r404[ErrorResponse]]:
        """
        Object criterion requirement delete

        Security: Basic: []
        Tags: Profile/Criteria/RequirementGroups/Requirements
        """
        validate_accreditation(self.request, "profile")
        async with self.read_and_update_criterion(obj_id, criterion_id) as parent_obj:
            validate_access_token(self.request, parent_obj, None)
            rg = find_item_by_id(parent_obj["criteria"]["requirementGroups"], rg_id, "requirementGroups")
            requirement = find_item_by_id(rg["requirements"], requirement_id, "requirements")
            rg["requirements"].remove(requirement)
            parent_obj["dateModified"] = get_now().isoformat()
        return {"result": "success"}

