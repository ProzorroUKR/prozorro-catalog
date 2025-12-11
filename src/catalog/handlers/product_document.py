from typing import Union

from aiohttp.web import HTTPForbidden
from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401

from catalog import db
from catalog.models.api import ErrorResponse
from catalog.models.document import DocumentPostInput, DocumentPutInput, DocumentPatchInput, DocumentList, \
    DocumentResponse
from catalog.handlers.base_document import BaseDocumentView, BaseDocumentItemView
from catalog.auth import validate_access_token, validate_accreditation
from catalog.settings import LOCALIZATION_CRITERIA


class ProductDocumentMixin:
    @classmethod
    async def get_parent_obj(cls, parent_obj_id, child_obj_id=None):
        return await db.read_product(parent_obj_id)

    @classmethod
    def read_and_update_object(cls, parent_obj_id, child_obj_id=None):
        return db.read_and_update_product(parent_obj_id)

    @classmethod
    async def validate_data(cls, request, body, parent_obj, parent_obj_id):
        category = await db.read_category(parent_obj["relatedCategory"])
        localization_criteria = [
            cr for cr in category['criteria'] if cr.get("classification", {}).get("id") == LOCALIZATION_CRITERIA
        ]
        if parent_obj.get("vendor") is None and not localization_criteria:
            raise HTTPForbidden(text='Forbidden to add document for non-localized product')
        validate_access_token(request, parent_obj, body.access)


class ProductDocumentView(ProductDocumentMixin, BaseDocumentView, PydanticView):
    async def post(
        self, product_id: str, /, body: DocumentPostInput
    ) -> Union[r201[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Product document create

        Security: Basic: []
        Tags: Products/Documents
        """
        validate_accreditation(self.request, "product")
        return await BaseDocumentView.post(self, product_id, body)

    async def get(self, product_id: str, /) -> r200[DocumentList]:
        """
        Get list of product documents

        Tags: Products/Documents
        """
        return await BaseDocumentView.get(self, product_id)


class ProductDocumentItemView(ProductDocumentMixin, BaseDocumentItemView, PydanticView):

    async def get(self, product_id: str, doc_id: str, /) -> Union[r200[DocumentResponse], r404[ErrorResponse]]:
        """
        Get product document

        Tags: Products/Documents
        """
        return await BaseDocumentItemView.get(self, product_id, doc_id)

    async def put(
        self, product_id: str, doc_id: str, /, body: DocumentPutInput,
    ) -> Union[r200[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Product document replace

        Security: Basic: []
        Tags: Products/Documents
        """
        validate_accreditation(self.request, "product")
        return await BaseDocumentItemView.put(self, product_id, doc_id, body)

    async def patch(
        self, product_id: str, doc_id: str, /, body: DocumentPatchInput,
    ) -> Union[r200[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Product document update

        Security: Basic: []
        Tags: Products/Documents
        """
        validate_accreditation(self.request, "product")
        return await BaseDocumentItemView.patch(self, product_id, doc_id, body)

