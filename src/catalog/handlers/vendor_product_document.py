from catalog import db
from catalog.swagger import class_view_swagger_path
from catalog.handlers.base_document import BaseDocumentView
from catalog.auth import validate_access_token


@class_view_swagger_path('/app/swagger/vendors/products/documents')
class VendorProductDocumentView(BaseDocumentView):

    @classmethod
    async def get_parent_obj(cls, **kwargs):
        return await db.read_product(kwargs.get("product_id"), {"vendor.id": kwargs.get("vendor_id")})

    @classmethod
    def read_and_update_object(cls, **kwargs):
        return db.read_and_update_product(kwargs.get("product_id"),  {"vendor.id": kwargs.get("vendor_id")})

    @classmethod
    async def validate_data(cls, request, body, parent_obj, **kwargs):
        vendor = await db.read_vendor(kwargs.get("vendor_id"))
        validate_access_token(request, vendor, body.access)
