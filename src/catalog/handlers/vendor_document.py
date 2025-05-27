from typing import Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401

from catalog import db
from catalog.handlers.base_document import BaseDocumentView, BaseDocumentItemView
from catalog.auth import validate_access_token
from catalog.models.api import ErrorResponse
from catalog.models.document import DocumentResponse, DocumentPostInput, DocumentList, DocumentPutInput, \
    DocumentPatchInput


class VendorDocumentMixin:

    parent_obj_name = "vendor"

    @classmethod
    async def get_parent_obj(cls, vendor_id, child_obj_id=None):
        return await db.read_vendor(vendor_id)

    @classmethod
    def read_and_update_object(cls, vendor_id, child_obj_id=None):
        return db.read_and_update_vendor(vendor_id)

    @classmethod
    async def validate_data(cls, request, body, parent_obj, parent_obj_id):
        validate_access_token(request, parent_obj, body.access)


class VendorDocumentView(VendorDocumentMixin, BaseDocumentView, PydanticView):
    async def post(
        self, vendor_id: str, /, body: DocumentPostInput
    ) -> Union[r201[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Vendor document create

        Security: Basic: []
        Tags: Vendor/Documents
        """
        return await BaseDocumentView.post(self, vendor_id, body)

    async def get(self, vendor_id: str, /) -> r200[DocumentList]:
        """
        Get list of vendor documents

        Tags: Vendor/Documents
        """
        return await BaseDocumentView.get(self, vendor_id)


class VendorDocumentItemView(VendorDocumentMixin, BaseDocumentItemView, PydanticView):

    async def get(self, vendor_id: str, doc_id: str, /) -> Union[r200[DocumentResponse], r404[ErrorResponse]]:
        """
        Get vendor document

        Tags: Vendor/Documents
        """
        return await BaseDocumentItemView.get(self, vendor_id, doc_id)

    async def put(
        self, vendor_id: str, doc_id: str, /, body: DocumentPutInput,
    ) -> Union[r200[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Vendor document replace

        Security: Basic: []
        Tags: Vendor/Documents
        """
        return await BaseDocumentItemView.put(self, vendor_id, doc_id, body)

    async def patch(
        self, vendor_id: str, doc_id: str, /, body: DocumentPatchInput,
    ) -> Union[r200[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Vendor document update

        Security: Basic: []
        Tags: Vendor/Documents
        """
        return await BaseDocumentItemView.patch(self, vendor_id, doc_id, body)
