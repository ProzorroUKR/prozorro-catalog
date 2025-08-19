import logging
from copy import deepcopy

from typing import Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401
from aiohttp.web_exceptions import HTTPNotFound

from catalog import db
from catalog.auth import validate_access_token
from catalog.models.api import ErrorResponse
from catalog.models.document import DocumentPostInput, DocumentPutInput, DocumentPatchInput, DocumentList, \
    DocumentResponse
from catalog.serializers.document import DocumentSerializer
from catalog.handlers.base_document import BaseDocumentView, BaseDocumentItemView
from catalog.utils import get_now, find_item_by_id, get_revision_changes


logger = logging.getLogger(__name__)


class VendorBanDocumentMixin:

    parent_obj_name = "vendor_ban"

    @classmethod
    async def get_parent_obj(cls, vendor_id, ban_id):
        vendor = await db.read_vendor(vendor_id)
        return find_item_by_id(vendor.get("bans", []), ban_id, "ban")

    @classmethod
    async def validate_data(cls, request, body, parent_obj, parent_obj_id):
        validate_access_token(request, parent_obj, body.access)


class VendorBanDocumentView(VendorBanDocumentMixin, BaseDocumentView, PydanticView):

    async def get(self, vendor_id: str, ban_id: str, /) -> r200[DocumentList]:
        """
        Get list of vendor ban documents

        Tags: Vendor/Bans/Documents
        """
        return await BaseDocumentView.get(self, vendor_id, ban_id)

    async def post(
        self, vendor_id: str, ban_id: str, /, body: DocumentPostInput
    ) -> Union[r201[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Vendor ban document create

        Security: Basic: []
        Tags: Vendor/Bans/Documents
        """
        data = body.data.dict_without_none()

        async with db.read_and_update_vendor(vendor_id) as parent_obj:
            old_parent_obj = deepcopy(parent_obj)
            await self.validate_data(self.request, body, parent_obj, vendor_id)
            ban = find_item_by_id(parent_obj.get("bans", []), ban_id, "ban")
            now = get_now().isoformat()
            parent_obj["dateModified"] = ban['dateModified'] = data['datePublished'] = data['dateModified'] = now
            if "documents" not in ban:
                ban["documents"] = []
            ban["documents"].append(data)
            get_revision_changes(self.request, new_obj=parent_obj, old_obj=old_parent_obj)

            logger.info(
                f"Created {self.parent_obj_name} document {data['id']}",
                extra={
                    "MESSAGE_ID": f"{self.parent_obj_name}_document_create",
                    "document_id": data["id"],
                },
            )

        return {"data": DocumentSerializer(data).data}


class VendorBanDocumentItemView(VendorBanDocumentMixin, BaseDocumentItemView, PydanticView):

    async def get(self, vendor_id: str, ban_id: str, doc_id: str, /) -> Union[r200[DocumentResponse], r404[ErrorResponse]]:
        """
        Get vendor ban document

        Tags: Vendor/Bans/Documents
        """
        return await BaseDocumentItemView.get(self, vendor_id, doc_id, ban_id)

    async def put(
        self, vendor_id: str, ban_id: str, doc_id: str, /, body: DocumentPutInput,
    ) -> Union[r200[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Vendor ban document replace

        Security: Basic: []
        Tags: Vendor/Bans/Documents
        """
        async with db.read_and_update_vendor(vendor_id) as parent_obj:
            old_parent_obj = deepcopy(parent_obj)
            # import and validate data
            json = await self.request.json()
            json["data"]["id"] = doc_id
            body = DocumentPutInput(**json)
            await self.validate_data(self.request, body, parent_obj, vendor_id)
            # find & append doc
            ban = find_item_by_id(parent_obj.get("bans", []), ban_id, "ban")
            for doc in ban.get("documents", "")[::-1]:
                if doc["id"] == doc_id:
                    data = body.data.dict_without_none()
                    data["id"] = doc_id
                    parent_obj["dateModified"] = ban["dateModified"] = data["datePublished"] = data["dateModified"] = get_now().isoformat()
                    ban["documents"].append(data)
                    break
            else:
                raise HTTPNotFound(text="Document not found")
            get_revision_changes(self.request, new_obj=parent_obj, old_obj=old_parent_obj)

            logger.info(
                f"Updated {self.parent_obj_name} document {doc_id}",
                extra={"MESSAGE_ID": f"{self.parent_obj_name}_document_put"},
            )

        return {"data": DocumentSerializer(data).data}

    async def patch(
        self, vendor_id: str, ban_id: str, doc_id: str, /, body: DocumentPatchInput,
    ) -> Union[r200[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Product vendor ban update

        Security: Basic: []
        Tags: Vendor/Bans/Documents
        """
        async with db.read_and_update_vendor(vendor_id) as parent_obj:
            old_parent_obj = deepcopy(parent_obj)
            await self.validate_data(self.request, body, parent_obj, vendor_id)
            # export data back to dict
            data = body.data.dict_without_none()
            # find & update doc
            ban = find_item_by_id(parent_obj.get("bans", []), ban_id, "ban")
            for doc in ban.get("documents", "")[::-1]:
                if doc["id"] == doc_id:
                    initial = dict(doc)
                    doc.update(data)
                    if initial != doc:
                        parent_obj["dateModified"] = ban['dateModified'] = doc['dateModified'] = get_now().isoformat()
                    break
            else:
                raise HTTPNotFound(text="Document not found")
            get_revision_changes(self.request, new_obj=parent_obj, old_obj=old_parent_obj)

            logger.info(
                f"Updated {self.parent_obj_name} document {doc_id}",
                extra={"MESSAGE_ID": f"{self.parent_obj_name}_document_patch"},
            )
        return {"data": DocumentSerializer(doc).data}
