from aiohttp import web
from aiohttp_swagger import setup_swagger
from catalog import version
from catalog.settings import SWAGGER_DOC_AVAILABLE
from catalog.swagger import get_definitions
from catalog.middleware import (
    request_unpack_params,
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
    ProfileCriteriaView,
    ProfileCriteriaRGView,
    ProfileCriteriaRGRequirementView,
)
from catalog.handlers.category import (
    CategoryView,
    CategoryCriteriaView,
    CategoryCriteriaRGView,
    CategoryCriteriaRGRequirementView,
)
from catalog.handlers.product import ProductView
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
            request_unpack_params,
        ),
        client_max_size=CLIENT_MAX_SIZE
    )
    app.router.add_get("/api/ping", ping_handler, allow_head=False)
    app.router.add_get("/api/version", get_version, allow_head=False)

    # categories
    app.router.add_get(
        "/api/categories",
        CategoryView.collection_get,
        name="read_category_registry",
    )
    app.router.add_get(
        r"/api/categories/{category_id:[\w-]+}",
        CategoryView.get,
        name="read_category",
        allow_head=False
    )
    app.router.add_put(
        r"/api/categories/{category_id:[\w-]+}",
        CategoryView.put,
        name="create_category"
    )
    app.router.add_patch(
        r"/api/categories/{category_id:[\w-]+}",
        CategoryView.patch,
        name="update_category"
    )

    # category criteria

    app.router.add_get(
        r"/api/categories/{obj_id:[\w-]+}/criteria",
        CategoryCriteriaView.collection_get,
        name="read_category_criteria_registry",
    )
    app.router.add_get(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}",
        CategoryCriteriaView.get,
        name="read_category_criteria",
        allow_head=False,
    )
    app.router.add_post(
        r"/api/categories/{obj_id:[\w-]+}/criteria",
        CategoryCriteriaView.post,
        name="create_category_criteria"
    )
    app.router.add_patch(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}",
        CategoryCriteriaView.patch,
        name="update_category_criteria"
    )

    # profile criteria RG
    app.router.add_get(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups",
        CategoryCriteriaRGView.collection_get,
        name="read_category_criteria_rg_registry",
    )
    app.router.add_get(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}",
        CategoryCriteriaRGView.get,
        name="read_category_criteria_rg",
        allow_head=False,
    )
    app.router.add_post(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups",
        CategoryCriteriaRGView.post,
        name="create_category_criteria_rg"
    )
    app.router.add_patch(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}",
        CategoryCriteriaRGView.patch,
        name="update_category_criteria_rg"
    )

    # profile criteria RG requirements
    app.router.add_get(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements",
        CategoryCriteriaRGRequirementView.collection_get,
        name="read_category_criteria_rg_requirement_registry",
    )
    app.router.add_get(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements/{requirement_id:[\w-]+}",
        CategoryCriteriaRGRequirementView.get,
        name="read_category_criteria_rg_requirement",
        allow_head=False,
    )
    app.router.add_post(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements",
        CategoryCriteriaRGRequirementView.post,
        name="create_category_criteria_rg_requirement"
    )
    app.router.add_patch(
        r"/api/categories/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements/{requirement_id:[\w-]+}",
        CategoryCriteriaRGRequirementView.patch,
        name="update_category_criteria_rg_requirement"
    )

    # risk profiles
    app.router.add_get(
        "/api/profiles",
        ProfileView.collection_get,
        name="read_profile_registry",
    )
    app.router.add_get(
        r"/api/profiles/{profile_id:[\w-]+}",
        ProfileView.get,
        name="read_profile",
        allow_head=False
    )
    app.router.add_put(
        r"/api/profiles/{profile_id:[\w-]+}",
        ProfileView.put,
        name="create_profile"
    )
    app.router.add_patch(
        r"/api/profiles/{profile_id:[\w-]+}",
        ProfileView.patch,
        name="update_profile"
    )

    # profile criteria
    app.router.add_get(
        r"/api/profiles/{obj_id:[\w-]+}/criteria",
        ProfileCriteriaView.collection_get,
        name="read_profile_criteria_registry",
    )
    app.router.add_get(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}",
        ProfileCriteriaView.get,
        name="read_profile_criteria",
        allow_head=False,
    )
    app.router.add_post(
        r"/api/profiles/{obj_id:[\w-]+}/criteria",
        ProfileCriteriaView.post,
        name="create_profile_criteria"
    )
    app.router.add_patch(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}",
        ProfileCriteriaView.patch,
        name="update_profile_criteria"
    )
    app.router.add_delete(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}",
        ProfileCriteriaView.delete,
        name="delete_profile_criteria"
    )

    # profile criteria RG
    app.router.add_get(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups",
        ProfileCriteriaRGView.collection_get,
        name="read_profile_criteria_rg_registry",
    )
    app.router.add_get(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}",
        ProfileCriteriaRGView.get,
        name="read_profile_criteria_rg",
        allow_head=False,
    )
    app.router.add_post(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups",
        ProfileCriteriaRGView.post,
        name="create_profile_criteria_rg"
    )
    app.router.add_patch(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}",
        ProfileCriteriaRGView.patch,
        name="update_profile_criteria_rg"
    )
    app.router.add_delete(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}",
        ProfileCriteriaRGView.delete,
        name="delete_profile_criteria_rg"
    )

    # profile criteria RG requirements
    app.router.add_get(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements",
        ProfileCriteriaRGRequirementView.collection_get,
        name="read_profile_criteria_rg_requirement_registry",
    )
    app.router.add_get(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements/{requirement_id:[\w-]+}",
        ProfileCriteriaRGRequirementView.get,
        name="read_profile_criteria_rg_requirement",
        allow_head=False,
    )
    app.router.add_post(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements",
        ProfileCriteriaRGRequirementView.post,
        name="create_profile_criteria_rg_requirement"
    )
    app.router.add_patch(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements/{requirement_id:[\w-]+}",
        ProfileCriteriaRGRequirementView.patch,
        name="update_profile_criteria_rg_requirement"
    )
    app.router.add_delete(
        r"/api/profiles/{obj_id:[\w-]+}/criteria/{criterion_id:[\w-]+}/requirementGroups/{rg_id:[\w-]+}/requirements/{requirement_id:[\w-]+}",
        ProfileCriteriaRGRequirementView.delete,
        name="delete_profile_criteria_rg_requirement"
    )

    # products
    app.router.add_get(
        "/api/products",
        ProductView.collection_get,
        name="read_product_registry",
    )
    app.router.add_get(
        r"/api/products/{product_id:[\w-]+}",
        ProductView.get,
        name="read_product",
        allow_head=False
    )
    app.router.add_post(
        r"/api/products",
        ProductView.post,
        name="create_product"
    )
    app.router.add_patch(
        r"/api/products/{product_id:[\w-]+}",
        ProductView.patch,
        name="update_product"
    )

    # offers
    app.router.add_get(
        "/api/offers",
        OfferView.collection_get,
        name="read_offer_registry",
    )
    app.router.add_get(
        r"/api/offers/{offer_id:[\w-]+}",
        OfferView.get,
        name="read_offer",
        allow_head=False
    )

    # vendors
    app.router.add_get(
        "/api/vendors",
        VendorView.collection_get,
        name="read_vendor_registry",
        allow_head=False
    )
    app.router.add_get(
        r"/api/vendors/{vendor_id:[\w]{32}}",
        VendorView.get,
        name="read_vendor",
    )
    app.router.add_get(
        r"/api/sign/vendors/{vendor_id:[\w]{32}}",
        VendorView.sign_get,
        name="read_sign_vendor",
        allow_head=False
    )
    app.router.add_post(
        r"/api/vendors",
        VendorView.post,
        name="create_vendor"
    )
    app.router.add_patch(
        r"/api/vendors/{vendor_id:[\w]{32}}",
        VendorView.patch,
        name="update_vendor"
    )

    # vendor docs
    app.router.add_get(
        r"/api/vendors/{vendor_id:[\w]{32}}/documents",
        VendorDocumentView.collection_get,
        name="read_vendor_document_registry",
        allow_head=False,
    )
    app.router.add_get(
        r"/api/vendors/{vendor_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
        VendorDocumentView.get,
        name="read_vendor_document",
    )
    app.router.add_post(
        r"/api/vendors/{vendor_id:[\w]{32}}/documents",
        VendorDocumentView.post,
        name="create_vendor_document"
    )
    app.router.add_put(
        r"/api/vendors/{vendor_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
        VendorDocumentView.put,
        name="replace_vendor_document",
    )
    app.router.add_patch(
        r"/api/vendors/{vendor_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
        VendorDocumentView.patch,
        name="update_vendor_document",
    )

    # vendor product
    app.router.add_post(
        r"/api/vendors/{vendor_id:[\w]{32}}/products",
        VendorProductView.post,
        name="create_vendor_product",
    )

    # vendor product docs
    app.router.add_get(
        r"/api/vendors/{vendor_id:[\w]{32}}/products/{product_id:[\w]{32}}/documents",
        VendorProductDocumentView.collection_get,
        name="read_vendor_product_document_registry",
        allow_head=False,
    )
    app.router.add_get(
        r"/api/vendors/{vendor_id:[\w]{32}}/products/{product_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
        VendorProductDocumentView.get,
        name="read_vendor_product_document",
    )
    app.router.add_post(
        r"/api/vendors/{vendor_id:[\w]{32}}/products/{product_id:[\w]{32}}/documents",
        VendorProductDocumentView.post,
        name="create_vendor_product_document"
    )
    app.router.add_put(
        r"/api/vendors/{vendor_id:[\w]{32}}/products/{product_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
        VendorProductDocumentView.put,
        name="replace_vendor_product_document",
    )
    app.router.add_patch(
        r"/api/vendors/{vendor_id:[\w]{32}}/products/{product_id:[\w]{32}}/documents/{doc_id:[\w]{32}}",
        VendorProductDocumentView.patch,
        name="update_vendor_product_document",
    )

    # search
    app.router.add_post(
        r"/api/search",
        SearchView.post,
        name="search_resources"
    )
    # images
    app.router.add_post(
        r"/api/images",
        ImageView.post,
        name="upload_image"
    )
    # server images for dev env
    app.router.add_static(IMG_PATH, IMG_DIR)

    app.on_startup.append(init_mongo)
    app.on_startup.append(import_data_job)
    if on_cleanup:
        app.on_cleanup.append(on_cleanup)
    app.on_cleanup.append(cleanup_db_client)
    return app


if __name__ == "__main__":
    setup_logging()
    if SENTRY_DSN:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[AioHttpIntegration()]
        )
    logger.info("Starting app on 0.0.0.0:8000")
    application = create_application()

    if SWAGGER_DOC_AVAILABLE:
        setup_swagger(
            application,
            title='Prozorro Catalog API',
            description='Prozorro Catalog API description',
            api_version=version,
            ui_version=3,
            definitions=get_definitions(),
        )
    web.run_app(
        application,
        host="0.0.0.0",
        port=8000,
        access_log_class=AccessLogger,
        print=None
    )
