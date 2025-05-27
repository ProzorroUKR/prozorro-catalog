from typing import Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401

from catalog.auth import validate_accreditation
from catalog.models.api import ErrorResponse
from catalog.models.document import (
    DocumentResponse,
    DocumentPutInput,
    DocumentPatchInput,
    DocumentPostInput,
    DocumentList,
)
from catalog import db
from catalog.handlers.base_document import BaseDocumentView, BaseDocumentItemView


class ProductRequestDocumentMixin:
    parent_obj_name = "product_request"

    @classmethod
    async def get_parent_obj(cls, request_id, child_obj_id=None):
        return await db.read_product_request(request_id)

    @classmethod
    def read_and_update_object(cls, request_id, child_obj_id=None):
        return db.read_and_update_product_request(request_id)


class ProductRequestDocumentView(ProductRequestDocumentMixin, PydanticView):

    async def post(
        self, request_id: str, /, body: DocumentPostInput
    ) -> Union[r201[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Product request document create

        Security: Basic: []
        Tags: Contributor/ProductRequest/Documents
        """
        validate_accreditation(self.request, "contributors")
        return await BaseDocumentView.post(self, request_id, body)

    async def get(self, request_id: str, /) -> r200[DocumentList]:
        """
        Get list of product request documents

        Tags: Contributor/ProductRequest/Documents
        """
        return await BaseDocumentView.get(self, request_id)


class ProductRequestDocumentItemView(ProductRequestDocumentMixin, BaseDocumentItemView, PydanticView):

    async def get(self, request_id: str, doc_id: str, /) -> Union[r200[DocumentResponse], r404[ErrorResponse]]:
        """
        Get product request document

        Tags: Contributor/ProductRequest/Documents
        """
        return await BaseDocumentItemView.get(self, request_id, doc_id)

    async def put(
        self, request_id: str, doc_id: str, /, body: DocumentPutInput,
    ) -> Union[r200[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Product request document replace

        Security: Basic: []
        Tags: Contributor/ProductRequest/Documents
        """
        validate_accreditation(self.request, "contributors")
        return await BaseDocumentItemView.put(self, request_id, doc_id, body)

    async def patch(
        self, request_id: str, doc_id: str, /, body: DocumentPatchInput,
    ) -> Union[r200[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Product request document update

        Security: Basic: []
        Tags: Contributor/ProductRequest/Documents
        """
        validate_accreditation(self.request, "contributors")
        return await BaseDocumentItemView.patch(self, request_id, doc_id, body)
