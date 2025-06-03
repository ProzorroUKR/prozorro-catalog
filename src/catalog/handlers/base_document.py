import logging
from typing import Optional
from copy import deepcopy

from aiohttp.web import HTTPFound, HTTPNotFound
from catalog.utils import get_now, get_revision_changes
from catalog.models.document import DocumentPostInput, DocumentPutInput, DocumentPatchInput
from catalog.serializers.document import DocumentSerializer
from catalog.doc_service import get_doc_download_url, get_ds_id_from_api_url


logger = logging.getLogger(__name__)


class BaseDocumentMixin:
    parent_obj_name = None

    @classmethod
    async def get_parent_obj(cls, parent_obj_id, child_obj_id=None):
        pass

    @classmethod
    def read_and_update_object(cls, parent_obj_id, child_obj_id=None):
        pass

    @classmethod
    async def validate_data(cls, request, body, parent_obj, parent_obj_id):
        pass


class BaseDocumentView(BaseDocumentMixin):

    async def get(self, parent_obj_id: str, child_obj_id: Optional[str] = None):
        obj = await self.get_parent_obj(parent_obj_id, child_obj_id)
        return {"data": [DocumentSerializer(d).data for d in obj.get("documents", "")]}

    async def post(self, parent_obj_id: str, body: DocumentPostInput, child_obj_id: Optional[str] = None):

        data = body.data.dict_without_none()

        async with self.read_and_update_object(parent_obj_id, child_obj_id) as parent_obj:
            old_parent_obj = deepcopy(parent_obj)
            await self.validate_data(self.request, body, parent_obj, parent_obj_id)
            parent_obj['dateModified'] = data['datePublished'] = data['dateModified'] = get_now().isoformat()
            if "documents" not in parent_obj:
                parent_obj["documents"] = []
            parent_obj["documents"].append(data)
            get_revision_changes(self.request, new_obj=parent_obj, old_obj=old_parent_obj)

            logger.info(
                f"Created {self.parent_obj_name} document {data['id']}",
                extra={
                    "MESSAGE_ID": f"{self.parent_obj_name}_document_create",
                    "document_id": data["id"]
                },
            )

        return {"data": DocumentSerializer(data).data}


class BaseDocumentItemView(BaseDocumentMixin):

    async def get(self, parent_obj_id: str, doc_id: str, child_obj_id: Optional[str] = None):
        obj = await self.get_parent_obj(parent_obj_id, child_obj_id)
        request_ds_id = self.request.query.get("download")
        for d in obj.get("documents", "")[::-1]:
            if d["id"] == doc_id:
                if request_ds_id:
                    ds_id = get_ds_id_from_api_url(d)
                    if ds_id == request_ds_id:
                        redirect_url = get_doc_download_url(ds_id)
                        raise HTTPFound(location=redirect_url)
                else:
                    return {"data": DocumentSerializer(d).data}
        else:
            raise HTTPNotFound(text="Document not found")

    async def put(self, parent_obj_id: str, doc_id: str, body: DocumentPutInput, child_obj_id: Optional[str] = None):
        # validate_accreditation(request, "category")
        async with self.read_and_update_object(parent_obj_id, child_obj_id) as parent_obj:
            old_parent_obj = deepcopy(parent_obj)
            # import and validate data
            json = await self.request.json()
            json["data"]["id"] = doc_id
            body = DocumentPutInput(**json)
            await self.validate_data(self.request, body, parent_obj, parent_obj_id)
            # find & append doc
            for d in parent_obj.get("documents", "")[::-1]:
                if d["id"] == doc_id:
                    data = body.data.dict_without_none()
                    data["id"] = doc_id
                    parent_obj["dateModified"] = data["datePublished"] = data["dateModified"] = get_now().isoformat()
                    parent_obj["documents"].append(data)
                    break
            else:
                raise HTTPNotFound(text="Document not found")
            get_revision_changes(self.request, new_obj=parent_obj, old_obj=old_parent_obj)

            logger.info(
                f"Updated {self.parent_obj_name} document {doc_id}",
                extra={"MESSAGE_ID": f"{self.parent_obj_name}_document_put"},
            )
        return {"data": DocumentSerializer(data).data}

    async def patch(self, parent_obj_id: str, doc_id: str, body: DocumentPatchInput, child_obj_id: Optional[str] = None):
        # validate_accreditation(request, "category")
        async with self.read_and_update_object(parent_obj_id, child_obj_id) as parent_obj:
            await self.validate_data(self.request, body, parent_obj, parent_obj_id)
            old_parent_obj = deepcopy(parent_obj)
            # export data back to dict
            data = body.data.dict_without_none()
            # find & update doc
            for d in parent_obj.get("documents", "")[::-1]:
                if d["id"] == doc_id:
                    initial = dict(d)
                    d.update(data)
                    if initial != d:
                        parent_obj['dateModified'] = d['dateModified'] = get_now().isoformat()
                    break
            else:
                raise HTTPNotFound(text="Document not found")
            get_revision_changes(self.request, new_obj=parent_obj, old_obj=old_parent_obj)

            logger.info(
                f"Updated {self.parent_obj_name} document {doc_id}",
                extra={"MESSAGE_ID": f"{self.parent_obj_name}_document_patch"},
            )
        return {"data": DocumentSerializer(d).data}
