from aiohttp import web
# from aiohttp_swagger import setup_swagger as aiohttp_setup_swagger
from aiohttp_pydantic import oas
from catalog import version
from catalog.handlers.crowd_sourcing.contributor import ContributorView
from catalog.handlers.crowd_sourcing.contributor_ban import ContributorBanView
from catalog.handlers.crowd_sourcing.contributor_ban_document import ContributorBanDocumentView
from catalog.handlers.crowd_sourcing.contributor_document import ContributorDocumentView
from catalog.handlers.crowd_sourcing.product_request import (
    ProductRequestView,
    ContributorProductRequestView,
    ProductRequestAcceptionView,
    ProductRequestRejectionView,
)
from catalog.handlers.crowd_sourcing.product_request_document import ProductRequestDocumentView
from catalog.handlers.vendor_ban import VendorBanView
from catalog.handlers.vendor_ban_document import VendorBanDocumentView
from catalog.settings import SWAGGER_DOC_AVAILABLE
from catalog.swagger import get_definitions
from catalog.middleware import (
    convert_response_to_json,
    error_middleware,
    request_id_middleware,
    login_middleware,
    context_middleware,
)
from catalog.db import init_mongo, cleanup_db_client
from catalog.logging import AccessLogger, setup_logging
from catalog.handlers.general import get_version, ping_handler
from catalog.handlers.profile import (
    ProfileView,
    ProfileItemView,
    ProfileCriteriaView,
    ProfileCriteriaItemView,
    ProfileCriteriaRGView,
    ProfileCriteriaRGItemView,
    ProfileCriteriaRGRequirementView,
    ProfileCriteriaRGRequirementItemView,
)
from catalog.handlers.category import (
    CategoryView,
    CategoryItemView,
    CategoryCriteriaView,
    CategoryCriteriaRGView,
    CategoryCriteriaRGRequirementView,
    CategoryCriteriaItemView,
    CategoryCriteriaRGItemView,
    CategoryCriteriaRGRequirementItemView,
)
from catalog.handlers.product import ProductView, ProductItemView
from catalog.handlers.product_document import ProductDocumentView, ProductDocumentItemView
from catalog.handlers.offer import OfferView
from catalog.handlers.image import ImageView
from catalog.handlers.search import SearchView
from catalog.handlers.vendor import VendorView
from catalog.handlers.vendor_document import VendorDocumentView
from catalog.handlers.vendor_product import VendorProductView
from catalog.handlers.vendor_product_document import VendorProductDocumentView
from catalog.settings import SENTRY_DSN, IMG_PATH, IMG_DIR, CLIENT_MAX_SIZE
from catalog.migration import import_data_job
from sentry_sdk.integrations.aiohttp import AioHttpIntegration
import sentry_sdk
import logging

logger = logging.getLogger(__name__)


