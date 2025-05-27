from typing import Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401

from catalog.auth import validate_accreditation
from catalog.models.api import ErrorResponse
from catalog.models.document import (
    DocumentResponse,
    DocumentPutInput,
    DocumentPatchInput,
    DocumentList,
    DocumentPostInput,
)
from catalog import db
from catalog.handlers.base_document import BaseDocumentView, BaseDocumentItemView


class ContributorDocumentMixin:

    parent_obj_name = "contributor"

    @classmethod
    async def get_parent_obj(cls, contributor_id, child_obj_id=None):
        return await db.read_contributor(contributor_id)

    @classmethod
    def read_and_update_object(cls, contributor_id, child_obj_id=None):
        return db.read_and_update_contributor(contributor_id)


class ContributorDocumentView(ContributorDocumentMixin, BaseDocumentView, PydanticView):

    async def post(
        self, contributor_id: str, /, body: DocumentPostInput
    ) -> Union[r201[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Contributor document create

        Security: Basic: []
        Tags: Contributor/Documents
        """
        validate_accreditation(self.request, "contributors")
        return await BaseDocumentView.post(self, contributor_id, body)

    async def get(self, contributor_id: str, /) -> r200[DocumentList]:
        """
        Get list of contributor documents

        Tags: Contributor/Documents
        """
        return await BaseDocumentView.get(self, contributor_id)


class ContributorDocumentItemView(ContributorDocumentMixin, BaseDocumentItemView, PydanticView):

    async def get(self, contributor_id: str, doc_id: str, /) -> Union[r200[DocumentResponse], r404[ErrorResponse]]:
        """
        Get contributor document

        Tags: Contributor/Documents
        """
        return await BaseDocumentItemView.get(self, contributor_id, doc_id)

    async def put(
        self, contributor_id: str, doc_id: str, /, body: DocumentPutInput,
    ) -> Union[r200[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Contributor document replace

        Security: Basic: []
        Tags: Contributor/Documents
        """
        validate_accreditation(self.request, "contributors")
        return await BaseDocumentItemView.put(self, contributor_id, doc_id, body)

    async def patch(
            self, contributor_id: str, doc_id: str, /, body: DocumentPatchInput,
    ) -> Union[r200[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Contributor document update

        Security: Basic: []
        Tags: Contributor/Documents
        """
        validate_accreditation(self.request, "contributors")
        return await BaseDocumentItemView.patch(self, contributor_id, doc_id, body)
