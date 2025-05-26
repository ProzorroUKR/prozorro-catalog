import random
import logging

from aiohttp_pydantic import PydanticView
from aiohttp.web import HTTPConflict, HTTPFound, HTTPNotFound
from pymongo.errors import OperationFailure
from catalog.utils import get_now, async_retry
from catalog.models.document import DocumentPostInput, DocumentPutInput, DocumentPatchInput
from catalog.serializers.document import DocumentSerializer
from catalog.doc_service import get_doc_download_url, get_ds_id_from_api_url


logger = logging.getLogger(__name__)


class BaseDocumentMixin:
    parent_obj_name = None

    @classmethod
    async def get_parent_obj(cls, parent_obj_id):
        pass

    @classmethod
    def read_and_update_object(cls, parent_obj_id):
        pass

    @classmethod
    async def validate_data(cls, request, body, parent_obj, parent_obj_id):
        pass


class BaseDocumentView(BaseDocumentMixin):

    async def get(self, parent_obj_id: str):
        obj = await self.get_parent_obj(parent_obj_id)
        return {"data": [DocumentSerializer(d).data for d in obj.get("documents", "")]}

    async def post(self, parent_obj_id: str, body: DocumentPostInput):

        data = body.data.dict_without_none()

        async with self.read_and_update_object(parent_obj_id) as obj:
            await self.validate_data(self.request, body, obj, parent_obj_id)
            obj['dateModified'] = data['datePublished'] = data['dateModified'] = get_now().isoformat()
            if "documents" not in obj:
                obj["documents"] = []
            obj["documents"].append(data)

            logger.info(
                f"Created {self.parent_obj_name} document {data['id']}",
                extra={
                    "MESSAGE_ID": f"{self.parent_obj_name}_document_create",
                    "document_id": data["id"]
                },
            )

        return {"data": DocumentSerializer(data).data}


class BaseDocumentItemView(BaseDocumentMixin):

    async def get(self, parent_obj_id: str, doc_id: str):
        obj = await self.get_parent_obj(parent_obj_id)
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

    async def put(self, parent_obj_id: str, doc_id: str, body: DocumentPutInput):
        # validate_accreditation(request, "category")
        async with self.read_and_update_object(parent_obj_id) as obj:
            # import and validate data
            json = await self.request.json()
            json["data"]["id"] = doc_id
            body = DocumentPutInput(**json)
            await self.validate_data(self.request, body, obj, parent_obj_id)
            # find & append doc
            for d in obj.get("documents", "")[::-1]:
                if d["id"] == doc_id:
                    data = body.data.dict_without_none()
                    data["id"] = doc_id
                    obj["dateModified"] = data["datePublished"] = data["dateModified"] = get_now().isoformat()
                    obj["documents"].append(data)
                    break
            else:
                raise HTTPNotFound(text="Document not found")

            logger.info(
                f"Updated {self.parent_obj_name} document {doc_id}",
                extra={"MESSAGE_ID": f"{self.parent_obj_name}_document_put"},
            )
        return {"data": DocumentSerializer(data).data}

    async def patch(self, parent_obj_id: str, doc_id: str, body: DocumentPatchInput):
        # validate_accreditation(request, "category")
        async with self.read_and_update_object(parent_obj_id) as obj:
            await self.validate_data(self.request, body, obj, parent_obj_id)
            # export data back to dict
            data = body.data.dict_without_none()
            # find & update doc
            for d in obj.get("documents", "")[::-1]:
                if d["id"] == doc_id:
                    initial = dict(d)
                    d.update(data)
                    if initial != d:
                        obj['dateModified'] = d['dateModified'] = get_now().isoformat()
                    break
            else:
                raise HTTPNotFound(text="Document not found")

            logger.info(
                f"Updated {self.parent_obj_name} document {doc_id}",
                extra={"MESSAGE_ID": f"{self.parent_obj_name}_document_patch"},
            )
        return {"data": DocumentSerializer(d).data}
