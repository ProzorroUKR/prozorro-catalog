import random
from aiohttp.web_urldispatcher import View
from aiohttp.web import HTTPConflict, HTTPFound, HTTPNotFound
from pymongo.errors import OperationFailure
from catalog import db
from catalog.swagger import class_view_swagger_path
from catalog.auth import validate_access_token
from catalog.utils import get_now, async_retry
from catalog.models.document import DocumentPostInput, DocumentPatchInput
from catalog.serializers.document import DocumentSerializer
from catalog.doc_service import get_doc_download_url


@class_view_swagger_path('/app/swagger/vendors/products/documents')
class VendorProductDocumentView(View):

    @classmethod
    async def collection_get(cls, request, vendor_id, product_id):
        obj = await db.read_product(product_id, {"vendor.id": vendor_id})
        return {"data": [DocumentSerializer(d).data for d in obj.get("documents", "")]}

    @classmethod
    async def get(cls, request, vendor_id, product_id, doc_id):
        obj = await db.read_product(product_id, {"vendor.id": vendor_id})
        for d in obj.get("documents", ""):
            if d["id"] == doc_id:
                if request.query.get("download"):
                    redirect_url = get_doc_download_url(d)
                    raise HTTPFound(location=redirect_url)
                return {"data": DocumentSerializer(d).data}
        else:
            raise HTTPNotFound(text="Document not found")

    @classmethod
    async def post(cls, request, vendor_id, product_id):

        json = await request.json()
        body = DocumentPostInput(**json)
        data = body.data.dict_without_none()
        data['datePublished'] = data['dateModified'] = get_now().isoformat()
        vendor = await db.read_vendor(vendor_id)
        validate_access_token(request, vendor, body.access)

        async with db.read_and_update_product(product_id,  {"vendor.id": vendor_id}) as product:
            if "documents" not in product:
                product["documents"] = []
            product["documents"].append(data)

        return {"data": DocumentSerializer(data).data}

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def put(cls, request, vendor_id, product_id, doc_id):
        # validate_accreditation(request, "category")
        async with db.read_and_update_product(product_id, {"vendor.id": vendor_id}) as product:
            # import and validate data
            json = await request.json()
            body = DocumentPostInput(**json)
            vendor = await db.read_vendor(vendor_id)
            validate_access_token(request, vendor, body.access)
            # find & append doc
            for d in product.get("documents", ""):
                if d["id"] == doc_id:
                    data = body.data.dict_without_none()
                    data["id"] = doc_id
                    data['datePublished'] = data['dateModified'] = get_now().isoformat()
                    product["documents"].append(data)
                    break
            else:
                raise HTTPNotFound(text="Document not found")
        return {"data": DocumentSerializer(d).data}

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def patch(cls, request, vendor_id, product_id, doc_id):
        # validate_accreditation(request, "category")
        async with db.read_and_update_product(product_id, {"vendor.id": vendor_id}) as product:
            # import and validate data
            json = await request.json()
            body = DocumentPatchInput(**json)
            vendor = await db.read_vendor(vendor_id)
            validate_access_token(request, vendor, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            # find & update doc
            for d in product.get("documents", ""):
                if d["id"] == doc_id:
                    initial = dict(d)
                    d.update(data)
                    if initial != d:
                        data['dateModified'] = get_now().isoformat()
                    break
            else:
                raise HTTPNotFound(text="Document not found")
        return {"data": DocumentSerializer(d).data}
