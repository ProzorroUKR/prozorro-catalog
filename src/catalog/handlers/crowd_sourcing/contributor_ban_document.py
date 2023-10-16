import random
from aiohttp.web_exceptions import HTTPNotFound
from aiohttp.web import HTTPConflict
from pymongo.errors import OperationFailure

from catalog import db
from catalog.models.document import DocumentPostInput, DocumentPutInput, DocumentPatchInput
from catalog.serializers.document import DocumentSerializer
from catalog.swagger import class_view_swagger_path
from catalog.handlers.base_document import BaseDocumentView
from catalog.utils import async_retry, get_now, find_item_by_id


@class_view_swagger_path('/app/swagger/crowd_sourcing/contributors/bans/documents')
class ContributorBanDocumentView(BaseDocumentView):

    @classmethod
    async def get_parent_obj(cls, **kwargs):
        contributor = await db.read_contributor(kwargs.get("contributor_id"))
        ban_id = kwargs.get("ban_id")
        return find_item_by_id(contributor.get("bans", []), ban_id, "ban")

    @classmethod
    async def collection_get(cls, request, **kwargs):
        return await super().collection_get(request, **kwargs)

    @classmethod
    async def get(cls, request, **kwargs):
        return await super().get(request, **kwargs)

    @classmethod
    async def post(cls, request, **kwargs):
        json = await request.json()
        body = DocumentPostInput(**json)
        data = body.data.dict_without_none()

        async with db.read_and_update_contributor(kwargs.get("contributor_id")) as obj:
            ban = find_item_by_id(obj.get("bans", []), kwargs.get("ban_id"), "ban")
            ban['dateModified'] = data['datePublished'] = data['dateModified'] = get_now().isoformat()
            if "documents" not in ban:
                ban["documents"] = []
            ban["documents"].append(data)

        return {"data": DocumentSerializer(data).data}

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def put(cls, request, **kwargs):
        async with db.read_and_update_contributor(kwargs.get("contributor_id")) as obj:
            # import and validate data
            json = await request.json()
            doc_id = kwargs.get("doc_id")
            json["data"]["id"] = doc_id
            body = DocumentPutInput(**json)
            # find & append doc
            ban = find_item_by_id(obj.get("bans", []), kwargs.get("ban_id"), "ban")
            for doc in ban.get("documents", "")[::-1]:
                if doc["id"] == doc_id:
                    data = body.data.dict_without_none()
                    data["id"] = doc_id
                    data["datePublished"] = doc["datePublished"]
                    ban["dateModified"] = data["dateModified"] = get_now().isoformat()
                    ban["documents"].append(data)
                    break
            else:
                raise HTTPNotFound(text="Document not found")
        return {"data": DocumentSerializer(data).data}

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def patch(cls, request, **kwargs):
        # validate_accreditation(request, "category")
        async with db.read_and_update_contributor(kwargs.get("contributor_id")) as obj:
            doc_id = kwargs.get("doc_id")
            # import and validate data
            json = await request.json()
            body = DocumentPatchInput(**json)
            # export data back to dict
            data = body.data.dict_without_none()
            # find & update doc
            ban = find_item_by_id(obj.get("bans", []), kwargs.get("ban_id"), "ban")
            for doc in ban.get("documents", "")[::-1]:
                if doc["id"] == doc_id:
                    initial = dict(doc)
                    doc.update(data)
                    if initial != doc:
                        ban['dateModified'] = doc['dateModified'] = get_now().isoformat()
                    break
            else:
                raise HTTPNotFound(text="Document not found")
        return {"data": DocumentSerializer(doc).data}
