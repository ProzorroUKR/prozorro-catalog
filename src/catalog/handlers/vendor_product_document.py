from typing import Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401

from catalog import db
from catalog.handlers.base_document import BaseDocumentView, BaseDocumentItemView
from catalog.auth import validate_access_token
from catalog.models.api import ErrorResponse
from catalog.models.document import DocumentResponse, DocumentPatchInput, DocumentPutInput, DocumentPostInput, \
    DocumentList


class VendorProductDocumentMixin:
    parent_obj_name = "vendor_product"
    @classmethod
    async def get_parent_obj(cls, vendor_id, product_id):
        return await db.read_product(product_id, {"vendor.id": vendor_id})

    @classmethod
    def read_and_update_object(cls, vendor_id, product_id):
        return db.read_and_update_product(product_id, {"vendor.id": vendor_id})

    @classmethod
    async def validate_data(cls, request, body, parent_obj, vendor_id):
        vendor = await db.read_vendor(vendor_id)
        validate_access_token(request, vendor, body.access)


class VendorProductDocumentView(VendorProductDocumentMixin, BaseDocumentView, PydanticView):
    async def post(
        self, vendor_id: str, product_id: str, /, body: DocumentPostInput
    ) -> Union[r201[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Vendor product document create

        Security: Basic: []
        Tags: Vendor/Product/Documents
        """
        return await BaseDocumentView.post(self, vendor_id, body, product_id)

    async def get(self, vendor_id: str, product_id: str, /) -> r200[DocumentList]:
        """
        Get list of vendor product documents

        Tags: Vendor/Product/Documents
        """
        return await BaseDocumentView.get(self, vendor_id, product_id)


class VendorProductDocumentItemView(VendorProductDocumentMixin, BaseDocumentItemView, PydanticView):

    async def get(self, vendor_id: str, product_id: str, doc_id: str, /) -> Union[r200[DocumentResponse], r404[ErrorResponse]]:
        """
        Get vendor product document

        Tags: Vendor/Product/Documents
        """
        return await BaseDocumentItemView.get(self, vendor_id, doc_id, product_id)

    async def put(
        self, vendor_id: str, product_id: str, doc_id: str, /, body: DocumentPutInput,
    ) -> Union[r200[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Vendor product document replace

        Security: Basic: []
        Tags: Vendor/Product/Documents
        """
        return await BaseDocumentItemView.put(self, vendor_id, doc_id, body, product_id)

    async def patch(
        self, vendor_id: str, product_id: str, doc_id: str, /, body: DocumentPatchInput,
    ) -> Union[r200[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Vendor product document update

        Security: Basic: []
        Tags: Vendor/Product/Documents
        """
        return await BaseDocumentItemView.patch(self, vendor_id, doc_id, body, product_id)