def create_application(on_cleanup=None):
    app = web.Application(
        middlewares=(
            request_id_middleware,
            context_middleware,
            error_middleware,
            convert_response_to_json,
            login_middleware,
        ),
        client_max_size=CLIENT_MAX_SIZE
    )
    oas.setup(
        app,
        url_prefix='/api/doc',
        security={"Basic": {
            "type": "http",
            "scheme": "basic",
            "in": "header",
            "name": "Authorization"
        }})
    app.router.add_get("/api/ping", ping_handler, allow_head=False)
    app.router.add_get("/api/version", get_version, allow_head=False)

    # categories
    app.router.add_view(
        "/api/categories",
        CategoryView,
    )
    app.router.add_view(
        "/api/categories/{category_id}",
        CategoryItemView,
    )

    # category criteria

    app.router.add_view(
        r"/api/categories/{obj_id:[\w-]+}/criteria",
        CategoryCriteriaView,
    )
    app.router.add_view(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}",
        CategoryCriteriaItemView,
    )

    # profile criteria RG
    app.router.add_view(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups",
        CategoryCriteriaRGView,
    )
    app.router.add_view(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}",
        CategoryCriteriaRGItemView,
    )

    # profile criteria RG requirements
    app.router.add_view(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements",
        CategoryCriteriaRGRequirementView,
    )
    app.router.add_view(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements/{requirement_id:[\w-]+}",
        CategoryCriteriaRGRequirementItemView,
    )

    # profiles
    app.router.add_view(
        "/api/profiles",
        ProfileView,
    )
    app.router.add_view(
        r"/api/profiles/{profile_id:[\w-]+}",
        ProfileItemView,
    )

    # profile criteria
    app.router.add_view(
        r"/api/profiles/{obj_id:[\w-]+}/criteria",
        ProfileCriteriaView,
    )
    app.router.add_view(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}",
        ProfileCriteriaItemView,
    )

    # profile criteria RG
    app.router.add_view(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups",
        ProfileCriteriaRGView,
    )
    app.router.add_view(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}",
        ProfileCriteriaRGItemView,
    )

    # profile criteria RG requirements
    app.router.add_view(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements",
        ProfileCriteriaRGRequirementView,
    )
    app.router.add_view(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements/{requirement_id:[\w-]+}",
        ProfileCriteriaRGRequirementItemView,
    )

    # products
    app.router.add_view(
        "/api/products",
        ProductView
    )
    app.router.add_view(
        r"/api/products/{product_id:[\w-]+}",
        ProductItemView
    )

    # product docs
    app.router.add_view(
        r"/api/products/{parent_obj_id:[\w-]+}/documents",
        ProductDocumentView,
    )
    app.router.add_view(
        r"/api/products/{parent_obj_id:[\w-]+}/documents/{doc_id:[\w]{32}}",
        ProductDocumentItemView,
    )

    # # offers
    # app.router.add_get(
    #     "/api/offers",
    #     OfferView.collection_get,
    #     name="read_offer_registry",
    # )
    # app.router.add_get(
    #     r"/api/offers/{offer_id:[\w-]+}",
    #     OfferView.get,
    #     name="read_offer",
    #     allow_head=False
    # )
    #
    # # vendors
    # app.router.add_get(
    #     "/api/vendors",
    #     VendorView.collection_get,
    #     name="read_vendor_registry",
    #     allow_head=False
    # )
    # app.router.add_get(
    #     r"/api/vendors/{vendor_id:[\w]{32}}",
    #     VendorView.get,
    #     name="read_vendor",
    # )
    # app.router.add_get(
    #     r"/api/sign/vendors/{vendor_id:[\w]{32}}",
    #     VendorView.sign_get,
    #     name="read_sign_vendor",
    #     allow_head=False
    # )
    # app.router.add_post(
    #     r"/api/vendors",
    #     VendorView.post,
    #     name="create_vendor"
    # )
    # app.router.add_patch(
    #     r"/api/vendors/{vendor_id:[\w]{32}}",
    #     VendorView.patch,
    #     name="update_vendor"
    # )
    #
    # # vendor docs
    # app.router.add_get(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/documents",
    #     VendorDocumentView.collection_get,
    #     name="read_vendor_document_registry",
    #     allow_head=False,
    # )
    # app.router.add_get(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
    #     VendorDocumentView.get,
    #     name="read_vendor_document",
    # )
    # app.router.add_post(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/documents",
    #     VendorDocumentView.post,
    #     name="create_vendor_document"
    # )
    # app.router.add_put(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
    #     VendorDocumentView.put,
    #     name="replace_vendor_document",
    # )
    # app.router.add_patch(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
    #     VendorDocumentView.patch,
    #     name="update_vendor_document",
    # )
    #
    # # vendor product
    # app.router.add_post(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/products",
    #     VendorProductView.post,
    #     name="create_vendor_product",
    # )
    #
    # # vendor product docs
    # app.router.add_get(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/products/{product_id:[\w]{32}}/documents",
    #     VendorProductDocumentView.collection_get,
    #     name="read_vendor_product_document_registry",
    #     allow_head=False,
    # )
    # app.router.add_get(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/products/{product_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
    #     VendorProductDocumentView.get,
    #     name="read_vendor_product_document",
    # )
    # app.router.add_post(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/products/{product_id:[\w]{32}}/documents",
    #     VendorProductDocumentView.post,
    #     name="create_vendor_product_document"
    # )
    # app.router.add_put(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/products/{product_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
    #     VendorProductDocumentView.put,
    #     name="replace_vendor_product_document",
    # )
    # app.router.add_patch(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/products/{product_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
    #     VendorProductDocumentView.patch,
    #     name="update_vendor_product_document",
    # )
    #
    # # vendor ban
    # app.router.add_get(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/bans",
    #     VendorBanView.collection_get,
    #     name="read_vendor_ban_registry",
    #     allow_head=False
    # )
    # app.router.add_get(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}",
    #     VendorBanView.get,
    #     name="read_vendor_ban",
    # )
    # app.router.add_post(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/bans",
    #     VendorBanView.post,
    #     name="create_vendor_ban"
    # )
    #
    # # vendor ban docs
    # app.router.add_get(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}/documents",
    #     VendorBanDocumentView.collection_get,
    #     name="read_vendor_ban_document_registry",
    #     allow_head=False,
    # )
    # app.router.add_get(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}"
    #     r"/documents/{doc_id:[\w]{32}}",
    #     VendorBanDocumentView.get,
    #     name="read_vendor_ban_document",
    # )
    # app.router.add_post(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}/documents",
    #     VendorBanDocumentView.post,
    #     name="create_vendor_ban_document"
    # )
    # app.router.add_put(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
    #     VendorBanDocumentView.put,
    #     name="replace_vendor_ban_document",
    # )
    # app.router.add_patch(
    #     r"/api/vendors/{vendor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
    #     VendorBanDocumentView.patch,
    #     name="update_vendor_ban_document",
    # )
    #
    # # contributors
    # app.router.add_get(
    #     "/api/crowd-sourcing/contributors",
    #     ContributorView.collection_get,
    #     name="read_contributor_registry",
    #     allow_head=False
    # )
    # app.router.add_get(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}",
    #     ContributorView.get,
    #     name="read_contributor",
    # )
    # app.router.add_post(
    #     r"/api/crowd-sourcing/contributors",
    #     ContributorView.post,
    #     name="create_contributor"
    # )
    #
    # # contributor ban
    # app.router.add_get(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/bans",
    #     ContributorBanView.collection_get,
    #     name="read_contributor_ban_registry",
    #     allow_head=False
    # )
    # app.router.add_get(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}",
    #     ContributorBanView.get,
    #     name="read_contributor_ban",
    # )
    # app.router.add_post(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/bans",
    #     ContributorBanView.post,
    #     name="create_contributor_ban"
    # )
    #
    # # contributor docs
    # app.router.add_get(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/documents",
    #     ContributorDocumentView.collection_get,
    #     name="read_contributor_document_registry",
    #     allow_head=False,
    # )
    # app.router.add_get(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
    #     ContributorDocumentView.get,
    #     name="read_contributor_document",
    # )
    # app.router.add_post(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/documents",
    #     ContributorDocumentView.post,
    #     name="create_contributor_document"
    # )
    # app.router.add_put(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
    #     ContributorDocumentView.put,
    #     name="replace_contributor_document",
    # )
    # app.router.add_patch(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
    #     ContributorDocumentView.patch,
    #     name="update_contributor_document",
    # )
    #
    # # contributor ban docs
    # app.router.add_get(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}/documents",
    #     ContributorBanDocumentView.collection_get,
    #     name="read_contributor_ban_document_registry",
    #     allow_head=False,
    # )
    # app.router.add_get(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}"
    #     r"/documents/{doc_id:[\w]{32}}",
    #     ContributorBanDocumentView.get,
    #     name="read_contributor_ban_document",
    # )
    # app.router.add_post(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}/documents",
    #     ContributorBanDocumentView.post,
    #     name="create_contributor_ban_document"
    # )
    # app.router.add_put(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}"
    #     r"/documents/{doc_id:[\w]{32}}",
    #     ContributorBanDocumentView.put,
    #     name="replace_contributor_ban_document",
    # )
    # app.router.add_patch(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/bans/{ban_id:[\w]{32}}"
    #     r"/documents/{doc_id:[\w]{32}}",
    #     ContributorBanDocumentView.patch,
    #     name="update_contributor_ban_document",
    # )
    #
    # # product request
    # app.router.add_post(
    #     r"/api/crowd-sourcing/contributors/{contributor_id:[\w]{32}}/requests",
    #     ContributorProductRequestView.post,
    #     name="create_contributor_product_request"
    # )
    # app.router.add_get(
    #     r"/api/crowd-sourcing/requests",
    #     ProductRequestView.collection_get,
    #     name="read_product_request_registry",
    #     allow_head=False,
    # )
    # app.router.add_get(
    #     r"/api/crowd-sourcing/requests/{request_id:[\w]{32}}",
    #     ProductRequestView.get,
    #     name="read_product_request",
    # )
    # app.router.add_post(
    #     r"/api/crowd-sourcing/requests/{request_id:[\w]{32}}/accept",
    #     ProductRequestAcceptionView.post,
    #     name="accept_product_request"
    # )
    # app.router.add_post(
    #     r"/api/crowd-sourcing/requests/{request_id:[\w]{32}}/reject",
    #     ProductRequestRejectionView.post,
    #     name="reject_product_request"
    # )
    #
    # # product request docs
    # app.router.add_get(
    #     r"/api/crowd-sourcing/requests/{request_id:[\w]{32}}/documents",
    #     ProductRequestDocumentView.collection_get,
    #     name="read_product_request_document_registry",
    #     allow_head=False,
    # )
    # app.router.add_get(
    #     r"/api/crowd-sourcing/requests/{request_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
    #     ProductRequestDocumentView.get,
    #     name="read_product_request_document",
    # )
    # app.router.add_post(
    #     r"/api/crowd-sourcing/requests/{request_id:[\w]{32}}/documents",
    #     ProductRequestDocumentView.post,
    #     name="create_product_request_document"
    # )
    # app.router.add_put(
    #     r"/api/crowd-sourcing/requests/{request_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
    #     ProductRequestDocumentView.put,
    #     name="replace_product_request_document",
    # )
    # app.router.add_patch(
    #     r"/api/crowd-sourcing/requests/{request_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
    #     ProductRequestDocumentView.patch,
    #     name="update_product_request_document",
    # )
    #
    # # search
    # app.router.add_post(
    #     r"/api/search",
    #     SearchView.post,
    #     name="search_resources"
    # )
    # # images
    # app.router.add_post(
    #     r"/api/images",
    #     ImageView.post,
    #     name="upload_image"
    # )
    # # server images for dev env
    # app.router.add_static(IMG_PATH, IMG_DIR)

    app.on_startup.append(init_mongo)
    app.on_startup.append(import_data_job)
    if on_cleanup:
        app.on_cleanup.append(on_cleanup)
    app.on_cleanup.append(cleanup_db_client)
    return app


def setup_sentry():
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[AioHttpIntegration()]
        )


# def setup_swagger(application):
#     if SWAGGER_DOC_AVAILABLE:
#         aiohttp_setup_swagger(
#             application,
#             title='Prozorro Catalog API',
#             description='Prozorro Catalog API description',
#             api_version=version,
#             ui_version=3,
#             definitions=get_definitions(),
#         )


async def application():
    setup_logging()
    setup_sentry()
    application = create_application()
    # setup_swagger(application)
    return application


if __name__ == "__main__":
    logger.info("Starting app on 0.0.0.0:8000")
    web.run_app(
        application(),
        host="0.0.0.0",
        port=8000,
        access_log_class=AccessLogger,
        print=None
    )
