import random
from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPConflict, HTTPFound, HTTPNotFound
from pymongo.errors import OperationFailure
from catalog.utils import get_now, async_retry
from catalog.models.document import DocumentPostInput, DocumentPatchInput
from catalog.serializers.document import DocumentSerializer
from catalog.doc_service import get_doc_download_url


class BaseDocumentView(View):

    @classmethod
    async def get_parent_obj(cls, **kwargs):
        pass

    @classmethod
    def read_and_update_object(cls, **kwargs):
        pass

    @classmethod
    async def validate_data(cls, request, body, parent_obj, **kwargs):
       pass

    @classmethod
    async def collection_get(cls, request, **kwargs):
        obj = await cls.get_parent_obj(**kwargs)
        return {"data": [DocumentSerializer(d).data for d in obj.get("documents", "")]}

    @classmethod
    async def get(cls, request, **kwargs):
        obj = await cls.get_parent_obj(**kwargs)
        doc_id = kwargs.get("doc_id")
        for d in obj.get("documents", "")[::-1]:
            if d["id"] == doc_id:
                if request.query.get("download"):
                    redirect_url = get_doc_download_url(d)
                    raise HTTPFound(location=redirect_url)
                return {"data": DocumentSerializer(d).data}
        else:
            raise HTTPNotFound(text="Document not found")

    @classmethod
    async def post(cls, request, **kwargs):

        json = await request.json()
        body = DocumentPostInput(**json)
        data = body.data.dict_without_none()

        async with cls.read_and_update_object(**kwargs) as obj:
            await cls.validate_data(request, body, obj, **kwargs)
            obj['dateModified'] = data['datePublished'] = data['dateModified'] = get_now().isoformat()
            if "documents" not in obj:
                obj["documents"] = []
            obj["documents"].append(data)

        return {"data": DocumentSerializer(data).data}

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def put(cls, request, **kwargs):
        # validate_accreditation(request, "category")
        async with cls.read_and_update_object(**kwargs) as obj:
            # import and validate data
            json = await request.json()
            body = DocumentPostInput(**json)
            doc_id = kwargs.get("doc_id")
            await cls.validate_data(request, body, obj, **kwargs)
            # find & append doc
            for d in obj.get("documents", "")[::-1]:
                if d["id"] == doc_id:
                    data = body.data.dict_without_none()
                    data["id"] = doc_id
                    data["datePublished"] = d["datePublished"]
                    obj['dateModified'] = data['dateModified'] = get_now().isoformat()
                    obj["documents"].append(data)
                    break
            else:
                raise HTTPNotFound(text="Document not found")
        return {"data": DocumentSerializer(data).data}

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def patch(cls, request, **kwargs):
        # validate_accreditation(request, "category")
        async with cls.read_and_update_object(**kwargs) as obj:
            doc_id = kwargs.get("doc_id")
            # import and validate data
            json = await request.json()
            body = DocumentPatchInput(**json)
            await cls.validate_data(request, body, obj, **kwargs)
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
        return {"data": DocumentSerializer(d).data}
