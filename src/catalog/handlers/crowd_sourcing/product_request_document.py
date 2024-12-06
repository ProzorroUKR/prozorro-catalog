import random
from aiohttp.web import HTTPConflict
from pymongo.errors import OperationFailure

from catalog.auth import validate_accreditation
from catalog.utils import async_retry
from catalog import db
from catalog.swagger import class_view_swagger_path
from catalog.handlers.base_document import BaseDocumentView


# @class_view_swagger_path('/app/swagger/crowd_sourcing/product_requests/documents')
class ProductRequestDocumentView(BaseDocumentView):

    parent_obj_name = "product_request"

    @classmethod
    async def get_parent_obj(cls, **kwargs):
        return await db.read_product_request(kwargs.get("request_id"))

    @classmethod
    def read_and_update_object(cls, **kwargs):
        return db.read_and_update_product_request(kwargs.get("request_id"))

    @classmethod
    async def post(cls, request, **kwargs):
        validate_accreditation(request, "contributors")
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
        validate_accreditation(request, "contributors")
        return await super().put(request, **kwargs)

    @classmethod
    @async_retry(tries=3, exceptions=OperationFailure, delay=lambda: random.uniform(0, .5),
                 fail_exception=HTTPConflict(text="Try again later"))
    async def patch(cls, request, **kwargs):
        validate_accreditation(request, "contributors")
        return await super().patch(request, **kwargs)
