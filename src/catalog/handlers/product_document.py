import random
from aiohttp.web import HTTPConflict, HTTPForbidden
from pymongo.errors import OperationFailure

from catalog import db
from catalog.swagger import class_view_swagger_path
from catalog.handlers.base_document import BaseDocumentView
from catalog.utils import async_retry
from catalog.auth import validate_access_token, validate_accreditation


@class_view_swagger_path('/app/swagger/products/documents')
class ProductDocumentView(BaseDocumentView):

    @classmethod
    async def get_parent_obj(cls, **kwargs):
        return await db.read_product(kwargs.get("product_id"))

    @classmethod
    def read_and_update_object(cls, **kwargs):
        return db.read_and_update_product(kwargs.get("product_id"))

    @classmethod
    async def validate_data(cls, request, body, parent_obj, **kwargs):
        if parent_obj.get("vendor") is None:
            raise HTTPForbidden(text='Forbidden to add document for non-localized product')
        validate_access_token(request, parent_obj, body.access)

    # redefined post, patch, put, get methods of parent view
    # because Swagger connects all documents endpoints in other case
    @classmethod
    async def post(cls, request, **kwargs):
        validate_accreditation(request, "product")
        return await super().post(request, **kwargs)

    @classmethod
    async def collection_get(cls, request, **kwargs):
        return await super().collection_get(request, **kwargs)

    @classmethod
    async def get(cls, request, **kwargs):
        return await super().get(request, **kwargs)

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def put(cls, request, **kwargs):
        validate_accreditation(request, "product")
        return await super().put(request, **kwargs)

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def patch(cls, request, **kwargs):
        validate_accreditation(request, "product")
        return await super().patch(request, **kwargs)

