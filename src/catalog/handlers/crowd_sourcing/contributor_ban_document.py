from copy import deepcopy
from typing import Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401
from aiohttp.web_exceptions import HTTPNotFound

from catalog import db
from catalog.auth import validate_accreditation
from catalog.models.api import ErrorResponse
from catalog.models.document import DocumentPostInput, DocumentPutInput, DocumentPatchInput, DocumentResponse, \
    DocumentList
from catalog.serializers.document import DocumentSerializer
from catalog.handlers.base_document import BaseDocumentView, BaseDocumentItemView
from catalog.utils import get_now, find_item_by_id, get_revision_changes


class ContributorBanDocumentMixin:
    parent_obj_name = "contributor_ban"

    @classmethod
    async def get_parent_obj(cls, contributor_id, ban_id):
        contributor = await db.read_contributor(contributor_id)
        return find_item_by_id(contributor.get("bans", []), ban_id, "ban")


class ContributorBanDocumentView(ContributorBanDocumentMixin, BaseDocumentView, PydanticView):

    async def get(self, contributor_id: str, ban_id: str, /) -> r200[DocumentList]:
        """
        Get list of contributor ban documents

        Tags: Contributor/Bans/Documents
        """
        return await BaseDocumentView.get(self, contributor_id, ban_id)

    async def post(
            self, contributor_id: str, ban_id: str, /, body: DocumentPostInput
    ) -> Union[r201[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Contributor ban document create

        Security: Basic: []
        Tags: Contributor/Bans/Documents
        """
        validate_accreditation(self.request, "category")
        data = body.data.dict_without_none()

        async with db.read_and_update_contributor(contributor_id) as parent_obj:
            old_parent_obj = deepcopy(parent_obj)
            ban = find_item_by_id(parent_obj.get("bans", []), ban_id, "ban")
            now = get_now().isoformat()
            parent_obj["dateModified"] = ban['dateModified'] = data['datePublished'] = data['dateModified'] = now
            if "documents" not in ban:
                ban["documents"] = []
            ban["documents"].append(data)
            get_revision_changes(self.request, new_obj=parent_obj, old_obj=old_parent_obj)

        return {"data": DocumentSerializer(data).data}


class ContributorBanDocumentItemView(ContributorBanDocumentMixin, BaseDocumentItemView, PydanticView):

    async def get(
        self, contributor_id: str, ban_id: str, doc_id: str, /,
    ) -> Union[r200[DocumentResponse], r404[ErrorResponse]]:
        """
        Get contributor ban document

        Tags: Contributor/Bans/Documents
        """
        return await BaseDocumentItemView.get(self, contributor_id, doc_id, ban_id)

    async def put(
        self, contributor_id: str, ban_id: str, doc_id: str, /, body: DocumentPutInput,
    ) -> Union[r200[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Contributor ban document replace

        Security: Basic: []
        Tags: Contributor/Bans/Documents
        """
        validate_accreditation(self.request, "category")
        async with db.read_and_update_contributor(contributor_id) as parent_obj:
            old_parent_obj = deepcopy(parent_obj)
            # import and validate data
            json = await self.request.json()
            json["data"]["id"] = doc_id
            body = DocumentPutInput(**json)
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
        return {"data": DocumentSerializer(data).data}

    async def patch(
        self, contributor_id: str, ban_id: str, doc_id: str, /, body: DocumentPatchInput,
    ) -> Union[r200[DocumentResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Product contributor ban update

        Security: Basic: []
        Tags: Contributor/Bans/Documents
        """
        validate_accreditation(self.request, "category")
        async with db.read_and_update_contributor(contributor_id) as parent_obj:
            old_parent_obj = deepcopy(parent_obj)
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
        return {"data": DocumentSerializer(doc).data}
