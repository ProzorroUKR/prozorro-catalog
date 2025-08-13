from copy import deepcopy
import logging
from typing import Optional, Union

from aiohttp_pydantic import PydanticView
from aiohttp_pydantic.oas.typing import r200, r201, r204, r404, r400, r401
from aiohttp.web import HTTPNotFound

from catalog import db
from catalog.context import get_final_session_time
from catalog.models.api import PaginatedList, ErrorResponse
from catalog.models.product import ProductCreateInput, ProductUpdateInput, LocalizationProductUpdateInput, \
    ProductCreateResponse, ProductResponse
from catalog.utils import pagination_params, get_now, get_revision_changes
from catalog.auth import validate_access_token, validate_accreditation, set_access_token
from catalog.serializers.product import ProductSerializer
from catalog.state.product import ProductState


logger = logging.getLogger(__name__)


class ProductView(PydanticView):

    state_class = ProductState

    async def get(
            self, /, offset: Optional[str] = None, limit: Optional[int] = 100, descending: Optional[Union[int, str]] = 0,
    ) -> r200[PaginatedList]:
        """
        Get a list of products

        Tags: Products
        """
        offset, limit, reverse = pagination_params(self.request)
        response = await db.find_products(
            offset=offset,
            limit=limit,
            reverse=reverse,
        )
        return response

    async def post(
        self, /, body: ProductCreateInput
    ) -> Union[r201[ProductCreateResponse], r400[ErrorResponse], r401[ErrorResponse]]:
        """
        Create product

        Security: Basic: []
        Tags: Products
        """
        validate_accreditation(self.request, "product")
        # export data back to dict
        data = body.data.dict_without_none()

        category_id = data["relatedCategory"]
        category = await db.read_category(category_id)  # ensure exists
        validate_access_token(self.request, category, body.access)

        await self.state_class.on_post(data, category)

        access = set_access_token(self.request, data)
        data["dateCreated"] = data["dateModified"] = get_now().isoformat()
        get_revision_changes(self.request, new_obj=data)
        await db.insert_product(data)

        logger.info(
            f"Created product {data['id']}",
            extra={
                "MESSAGE_ID": "product_create",
                "product_id": data["id"],
                "session": get_final_session_time(),
            },
        )
        return {"data": ProductSerializer(data, category=category).data,
                "access": access}


class ProductItemView(PydanticView):

    state_class = ProductState

    async def get(self, product_id: str, /) -> Union[r201[ProductResponse], r400[ErrorResponse], r404[ErrorResponse]]:
        """
        Get product

        Tags: Products
        """
        product = await db.read_product(product_id)
        category = await db.read_category(
            category_id=product.get("relatedCategory"),
            projection={"criteria": 1},
        )

        vendor = None
        if "vendor" in product:
            try:
                vendor = await db.read_vendor(product["vendor"]["id"])
            except HTTPNotFound:
                pass

        return {"data": ProductSerializer(product, vendor=vendor, category=category).data}

    async def patch(
        self, product_id: str, /, body: ProductUpdateInput
    ) -> Union[r200[ProductResponse], r400[ErrorResponse], r401[ErrorResponse], r404[ErrorResponse]]:
        """
        Product update

        Security: Basic: []
        Tags: Products
        """
        validate_accreditation(self.request, "product")
        async with db.read_and_update_product(product_id) as product:
            # import and validate data
            json = await self.request.json()
            if product.get("vendor"):
                body = LocalizationProductUpdateInput(**json)
            else:
                body = ProductUpdateInput(**json)
            validate_access_token(self.request, product, body.access)
            # export data back to dict
            data = body.data.dict_without_none()
            product_before = deepcopy(product)
            product.update(data)
            category = await db.read_category(product["relatedCategory"])
            await self.state_class.on_patch(product_before, product)
            get_revision_changes(self.request, new_obj=product, old_obj=product_before)

            logger.info(
                f"Updated product {product_id}",
                extra={"MESSAGE_ID": "product_patch", "session": get_final_session_time()},
            )

        return {"data": ProductSerializer(product, category=category).data}
