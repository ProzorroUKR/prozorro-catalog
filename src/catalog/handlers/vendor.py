import logging
from typing import Optional, Union

from catalog import db
from catalog.models.api import PaginatedList, ErrorResponse
from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401
from catalog.state.vendor import VendorState
from catalog.auth import set_access_token, validate_accreditation, validate_access_token
from catalog.utils import pagination_params, get_revision_changes
from catalog.models.vendor import VendorPostInput, VendorPatchInput, VendorCreateResponse, VendorResponse, \
    VendorSignResponse
from catalog.serializers.vendor import VendorSignSerializer, VendorSerializer


logger = logging.getLogger(__name__)


class VendorView(PydanticView):
    state = VendorState

    async def get(
        self, /, offset: Optional[str] = None, limit: Optional[int] = 100, descending: Optional[Union[int, str]] = 0,
    ) -> r200[PaginatedList]:
        """
        Get a list of vendors

        Tags: Vendors
        """
        offset, limit, reverse = pagination_params(self.request)
        response = await db.find_vendors(
            offset=offset,
            limit=limit,
            reverse=reverse,
            filters={"isActivated": True}
        )
        return response

    async def post(
        self, /, body: VendorPostInput
    ) -> Union[r201[VendorCreateResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Create vendor

        Security: Basic: []
        Tags: Vendors
        """
        validate_accreditation(self.request, "vendors")
        data = body.data.dict_without_none()
        await self.state.on_post(data)
        access = set_access_token(self.request, data)
        get_revision_changes(self.request, new_obj=data)
        await db.insert_vendor(data)

        logger.info(
            f"Created vendor {data['id']}",
            extra={
                "MESSAGE_ID": "vendor_create",
                "vendor_id": data["id"],
            },
        )
        response = {"data": VendorSerializer(data).data,
                    "access": access}
        return response


class VendorItemView(PydanticView):
    state = VendorState

    async def get(self, vendor_id: str, /) -> Union[r200[VendorResponse], r400[ErrorResponse], r404[ErrorResponse]]:
        """
        Get a vendor

        Tags: Vendors
        """
        obj = await db.read_vendor(vendor_id)
        return {"data": VendorSerializer(obj).data}

    async def patch(
        self, vendor_id: str, /, body: VendorPatchInput
    ) -> Union[r200[VendorResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Vendor update

        Security: Basic: []
        Tags: Vendors
        """
        # validate_accreditation(request, "category")
        async with db.read_and_update_vendor(vendor_id) as vendor:
            validate_access_token(self.request, vendor, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # update profile with valid data
            initial_data = dict(vendor)
            vendor.update(data)
            await self.state.on_patch(initial_data, vendor)
            get_revision_changes(self.request, new_obj=vendor, old_obj=initial_data)

        logger.info(
            f"Updated vendor {vendor_id}",
            extra={"MESSAGE_ID": "vendor_patch"},
        )

        return {"data": VendorSerializer(vendor).data}


class VendorSignItemView(PydanticView):
    async def get(self, vendor_id: str, /) -> Union[r200[VendorSignResponse], r404[ErrorResponse]]:
        """
        Get a vendor for signing

        Tags: Vendors
        """
        obj = await db.read_vendor(vendor_id)
        return {"data": VendorSignSerializer(obj).data}
